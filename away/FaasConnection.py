import requests
from requests.exceptions import ConnectionError
import subprocess
import os
import yaml

from .exceptions import FaasReturnedError, FaasServiceUnavailableException, EnsureException

import warnings

class FaasConnection():

    def __init__(self,
        provider: str = 'localhost',
        port: int = 8080,
        user: str = 'admin',
        password: str = None,
        ensure_available: bool = True):

        self.address = f'{provider}:{port}'
        self.auth_address = None

        if ensure_available: self.ensure_available()

        has_user = user is not None
        has_password = password is not None
        if has_user and has_password:
            # TODO: Make this safe
            if ensure_available:
                self.__cli_login(user, password)
        else:
            if has_password != has_user:
                warnings.warn('Only one of [user, password] present, but not the other. auth will be blank', Warning)

    def __cli_login(self, user: str, password: str | int):
        """
        Authenticates with the OpenFaaS server via CLI
        """
        subprocess.run(
            ['faas', 'login', '--gateway', f'http://{self.address}', '-u', str(user), '-p', str(password)],
            check=True
        )
        self.auth_address = f'{user}:{password}@{self.address}'

    def __repr__(self) -> str:

        return f'''FaasConnection at endpoint: {self.address};
        Auth details: {"Not logged in" if self.auth_address is None else "Logged in"};
        Is Available: {self.is_available()}'''

    def ensure_available(self):
        """
        Attempts to check health of the OpenFaaS server, and raises an exception if it is unavailable
        """
        try:
            r = requests.get(f'http://{self.address}/healthz')
            if r.status_code != 200:
                raise EnsureException(f'FaaS \'healthz\ check failed: status_code={r.status_code}, r={r.text}')
        except ConnectionError:
            is_local = 'localhost' in self.address or '127.0.0.1' in self.address

            raise FaasServiceUnavailableException(f'The FaaS server at {self.address} is not available.'  + '\nCheck that the local Kubernetes cluster has a port forward active' if is_local else '')

    def is_available(self) -> bool:
        """
        Checks health of the OpenFaaS server, returning `True` if the server is available and responding and `False` otherwise
        """
        try:
            self.ensure_available()
            return True
        except Exception:
            return False

    def get_faas_functions(self) -> [str]:
        """
        Queries the given OpenFaaS server for available functions
        Is equivalent to curl -s -X GET http://<faas_endpoint>/system/functions and getting function names
        """
        self.ensure_auth()

        res = requests.get(
            f'http://{self.auth_address}/system/functions',
            headers={'Content-Type': 'application/json'}
            )

        if res.status_code != 200:

            if res.status_code == 401:
                raise FaasReturnedError(f'OpenFaas server at {self.address} rejected credentials: {res.status_code}: {res.text}')
            raise FaasReturnedError(f'OpenFaaS server at {self.address} returned non 200 code: {res}; {res.text}')


        names = []
        for fn_details in res.json():
            names.append(fn_details['name'])

        return names

    def check_fn_present(self, fn_name: str) -> bool:
        """
        Checks if the function is present in the FaaS server.

        arguments:
            fn_name: the name of the function to check
        """
        available_functions = self.get_faas_functions()

        return fn_name in available_functions

    def ensure_fn_present(self, fn_name: str):
        """
        Raises an exception if the function is not present in the FaaS server

        arguments:
            fn_name: the name of the function to check
        """

        if not self.check_fn_present(fn_name):
            raise EnsureException(f'Function {fn_name} not present in OpenFaas server {self}. Available Functions: {self.get_faas_functions()}') 

    def is_auth(self) -> bool:
        """
        Checks if this FaasConnection is authenticated, returning `True` if it is and `False` otherwise
        """
        return self.auth_address is not None
    
    def ensure_auth(self):
        """
        Checks if this FaasConnection is authenticated and raises an exception if not
        """
        if not self.is_auth():
            raise EnsureException(f'OpenFaaS connection is not auth:\n{self}')

    def create_from_template(self, registry_prefix: str, fn_name: str):
        """
        Creates the files for an OpenFaaS templated function 

        arguments:
            fn_name: The name of the function files to be created
            regsitry_prefix: The prefix of the registry where to store the function
        """
        if not os.path.isdir('template'):
            # Re-pull template if not present
            subprocess.run(
                ['faas', 'template', 'store', 'pull', 'python3'],
                check=True
            )

        # Create templated function
        subprocess.run(
            ['faas', 'new', '--lang', 'python3', '--prefix', registry_prefix, '--quiet', fn_name],
            check=True
        )

    def publish_from_yaml(self, fn_name: str):
        """
        Publishes a function, with an existing folder and .yaml file to this OpenFaaS instance

        arguments:
            fn_name: The name of folder and .yaml files for this function
        """
        # Publish with faas cli
        subprocess.run(
            ['faas', 'up', '--gateway', f'http://{self.address}', '--yaml', f'{fn_name}.yml'],
            check=True
        )

    def remove_fn(self, fn_name: str):
        """
        Attempts to remove a function in this server instance by the name <fn_name>
        Requires auth privileges

        arguments:
            fn_name: The name of the function to delete
        """
        self.ensure_auth()

        subprocess.run(
            ['faas', 'remove', fn_name.replace('_', '-')],
            check=True
        )

    def get_function_annotations(self, fn_name: str) -> dict[str, str]:
        """
        Get a function's annotations, as described in its yaml file

        arguments:
            fn_name: The name of the function in the OpenFaaS provider
        """
        self.ensure_auth()
        
        endpoint = f'http://{self.auth_address}/system/function/{fn_name}?usage=1'
        res = requests.get(endpoint, headers={'Content-Type' : 'application/json'})

        if res.status_code != 200:
            raise FaasReturnedError(res)

        description = yaml.load(res.text, Loader=yaml.Loader)
        return description.get('annotations', {})

    def is_away_protocol(self, fn_name: str) -> bool:
        """
        Returns if a function was built with away's protocol, i.e: if it contains the annotation marking it as such

        arguments:
            fn_name: The name of the function in the OpenFaaS provider
        """
        annotations = self.get_function_annotations(fn_name)
        return 'built-with' in annotations and annotations['built-with'] == 'away'

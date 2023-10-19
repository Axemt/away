
import requests
from requests.exceptions import ConnectionError
import subprocess

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
                print('[WARN]: Only one of [user, password] present, but not the other. auth will be blank')

    def __cli_login(self, user, password):
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
                raise Exception(f'FaaS \'healthz\ check failed: status_code={r.status_code}, r={r.text}')
        except ConnectionError:
            is_local = 'localhost' in self.address or '127.0.0.1' in self.address

            raise ConnectionError(f'The FaaS server at {self.address} is not available.'  + '\nCheck that the local Kubernetes cluster has a port forward active' if is_local else '')

    def is_available(self) -> bool:
        """
        Checks health of the OpenFaaS server, returning `True` if the server is available and responding and `False` otherwise
        """
        try:
            self.ensure_available()
            return True
        except:
            return False

    def get_faas_functions(self) -> [str]:
        """
        Queries the given OpenFaaS server for available functions
        Is equivalent to curl -s -X GET http://<faas_endpoint>/system/functions and getting function names
        """

        res = requests.get(
            f'http://{self.auth_address}/system/functions',
            headers={'Content-Type': 'application/json'}
            )

        if res.status_code != 200:

            if res.status_code == 401:
                raise Exception(f'OpenFaas server at {self.address} rejected credentials: {res.status_code}: {res.text}')
            raise Exception(f'OpenFaaS server at {self.address} returned non 200 code: {res}; {res.text}')


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
            raise Exception(f'Function {fn_name} not present in OpenFaas server {self}. Available Functions: {self.get_faas_functions()}') 

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
            raise Exception(f'OpenFaaS connection is not auth:\n{self}')

    
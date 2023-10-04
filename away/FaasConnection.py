
import requests
from requests.exceptions import ConnectionError

class FaasConnection():

    def __init__(self,
        provider: str = 'localhost',
        port: int = 8080,
        user: str = 'admin',
        password: str = None,
        ensure_available: bool = True):

        self.address = f'{provider}:{port}' 
        if ensure_available: self.ensure_available()

        has_user = user is not None
        has_password = password is not None
        if has_user and has_password:
            auth_details = f'{user}:{password}@'
        else:
            if has_password != has_user:
                print('[WARN]: Only one of [user, password] present, but not the other. auth will be blank')
            auth_details = ''

        self.auth = auth_details
        self.auth_address = f'{auth_details}{self.address}'

    def __repr__(self) -> str:
        is_available = True
        try:
            self.ensure_available()
        except:
            is_available = False

        return f'''FaasConnection at endpoint: {self.address};
        Auth details: {"Not present" if self.auth == "" else "Present"};
        Is Available: {is_available}'''

    def ensure_available(self):
        try:
            r = requests.get(f'http://{self.address}/healthz')
            if r.status_code != 200:
                raise Exception(f'FaaS \'healthz\ check failed: status_code={r.status_code}, r={r.text}')
        except ConnectionError:
            is_local = provider == 'localhost' or provider == '127.0.0.1'

            raise ConnectionError(f'The FaaS server at {self.address} is not available.'  + '\nCheck that the local Kubernetes cluster has a port forward active' if is_local else '')

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

        

import requests
from .FaasConnection import FaasConnection

import typing
from typing import Callable, Any

from .common_utils import parametrized

@parametrized
def from_faas_deco(
    fn: Callable[[str], None],
    faas: FaasConnection,
    namespace: str  = '',
    check_present: bool = True,
    implicit_exception_handling = True,
    post_cleanup: Callable | None = None,
    replace_underscore=True,
    verbose: bool = False) -> Callable[[Any], Any]:
    """
    Converts a blank function into an OpenFaas Sync function
    This calls an OpenFaaS function synchronously in the given provider. The function
    name is the same as the blank function being wrapped

    Note that functions marked with this decorator 

    If \'implicit_exception_handling\' is disabled (=False), the return signature is of the form (data, status_code). Otherwise only data is returned
    Usage:

    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')
    in_pack = lambda t, s, m: t+s+m

    @from_faas(faas)
    def call_this_faas_function(takes, some, arguments):
        pass

    
    """

    function_name = fn.__name__ + namespace
    if replace_underscore:
        function_name = function_name.replace('_', '-')

    if check_present:
        available_functions = faas.get_faas_functions()

        if function_name not in available_functions:
            raise Exception(f'Function {function_name} not present in OpenFaas server {faas}. Available Functions: {available_functions}')


    endpoint = f'http://{faas.address}/function/{function_name}'

    def faas_fn(*args, **kwargs):

        # the function should only receive str-type parameters.
        # TODO: Is there any way to accept multiple type
        if len(args) > 0: args=''.join(args)

        if verbose: print(f'[INFO]: Requesting at endpoint {endpoint} with data={args}')

        res = requests.get(endpoint, data=args )

        if verbose: print(f'[INFO]: Got {res}, implicit_exception_handling={implicit_exception_handling}')
        if implicit_exception_handling:
            if res.status_code != 200:
                raise Exception(f'Function returned non 200 code: {res.status_code}, {res.text}')


        r = res.text

        if verbose: print(f'[INFO]: Got contents r={r}')
        if post_cleanup is not None:
            r = post_cleanup(res.text)
        
        if verbose: print(f'[INFO][SUCCESS]: Finished. r={r}, post_cleanup={post_cleanup is not None}')

        if implicit_exception_handling:
            return r
        else:
            return (r, res.status_code)

    faas_fn.__name__ += '_' + function_name
    return faas_fn

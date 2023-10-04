
import requests
from .FaasConnection import FaasConnection

import typing
from typing import Callable, Any

from .common_utils import parametrized


def __pack_args(args):
    # the function should only receive str-type parameters.
    # TODO: Is there any way to accept multiple type
    if len(args) > 0: args=''.join(args)

    return args

@parametrized
def from_faas_deco(
    fn: Callable[[str], None],
    faas: FaasConnection,
    namespace: str  = '',
    check_present: bool = True,
    implicit_exception_handling = True,
    post_cleanup: Callable | None = None,
    replace_underscore=True,
    is_auth: bool = False,
    verbose: bool = False) -> Callable[[Any], Any]:
    """
    Converts a blank function into an OpenFaaS sync function

    This calls an OpenFaaS function synchronously in the given provider. The function
    name is the same as the blank function being wrapped
 
    If \'implicit_exception_handling\' is disabled (=False), the return signature is of the form (data, status_code). Otherwise only data is returned


    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    @from_faas(faas)
    def call_this_faas_function(takes, some, arguments):
        pass
    
    """

    function_name = fn.__name__ + namespace
    if replace_underscore: function_name = function_name.replace('_', '-')

    if check_present: faas.check_fn_present(function_name)

    endpoint = f'http://{faas.auth_address if is_auth else faas.address}/function/{function_name}'

    def faas_fn(*args, **kwargs) -> Any:

        if verbose: print(f'[INFO]: Requesting at endpoint {endpoint} with data={args}')

        args = __pack_args(args)

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


def from_faas_str(function_name: str,
    faas: FaasConnection,
    namespace: str  = '',
    check_present: bool = True,
    implicit_exception_handling = True,
    post_cleanup: Callable | None = None,
    replace_underscore=True,
    is_auth: bool = False,
    verbose: bool = False) -> Callable[[Any], Any]:
    """
    Creates an OpenFaaS sync function from a given name
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function with the given name synchronously in the given provider.
    
    If \'implicit_exception_handling\' is disabled (=False), the return signature is of the form (data, status_code). Otherwise only data is returned

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.from_faas_str('env', faas)

    res = env()
    
    """

    if replace_underscore: function_name = function_name.replace('_', '-')

    if check_present: faas.check_fn_present(function_name)

    endpoint = f'http://{faas.auth_address if is_auth else faas.address}/function/{function_name}'

    def faas_fn(*args) -> Any:

        if verbose: print(f'[INFO]: Requesting at endpoint {endpoint} with data={args}')


        args = __pack_args(args)

        res = requests.get(endpoint, data=args)

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
    
    return faas_fn
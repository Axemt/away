
import requests

from .FaasConnection import FaasConnection
from .exceptions import FaasReturnedError, FaasFunctionTimedOutError

import typing
from typing import Callable, Any

from .common_utils import parametrized, pack_args


def __builder_sync(function_name: str,
    faas: FaasConnection,
    namespace: str  = '',
    ensure_present: bool = False,
    implicit_exception_handling = True,
    pack_args: Callable[[Any], str | dict ] = pack_args,
    unpack_args: Callable | None = None,
    replace_underscore=True,
    is_auth: bool = False,
    verbose: bool = False) -> Callable[[Any], Any]:


    if replace_underscore: function_name = function_name.replace('_', '-')

    if ensure_present: faas.ensure_fn_present(function_name)

    endpoint = f'http://{faas.auth_address if is_auth else faas.address}/function/{function_name}'

    def faas_fn(*args) -> Any:

        if verbose: print(f'[INFO]: Requesting at endpoint {endpoint} with data={args}')


        args = pack_args(args)

        if verbose: print(f'[INFO]: Packed args: {args}')

        res = requests.get(endpoint, data=args)

        if verbose: print(f'[INFO]: Got {res}, implicit_exception_handling={implicit_exception_handling}')
        if implicit_exception_handling:
            if res.status_code == 502: # pragma: no cover
                raise FaasFunctionTimedOutError(f'Function {function_name} timed out')

            elif res.status_code != 200:
                raise FaasReturnedError(f'Function returned non 200 code: {res.status_code}, {res.text}')


        r = res.text

        if verbose: print(f'[INFO]: Got contents r={r}')
        if unpack_args is not None:
            r = unpack_args(r)

        if verbose: print(f'[INFO][SUCCESS]: Finished. r={r}, unpack_args={unpack_args is not None}')

        if implicit_exception_handling:
            return r
        else:
            return (r, res.status_code)   
    
    faas_fn.__name__ = f'{function_name}_faas_fn_sync'
    faas_fn.__is_away__ = True
    return faas_fn

def from_faas_deco(fn: Callable[[str], None], *args, **kwargs) -> Callable[[Any], Any]:
    """
    Converts a blank function into an OpenFaaS sync function

    This calls an OpenFaaS function synchronously in the given provider. The function
    name is the same as the blank function being wrapped
 
    If \'implicit_exception_handling\' is disabled (=False), the return signature is of the form (data, status_code). Otherwise only data is returned


    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    @from_faas_deco(faas)
    def call_this_faas_function(takes, some, arguments):
        pass
    
    """

    function_name = fn.__name__

    return __builder_sync(function_name, *args, **kwargs)


def from_name(*args, **kwargs) -> Callable[[Any], Any]:
    """
    Creates an OpenFaaS sync function from a given name
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function with the given name synchronously in the given provider.
    
    If \'implicit_exception_handling\' is disabled (=False), the return signature is of the form (data, status_code). Otherwise only data is returned

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.sync_from_name('env', faas)

    res = env()
    
    """

    return __builder_sync(*args, **kwargs)
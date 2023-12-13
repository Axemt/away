
import requests
import asyncio

from .FaasConnection import FaasConnection
from .exceptions import FaasReturnedError, FaasFunctionTimedOutError

import typing
from typing import Callable, Any, Awaitable

from .common_utils import parametrized, pack_args

def __builder_async(function_name: str,
    faas: FaasConnection,
    namespace: str  = '',
    ensure_present: bool = False,
    implicit_exception_handling: bool = True,
    pack_args: Callable[[Any], str | dict ] = pack_args,
    unpack_args: Callable = lambda e: e,
    replace_underscore=True,
    is_auth: bool = False,
    verbose: bool = False) -> Awaitable:
    
    if replace_underscore: function_name = function_name.replace('_', '-')

    if ensure_present: faas.ensure_fn_present(function_name)

    endpoint = f'http://{faas.auth_address if is_auth else faas.address}/function/{function_name+namespace}'
    loop = asyncio.get_event_loop()

    async def faas_fn(*args, **kwargs) -> Awaitable:

        if verbose: print(f'[INFO]: Async-Requesting at endpoint {endpoint} with data={args}')

        args = pack_args(args)

        if verbose: print(f'[INFO]: Packed args: {args}')

        def start_get():
            res = requests.get(endpoint, data=args)

            if verbose: 
                print(f'[INFO]: Got {res}, implicit_exception_handling={implicit_exception_handling}')
            if implicit_exception_handling:
                if res.status_code == 502: # pragma: no cover
                    raise FaasFunctionTimedOutError(f'Function {function_name} timed out')

                elif res.status_code != 200:
                    raise FaasReturnedError(f'Function returned non 200 code: {res.status_code}, {res.text}')
            r = res.text
            if unpack_args is not None:
                r = unpack_args(r)

            return r if implicit_exception_handling else (r, res.status_code)


        res_fut = asyncio.to_thread(start_get)

        if verbose: print(f'[INFO]: Got {res_fut}')

        return (await asyncio.gather(res_fut))[0]

    faas_fn.__faas_id__ = hash(faas)
    faas_fn.__faas_croscall_endpoint__ = f'http://gateway.openfaas.svc.cluster.local.:8080/function/{function_name+namespace}'
    return faas_fn



def from_faas_deco(fn: Callable[[str], None], *args, **kwargs) -> Awaitable:
    """
    Converts a blank function into an OpenFaaS async function

    This calls an OpenFaaS function synchronously in the given provider using an async backend. The function
    name is the same as the blank function being wrapped

    Note that the decorated function does not have to be marked `async`, but it is recommended to serve as documentation

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    @builder_async.from_faas_deco(faas)
    async def call_this_faas_function(takes, some, arguments):
        pass
    
    """

    function_name = fn.__name__

    return __builder_async(function_name, *args, **kwargs)


def from_name(*args, **kwargs) -> Awaitable:
    """
    Creates an OpenFaaS sync function from a given name
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function synchronously in the given provider using an async backend. 

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.async_from_name('env', faas)

    res = env()
    
    """


    return __builder_async(*args, **kwargs)
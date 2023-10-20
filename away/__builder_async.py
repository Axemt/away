
import requests
import asyncio
from .FaasConnection import FaasConnection

import typing
from typing import Callable, Any, Awaitable

from .common_utils import parametrized, pack_args

def __builder_async(function_name: str,
    faas: FaasConnection,
    namespace: str  = '',
    ensure_present: bool = True,
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

        start_get = lambda: unpack_args(requests.get(endpoint, data=args).text)

        res_fut = asyncio.to_thread(start_get)

        if verbose: print(f'[INFO]: Got {res_fut}')

        return (await asyncio.gather(res_fut))[0]

    faas_fn.__name__ += '_' + function_name
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


def from_faas_str(*args, **kwargs) -> Awaitable:
    """
    Creates an OpenFaaS sync function from a given name
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function synchronously in the given provider using an async backend. 

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.async_from_faas_str('env', faas)

    res = env()
    
    """


    return __builder_async(*args, **kwargs)

import requests
from .FaasConnection import FaasConnection

import typing
from typing import Callable, Any, Awaitable

import inspect

from .common_utils import parametrized, pack_args
from .__builder_sync import from_faas_deco as __from_faas_deco_sync
from .__builder_async import from_faas_deco as __from_faas_deco_async

from .__builder_sync import from_faas_str as sync_from_faas_str
from .__builder_async import from_faas_str as async_from_faas_str


def faas_function(fn: Callable[[Any], Any], *args, **kwargs) -> Callable[[Any], Any] | Callable[[Any], Awaitable]:
    """
    Converts a blank function into an OpenFaaS function

    This creates an OpenFaaS function proxy for the wrapped function. The function
    name is the same as the blank function being wrapped

    Function stubs marked `async` will be using async wrappers, and vice-versa.

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    @builder.faas_function(faas)
    async def call_this_faas_function(takes, some, arguments):
        pass
    
    """
    print(fn)
    builder_fn = __from_faas_deco_async if not inspect.iscoroutinefunction(fn) else __from_faas_deco_sync

    return builder_fn(fn, *args, **kwargs)



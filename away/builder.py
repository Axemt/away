
import requests

from typing import Callable, Any, Awaitable, Tuple, Iterable
from types import ModuleType

import warnings

import inspect
from types import LambdaType
from importlib.metadata import version
from time import ctime
import yaml
import subprocess
import os
import shutil

from .common_utils import parametrized
from .__fn_utils import __get_fn_source, __get_external_dependencies
from .__fn_utils import __is_lambda, __ensure_stateless

from .__builder_sync import from_faas_deco as __from_faas_deco_sync
from .__builder_async import from_faas_deco as __from_faas_deco_async
from .__builder_sync import from_faas_str as sync_from_faas_str
from .__builder_async import from_faas_str as async_from_faas_str

from .protocol import __safe_server_unpack_args, __unsafe_server_unpack_args
from .protocol import make_client_pack_args_fn, make_client_unpack_args_fn

from .FaasConnection import FaasConnection

# Functions are defined as separate implementation to avoid including extra information
#  and checks in the published function
HANDLER_TEMPLATE = '''
# Built with Away version {} on {}
{}

# Args unpacker
{}
# Captured dependencies at build time
{}
# Wrapped to-publish function
{}

EXPECTED_LEN_OF_ARGS = {}

def handle(req):
    # Unpack args:
    args_bundle, args_len = {}(req)
    
    # Ensure correct signature
    assert args_len == EXPECTED_LEN_OF_ARGS, 'The function takes ' + str(EXPECTED_LEN_OF_ARGS) + ' arguments. ' + str(args_len) + ' were provided:' + str(args_bundle)

    # Assign to names
    {} = args_bundle
    
    # Call
    return {}({})
'''

def __build_handler_template(
    source_fn: Callable,
    server_unpack_args: Callable,
    __from_deco=False) -> str:
    """
    Populates `HANDLER_TEMPLATE` with the decorated function, appropriate arg unpacking and checks
    """
    fn_args = inspect.getfullargspec(source_fn).args

    captured_vars_txt = __get_external_dependencies(source_fn, from_deco=__from_deco)

    if captured_vars_txt != '':
        warnings.warn(f'[WARN]: The function {source_fn.__name__} uses variables outside function scope in function body. These will be statically assigned to their current values because OpenFaaS functions are stateless', SyntaxWarning) 

    fn_args_n = len(fn_args)
    fn_arg_names = ', '.join(fn_args)
    # format accordingly
    fn_arg_names.replace('[','').replace(']','').replace('\'','')

    noargs = fn_arg_names == ''
    if fn_arg_names == '':
        fn_arg_names = '_'

    source_fn_txt = __get_fn_source(source_fn, __from_deco=__from_deco)

    server_unpack_args_txt = inspect.getsource(server_unpack_args).replace('\t\t','')
    
    handler = __format_handler_template(
        server_unpack_args_txt,
        source_fn_txt,
        captured_vars_txt,
        fn_args_n,
        server_unpack_args.__name__,
        fn_arg_names,
        source_fn.__name__,
        fn_arg_names if not noargs else ''
    )


    return handler


def __format_handler_template(
    server_unpack_args,
    source_fn,
    captured_vars,
    fn_args_n,
    server_unpack_args_name,
    fn_arg_names,
    source_fn_name,
    fn_args_names) -> str:
    """
    Formats HANDLER TEMPLATE. Separated for convenience, readability and the ability to add default information
    """
    
    return HANDLER_TEMPLATE.format(
        version('away'),
        ctime(), # add version information by default
        '# protocol unpacker\nimport yaml\n' if 'yaml.' in captured_vars else '',
        server_unpack_args,
        captured_vars,
        source_fn,
        fn_args_n,
        server_unpack_args_name,
        fn_arg_names,
        source_fn_name,
        fn_args_names
    )

@parametrized
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
    builder_fn = __from_faas_deco_async if inspect.iscoroutinefunction(fn) else __from_faas_deco_sync

    return builder_fn(fn, *args, **kwargs)

@parametrized
def faas_function_with_protocol(fn: Callable[[Any], Any], *args, safe_args: bool = True, **kwargs) -> Callable[[Any], Any] | Callable[[Any], Awaitable]:
    """
    Converts a blank function into an OpenFaaS function using away's protocol

    This creates an OpenFaaS function proxy for the wrapped function. The function
    name is the same as the blank function being wrapped

    Function stubs marked `async` will be using async wrappers, and vice-versa.

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    @builder.faas_function_with_protocol(faas)
    async def a_function_that_used_away(takes, some, arguments):
        pass
    
    """
    packer = make_client_pack_args_fn(safe_args)
    unpacker = make_client_unpack_args_fn(safe_args)

    builder_fn = __from_faas_deco_async if inspect.iscoroutinefunction(fn) else __from_faas_deco_sync

    return builder_fn(fn, *args, pack_args=packer, unpack_args=unpacker, **kwargs)

def sync_from_faas_str_with_protocol(*args, safe_args: bool = True, **kwargs) -> Callable[[Any], Any]:
    """
    Creates an OpenFaaS sync function from a given name, using away's protocol by default
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function synchronously in the given provider.

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.sync_from_faas_str_with_protocol('env', faas)

    res = env()
    
    """

    return sync_from_faas_str(*args, 
        pack_args=make_client_pack_args_fn(safe_args),
        unpack_args=make_client_unpack_args_fn(safe_args),
        **kwargs
    )

def async_from_faas_str_with_protocol(*args, safe_args: bool = True, **kwargs) -> Callable[[Any], Awaitable]:
    """
    Creates an OpenFaaS sync function from a given name, using away's protocol by default
    The decorator method is still recommended. This builder is intended for building functions with a name that already exists

    This calls an OpenFaaS function synchronously in the given provider using an async backend. 

    Usage:
    faas = FaasConnection('my_faas_server.endpoint.com', port=1234, user='a', password='12345')

    env = builder.async_from_faas_str_with_protocol('env', faas)

    res = env()
    
    """
    return async_from_faas_str(*args,
        pack_args=make_client_pack_args_fn(safe_args),
        unpack_args=make_client_unpack_args_fn(safe_args),
        **kwargs
    )

@parametrized
def publish( 
    fn: Callable[[Any], Any], 
    faas: FaasConnection,
    *args,
    **kwargs) -> Callable[[Any], Any] | Callable[[Any], Awaitable]:
    """
    Publishes the wrapped function to an OpenFaaS server

    This also creates a function proxy at the client, with the same properties of the wrapped function (i.e: async/sync)
    Usage:

    @builder.publish(faas)
    def fibbonacci(n):
        if n in [0,1]: 
            return n
        return fibbonacci(n-1) + fibbonacci(n-2)

    
    """
    return mirror_in_faas(fn, faas, *args, __from_deco=True, **kwargs)

def mirror_in_faas( 
    fn: Callable[[Any], Any], 
    faas: FaasConnection,
    registry_prefix: str ='localhost:5000', 
    safe_args: bool = True,
    annotations: dict[str, str] = {},
    enable_dev_building: bool = False,
    server_unpack_args: Callable[[Any], Tuple] | None = None,
    __from_deco: bool = False,
    **kwargs) -> Callable[[Any], Any]:
    """
    Mirrors a given function in an OpenFaaS server, and returns a proxy

    Usage:

    def fibbonacci(n):
        if n in [0,1]: 
            return n
        return fibbonacci(n-1) + fibbonacci(n-2)

    fibbonacci_mirrored_in_faas = mirror_in_faas(fibbonacci, faas)
    
    """
    __ensure_stateless(fn)

    fn_name = fn.__name__.replace('_','-')
    
    assert not os.path.exists(f'{fn_name}.yml'), f'Cannot create FaaS function: The file {fn_name}.yml already exists'
    assert not os.path.exists(f'{fn_name}'), f'Cannot create FaaS function: The folder {fn_name} already exists'

    try:

        faas.create_from_template(registry_prefix, fn_name)

        # TODO: handle possible imports in function?

        # Create unpacker if not provided
        if server_unpack_args is None:
            if not safe_args:
                warnings.warn('"safe_args"=False; This may expose your OpenFaaS instance to malicious call requests through python\'s "pickle" module. See {https://docs.python.org/3/library/pickle.html} for details')
            # Establish 'protocol': serialize and then back
            server_unpack_args = __safe_server_unpack_args if safe_args else __unsafe_server_unpack_args

            client_pack_args = make_client_pack_args_fn(safe_args=safe_args)

            client_unpack_args = make_client_unpack_args_fn(safe_args=safe_args)

        # Create handler
        handler_source = __build_handler_template(fn, server_unpack_args,__from_deco=__from_deco)

        if 'import yaml' in handler_source:
            with open(f'{fn_name}/requirements.txt', 'a') as requirements:
                requirements.write('pyyaml')

        with open(f'{fn_name}/handler.py', 'w') as handler:
            handler.write(handler_source)

        
        with open(f'{fn_name}.yml', 'r+') as stack:
            description = yaml.load(stack, Loader=yaml.Loader)
        
            # 'tag' as built with protocol
            annotations['built-with'] = 'away'
            description['functions'][fn_name]['annotations'] = annotations

            stack.seek(0)
            stack.write(yaml.dump(description))


        faas.publish_from_yaml(fn_name)


    finally:
        # cleanup
        shutil.rmtree('template')
        shutil.rmtree(fn_name)
        os.remove(f'{fn_name}.yml')
    

    # return a stub function wrapped with builder/builder async

    if inspect.iscoroutinefunction(fn):
        create_fn = async_from_faas_str
    else:
        create_fn = sync_from_faas_str

    fn = create_fn(fn_name, faas, pack_args=client_pack_args, unpack_args=client_unpack_args, **kwargs)

    return fn
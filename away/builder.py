
import requests

from typing import Callable, Any, Awaitable, Tuple, Iterable

import warnings

import inspect
from importlib.metadata import version
from time import ctime
import yaml
import subprocess
import os
import shutil

from .common_utils import parametrized, pack_args
from .__builder_sync import from_faas_deco as __from_faas_deco_sync
from .__builder_async import from_faas_deco as __from_faas_deco_async

from .__builder_sync import from_faas_str as sync_from_faas_str
from .__builder_async import from_faas_str as async_from_faas_str

from .__protocol import safe_server_unpack_args as __safe_server_unpack_args
from .__protocol import unsafe_server_unpack_args as __unsafe_server_unpack_args
from .__protocol import make_client_pack_args as __make_client_pack_args
from .__protocol import make_client_unpack_args as __make_client_unpack_args
from .__protocol import expand_dependency_item as __expand_dependency_item

from .FaasConnection import FaasConnection

# Functions are defined as separate implementation to avoid including extra information
#  and checks in the published function
HANDLER_TEMPLATE = '''
# Built with Away version {} on {}

{}

# Args unpacker
{}
    
# Wrapped to-publish function
{}

# Captured variables at build time
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


def __build_handler_template(server_unpack_args: Callable, source_fn: Callable, safe_args: bool, __from_deco=False) -> str:
    """
    Populates `HANDLER_TEMPLATE` with the decorated function, appropriate arg unpacking and checks
    """
    fn_args = inspect.getfullargspec(source_fn).args

    # FIXME: Fails for recursive functions defined inside another function or a class
    try:
        outside_vars = inspect.getclosurevars(source_fn)
    except ValueError as e:
        raise Exception("A value error was raised in `inspect.getclosurevars`. This is likely because you are decorating a function within a function/closure or class. For the meantime, use `builder.mirror_in_faas`: " + repr(e))
    captured_vars_txt = ''

    # recursive functions with decorator always have the function itself as unbound
    is_recursive_deco = __from_deco and source_fn.__name__ in outside_vars.unbound
    if (is_recursive_deco and len(outside_vars.unbound) > 1) or (not is_recursive_deco and len(outside_vars.unbound) > 0) :
        warnings.warn(f'The function {source_fn.__name__} contains unbound variables ({outside_vars.unbound})that cannot be resolved at build time. These may result in errors within the built OpenFaaS function.', SyntaxWarning)

    dependency_closed_l = [source_fn.__name__]
    for group in [outside_vars.nonlocals, outside_vars.globals]:
        for k, v in group.items():
            # exclude the function itself to allow recursive calls
            captured_vars_txt += __expand_dependency_item(k, v, safe_args, dependency_closed_l)
            dependency_closed_l.append(k)

    if captured_vars_txt != '':
        warnings.warn(f'[WARN]: The function {source_fn.__name__} uses variables outside function scope in function body. These will be statically assigned to the current values ({outside_vars}) because OpenFaaS functions are stateless', SyntaxWarning) 

    fn_args_n = len(fn_args)
    fn_arg_names = ', '.join(fn_args)
    # format accordingly
    fn_arg_names.replace('[','').replace(']','').replace('\'','')

    noargs = fn_arg_names == ''
    if fn_arg_names == '':
        fn_arg_names = '_'

    source_fn_arr = inspect.getsource(source_fn).split('\n')
    
    # skip line containing decorator, if it is decorated
    if __from_deco: source_fn_arr.pop(0)

    # replace possible async mark to sync in server
    source_fn_arr[0] = source_fn_arr[0].replace('async def', 'def')
    
    # get source indent level
    indent_level = source_fn_arr[0].find('def')
    indent_level = indent_level if indent_level > 0 else 0
    

    # unindent if the function happened to be nested
    source_fn_arr = list(map(lambda l: l[indent_level:], source_fn_arr))
    
    source_fn_txt = '\n'.join(source_fn_arr)

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
    fn_args_names
) -> str:
    """
    Formats HANDLER TEMPLATE. Separated for convenience, readability and the ability to add default information
    """
    
    return HANDLER_TEMPLATE.format(
        version('away'),
        ctime(), # add version information by default
        '# protocol unpacker\nimport yaml\n' if 'yaml.' in captured_vars else '',
        server_unpack_args,
        source_fn,
        captured_vars,
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
def publish( 
    fn: Callable[[Any], Any], 
    faas: FaasConnection,
    registry_prefix: str ='localhost:5000', 
    safe_args: bool = True,
    enable_dev_building: bool = False,
    server_unpack_args: Callable[[Any], Tuple] | None = None,
    **kwargs
) -> Callable[[Any], Any] | Callable[[Any], Awaitable]:
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
    return mirror_in_faas(fn, faas, registry_prefix, safe_args, enable_dev_building, server_unpack_args, __from_deco=True, **kwargs)


def mirror_in_faas( 
    fn: Callable[[Any], Any], 
    faas: FaasConnection,
    registry_prefix: str ='localhost:5000', 
    safe_args: bool = True,
    enable_dev_building: bool = False,
    server_unpack_args: Callable[[Any], Tuple] | None = None,
    __from_deco: bool = False,
    **kwargs
) -> Callable[[Any], Any]:
    """
    Mirrors a given function in an OpenFaaS server, and returns a proxy

    Usage:

    def fibbonacci(n):
        if n in [0,1]: 
            return n
        return fibbonacci(n-1) + fibbonacci(n-2)

    fibbonacci_mirrored_in_faas = mirror_in_faas(fibbonacci, faas)
    
    """

    # This is probably not the best way to check if a function is stateful,
    #   maybe it just happens to take an arg named 'self'...
    takes_self_as_arg = 'self' in inspect.getfullargspec(fn).args
    if takes_self_as_arg or inspect.ismethod(fn):
        reason = 'takes \'self\' as an argument' if takes_self_as_arg else 'is a class method'
        raise Exception(f'Can only build stateless functions. The function {fn.__name__} ' + reason)

    fn_name = fn.__name__.replace('_','-')
    
    assert not os.path.exists(f'{fn_name}.yml'), f'Cannot create FaaS function: The file {fn_name}.yml already exists'
    assert not os.path.exists(f'{fn_name}'), f'Cannot create FaaS function: The folder {fn_name} already exists'

    try:

        faas.create_from_template(registry_prefix, fn_name)

        # TODO: handle possible imports in function?

        # Create unpacker if not provided
        if server_unpack_args is None:
            if not safe_args:
                warnings.warn('"safe_args"=False; This may expose your OpenFaaS instance to malicious requests through python\'s "pickle" module. See {https://docs.python.org/3/library/pickle.html} for details')
            # Establish 'protocol': serialize and then back
            server_unpack_args = __safe_server_unpack_args if safe_args else __unsafe_server_unpack_args

            client_pack_args = __make_client_pack_args(safe_args)

            client_unpack_args = __make_client_unpack_args(safe_args)

        # Create handler
        handler_source = __build_handler_template(server_unpack_args, fn, safe_args, __from_deco=__from_deco)

        if 'import yaml' in handler_source:
            with open(f'{fn_name}/requirements.txt', 'a') as requirements:
                requirements.write('pyyaml')

        with open(f'{fn_name}/handler.py', 'w') as handler:
            handler.write(handler_source)


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
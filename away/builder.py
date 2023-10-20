
import requests

import typing
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

from .FaasConnection import FaasConnection

HANDLER_TEMPLATE = '''
# Built with Away version {} on {}

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

def __server_unpack_args(req):
    import yaml
    args =  yaml.safe_load(req)
    if len(args)==1:
        return args[0], 1
    if len(args)==0:
        return None, 0

    return args, len(args)

def __client_pack_args(it: Iterable): return yaml.safe_dump(it)

def __client_unpack_args(st: str): return yaml.safe_load(st)

def __get_handler_template(server_unpack_args: Callable, source_fn: Callable) -> str:
    """
    Populates `HANDLER_TEMPLATE` with the decorated function, appropriate arg unpacking and checks
    """
    fn_args = inspect.getfullargspec(source_fn)[0]
    captured_vars = inspect.getclosurevars(source_fn)
    captured_vars_txt = ''

    if len(captured_vars.unbound) > 0:
        warngins.warn(f'The function {source_fn.__name__} contains unbound variables ({captured_vars.unbound})that cannot be resolved at build time. These may result in errors within the built OpenFaaS function.', SyntaxWarning)

    for group in [captured_vars.nonlocals, captured_vars.globals]:
        for k, v in group.items():
            captured_vars_txt += f'{k} = {v}\n'

    if captured_vars_txt != '':
        warnings.warn(f'[WARN]: Use of variables outside function scope in function body. These will be statically assigned to the current values ({captured_vars}) because OpenFaaS functions are stateless', SyntaxWarning) 

    fn_args_n = len(fn_args)
    fn_arg_names = ', '.join(fn_args)
    # format accordingly
    fn_arg_names.replace('[','').replace(']','').replace('\'','')

    noargs = fn_arg_names == ''
    if fn_arg_names == '':
        fn_arg_names = '_'

    source_fn_arr = inspect.getsource(source_fn).split('\n')
    
    # skip line containing decorator
    source_fn_arr.pop(0)

    # check if function is marked as async in source
    source_marked_async = source_fn_arr[0].find('async') != -1
    
    # get source indent level
    indent_level = source_fn_arr[0].find('def' if not source_marked_async else 'async')
    indent_level = indent_level if indent_level > 0 else 0
    
    # replace possible async mark to sync in server
    source_fn_arr[0] = source_fn_arr[0].replace('async def', 'def')

    # unindent if the function happened to be nested
    source_fn_arr = list(map(lambda l: l[indent_level:], source_fn_arr))
    
    source_fn_txt = '\n'.join(source_fn_arr)
    
    handler = HANDLER_TEMPLATE.format(
        version('away'),
        ctime(),
        inspect.getsource(server_unpack_args).replace('\t\t',''),
        source_fn_txt,
        captured_vars_txt,
        fn_args_n,
        server_unpack_args.__name__,
        fn_arg_names,
        source_fn.__name__,
        fn_arg_names if not noargs else ''
    )

    return handler

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
    fn: Callable, 
    faas: FaasConnection,
    registry_prefix: str ='localhost:5000', 
    safe_args: bool = True,
    enable_dev_building: bool = False,
    server_unpack_args: Callable[[Any], Tuple] | None = None,
    **kwargs
):
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
    
    fn_name = fn.__name__.replace('_','-')
    
    #raise NotImplementedError('Under construction')
    assert not os.path.exists(f'{fn_name}.yml'), f'Cannot create FaaS function: The file {fn_name}.yml already exists'
    assert not os.path.exists(f'{fn_name}'), f'Cannot create FaaS function: The folder {fn_name} already exists'

    try:

        # Re-pull template
        subprocess.run(
            ['faas', 'template', 'store', 'pull', 'python3'],
            check=True
        )

        # Create templated function
        subprocess.run(
            ['faas', 'new', '--lang', 'python3', '--prefix', registry_prefix, '--quiet', fn_name], 
            check=True
        )

        # TODO: handle possible imports in function?
        # TODO: handle variables used in function but defined outside

        # Create unpacker
        if server_unpack_args is None:
            # Establish 'protocol': serialize and then back
            server_unpack_args = __server_unpack_args

            client_pack_args = __client_pack_args

            client_unpack_args = __client_unpack_args

            with open(f'{fn_name}/requirements.txt', 'a') as requirements:
                requirements.write('pyyaml')

        # Create handler
        handler_source = __get_handler_template(server_unpack_args, fn)

        with open(f'{fn_name}/handler.py', 'w') as handler:
            handler.write(handler_source)


        # Publish with faas cli
        subprocess.run(
            ['faas', 'up', '--gateway', f'http://{faas.address}', '--yaml', f'{fn_name}.yml'],
            check=True
        )


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
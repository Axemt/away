import yaml
from typing import Callable, Any, Awaitable, Tuple, Iterable
import inspect
import warnings

from .__fn_utils import __get_fn_source

def __safe_server_unpack_args(req): # pragma: no cover
    import yaml
    args =  yaml.safe_load(req)
    if len(args)==1:
        return args[0], 1
    if len(args)==0:
        return None, 0

    return args, len(args)

def __unsafe_server_unpack_args(req): # pragma: no cover
    import yaml
    # uses pyyaml's unsafe Loader
    args =  yaml.load(req, Loader=yaml.Loader)
    if len(args)==1:
        return args[0], 1
    if len(args)==0:
        return None, 0

    return args, len(args)

def __safe_server_pack_args(req): # pragma: no cover
    import yaml
    args =  yaml.safe_dump(req)
    return args

def __unsafe_server_pack_args(req): # pragma: no cover
    import yaml
    args =  yaml.dump(req)
    return args

def make_client_pack_args_fn(safe_args: bool = True) -> Callable[[Iterable[Any]], str]: 

    # NOTE: Why does this have this very particular structure?
    #        this if-else block and particular variable assign and then return helps implement intra-cluster
    #        dependencies due to the dependency expansion engine, which will take the below line literally and 
    #        include it in the intracluster proxy. I'd love to have it be more elegant :)
    if safe_args: 
        pack_args = lambda it: yaml.safe_dump(it)
    else:
        pack_args = lambda it: yaml.dump(it)

    return pack_args

def make_client_unpack_args_fn(safe_args: bool = True) -> Callable[[str], Tuple[Any]]: 
    if safe_args:
        unpack_args = lambda st: yaml.safe_load(st)
    else:
        unpack_args = lambda st: yaml.load(st, Loader=yaml.Loader)

    return unpack_args

def __pack_repr_or_protocol(var_obj: Any, safe_args: bool = False) -> str:

    if __is_repr_literal(var_obj):
        return f'{repr(var_obj)}'
    elif inspect.isfunction(var_obj):
        return __get_fn_source(var_obj)
    else:
        safe_load_prefix_or = 'safe_' if safe_args else ''
        pack_fn = make_client_pack_args_fn(safe_args=safe_args)
        var_obj_yaml = pack_fn(var_obj).replace('\n', '\\n')
        packed_line = f'yaml.{safe_load_prefix_or}load("{var_obj_yaml}",Loader=yaml.Loader)'

        if '!!python/name:' in packed_line:
            warnings.warn(f'The object {var_obj} contains a member that may not be present in the handler namespace')

        return packed_line

def __is_repr_literal(var_obj: Any) -> bool:

    is_repr_literal = True
    try:
        fake_scope = {}
        exec(f'test = {repr(var_obj)}', fake_scope)
        assert fake_scope['test'] == var_obj
    except SyntaxError:
        is_repr_literal = False
    
    return is_repr_literal

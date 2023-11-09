import yaml
from typing import Callable, Any, Awaitable, Tuple, Iterable
import inspect

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

def make_client_pack_args_fn(safe_args: bool = True) -> Callable[[Iterable[Any]], str]: 
    return (lambda it: yaml.safe_dump(it)) if safe_args else (lambda it: yaml.dump(it))

def make_client_unpack_args_fn(safe_args: bool = True) -> Callable[[str], Tuple[Any]]: 
    return (lambda st: yaml.safe_load(st)) if safe_args else (lambda st: yaml.load(st, Loader=yaml.Loader))

def __pack_repr_or_protocol(var_obj: Any, safe_args: bool) -> str:

    if __is_repr_literal(var_obj):
        return f'{repr(var_obj)}'
    elif inspect.isfunction(var_obj):
        return __get_fn_source(var_obj)
    else:
        safe_load_prefix_or = 'safe_' if safe_args else ''
        pack_fn = make_client_pack_args_fn(safe_args=safe_args)
        var_obj_yaml = pack_fn(var_obj).replace('\n', '\\n')
        return f"yaml.{safe_load_prefix_or}load(\'{var_obj_yaml}\')"

def __is_repr_literal(var_obj: Any) -> bool:

    is_repr_literal = True
    try:
        fake_scope = {}
        exec(f'test = {repr(var_obj)}', fake_scope)
        assert fake_scope['test'] == var_obj
    except SyntaxError:
        is_repr_literal = False
    
    return is_repr_literal
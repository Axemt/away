import yaml
from typing import Callable, Any, Awaitable, Tuple, Iterable


def safe_server_unpack_args(req): # pragma: no cover
    import yaml
    args =  yaml.safe_load(req)
    if len(args)==1:
        return args[0], 1
    if len(args)==0:
        return None, 0

    return args, len(args)

def unsafe_server_unpack_args(req): # pragma: no cover
    import yaml
    # uses pyyaml's unsafe Loader
    args =  yaml.load(req, Loader=yaml.Loader)
    if len(args)==1:
        return args[0], 1
    if len(args)==0:
        return None, 0

    return args, len(args)

def make_client_pack_args(safe_args: bool) -> Callable[[Iterable[Any]], str]: 
    return (lambda it: yaml.safe_dump(it)) if safe_args else (lambda it: yaml.dump(it))

def make_client_unpack_args(safe_args: bool) -> Callable[[str], Tuple[Any]]: 
    return (lambda st: yaml.safe_load(st)) if safe_args else (lambda st: yaml.load(st, Loader=yaml.Loader))



def expand_dependency_item(var_name: str, var_obj: Any, safe_args: bool, dependency_closed_l: [str]) -> str:

    res = ''
    safe_load_prefix_or = 'safe_' if safe_args else ''
    if var_name not in dependency_closed_l:
        # TODO: if the type of the value is not a complex object, write literal
        res += f'{var_name} = {pack_repr_or_protocol(var_obj, safe_args)}\n'
        # ... else expand the dependent function/object/class
    return res

def pack_repr_or_protocol(var_obj: Any, safe_args: bool) -> str:

    if is_repr_literal(var_obj):
        return f'{repr(var_obj)}'
    else:
        safe_load_prefix_or = 'safe_' if safe_args else ''
        pack_fn = make_client_pack_args(safe_args)
        var_obj_yaml = pack_fn(var_obj).replace('\n', '\\n')
        return f"yaml.{safe_load_prefix_or}load(\'{var_obj_yaml}\')"

def is_repr_literal(var_obj: Any) -> bool:

    is_repr_literal = True
    try:
        fake_scope = {}
        exec(f'test = {repr(var_obj)}', fake_scope)
        assert fake_scope['test'] == var_obj
    except SyntaxError:
        is_repr_literal = False
    
    return is_repr_literal
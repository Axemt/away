from typing import Callable, Any
import inspect
import dis
import warnings

from .common_utils import pack_args as default_pack_args
from .common_utils import experimental
from .exceptions import EnsureException

def __get_fn_source(source_fn: Callable[[Any], Any], from_deco: bool=False):
    source_fn_arr = inspect.getsource(source_fn).split('\n')
    is_lambda = __is_lambda(source_fn)

    # skip line containing decorator, if it is decorated
    if from_deco: source_fn_arr.pop(0)
    # replace possible async mark to sync in server (only fns)
    if not is_lambda: source_fn_arr[0] = source_fn_arr[0].replace('async def', 'def')
    
    # get source indent level
    indent_level = source_fn_arr[0].find('lambda' if is_lambda else 'def')
    indent_level = max(indent_level, 0)
    
    # unindent if the function happened to be nested
    source_fn_arr = list(map(lambda l: l[indent_level:] if not is_lambda else l.strip(), source_fn_arr))

    source_fn_txt = '\n'.join(source_fn_arr)

    return source_fn_txt

__is_lambda = lambda fn: inspect.isfunction(fn) and fn.__name__ == '<lambda>'

def __is_away_fn(fn: Callable[[Any], Any]) -> bool:

    return hasattr(fn, '__faas_id__')

def __is_away_protocol_fn(fn: Callable[[Any], Any]) -> bool:

    return hasattr(fn, '__away_protocol_is_safe__')

def __is_away_protocol_safe_fn(fn: Callable[[Any], Any]) -> bool:
    return __is_away_protocol_fn(fn) and fn.__away_protocol_is_safe__

def __is_stateless(fn: Callable[[Any], Any]) -> bool:
    # This is probably not the best way to check if a function is stateful,
    #   maybe it just happens to take an arg named 'self'...
    return not (__is_takes_self(fn) or inspect.ismethod(fn))

def __is_takes_self(fn: Callable[[Any], Any]) -> bool:
    takes_self_as_arg = 'self' in inspect.getfullargspec(fn).args
    return takes_self_as_arg

def __ensure_stateless(fn):
    # This is probably not the best way to check if a function is stateful,
    #   maybe it just happens to take an arg named 'self'...
    
    if not __is_stateless(fn):
        reason = 'takes \'self\' as an argument' if __is_takes_self(fn) else 'is a class method'
        raise EnsureException(f'Can only build stateless functions. The function {fn.__name__} ' + reason)

def __get_external_dependencies(fn: Callable[[Any], Any], faas_id: int, from_deco: bool=False) -> str:
    return __get_external_dependencies_rec(fn, faas_id, set(), from_deco=from_deco)

def __get_external_dependencies_rec(fn: Callable[[Any], Any], faas_id: int, closed_s: set[str], from_deco: bool=False) -> str:
    res = ''

    try:
        # FIXME: Fails for recursive functions defined inside another function or a class
        #         this looks like a problem on `inspect`'s end. (py3.10)
        outside_vars = inspect.getclosurevars(fn)
    except ValueError as e:
        raise Exception(f"A value error was raised in `inspect.getclosurevars`. This is likely because you are decorating a recursive function within a function/closure or class. For the meantime, use `builder.mirror_in_faas`:\nError message {repr(e)} while expanding dependencies of function `{fn.__name__}` ({fn})")

    # recursive functions with decorator always have the function itself as unbound
    is_recursive_deco = from_deco and fn.__name__ in outside_vars.unbound
    if (is_recursive_deco and len(outside_vars.unbound) > 1) or (not is_recursive_deco and len(outside_vars.unbound) > 0) :
        warnings.warn(f'The function {fn.__name__} contains unbound variables ({outside_vars.unbound})that cannot be resolved at build time. These may result in errors within the built OpenFaaS function.', SyntaxWarning)
    
    closed_s.add(fn.__name__)
    for group in [outside_vars.nonlocals, outside_vars.globals]:
        for var_name, var_obj in group.items():
            if var_name not in closed_s:
                closed_s.add(var_name)

                is_intracluster = __is_away_fn(var_obj) and var_obj.__faas_id__ == faas_id
                if is_intracluster:
                    # if away_fn and intracluster -> special case: build an intra-cluster proxy and expand-it
                    # discard the original proxy
                    var_obj = __build_intracluster_proxy(var_obj)

                add = __expand_dependency_item(var_name, var_obj)
                if is_intracluster:
                    add = add.replace('intracluster_proxy', var_name)

                res += add
                if inspect.isfunction(var_obj):
                    add = __get_external_dependencies_rec(var_obj, faas_id, closed_s)
                    res += add

    return res

def __expand_dependency_item(
    var_name: str, 
    var_obj: Any) -> str:
    """
    Gets the line to insert in the template to define <var_name> with value <var_obj> in the server
    """
    # avoid circular dependency
    from .protocol import __pack_repr_or_protocol
    res = ''

    # only assign name to variables that can be assigned; i.e everything except non-functions. Lambda sources already include the name
    if not inspect.isfunction(var_obj):
        res += f'{var_name} = '

    # Since we are pulling in a dependency, everything is assumed to be safe
    #  i.e: it's your fault if you use an unsafe dependency in your own function
    #  this doesn't mean the calls are safe. Call safety is handled separately
    res += f'{__pack_repr_or_protocol(var_obj, safe_args=False)}\n'
    
    return res

def __build_intracluster_proxy(faas_fn: Callable[[Any], Any]) -> Callable[[Any], Any]:

    is_proto = __is_away_protocol_fn(faas_fn)
    is_safe_proto = __is_away_protocol_safe_fn(faas_fn)

    # avoid circular dependency
    from .protocol import make_client_pack_args_fn, make_client_unpack_args_fn
    
    # NOTE: Why does this have this very particular structure?
    #        this if-else block and particular variable assign and then return helps implement intra-cluster
    #        dependencies due to the dependency expansion engine, which will take the below line literally and 
    #        include it in the intracluster proxy. I'd love to have it be more elegant :)
    #        
    #       This is the same for `protocol.make_client_*_args_fn`
    if not is_proto:
        pack_args   = default_pack_args
        unpack_args = lambda e: e 
    else:
        pack_args   = make_client_pack_args_fn(is_safe_proto)
        unpack_args = make_client_unpack_args_fn(is_safe_proto)

    endpoint = faas_fn.__faas_croscall_endpoint__
    
    
    def intracluster_proxy(*args): # pragma: no cover
        # This function dependency has been detected to be present in the same cluster by Away
        import requests
        args = pack_args(args)
        res = requests.get(endpoint, data=args)

        if res.status_code != 200:
            raise Exception(f'Function returned non 200 code: {res.status_code}, {res.text}')

        return unpack_args(res.text)

    if is_proto:
        from .builder import __add_protocol_marker_attrs
        __add_protocol_marker_attrs(intracluster_proxy, is_safe_proto)

    return intracluster_proxy

def __get_all_modules_mentioned(fn: Callable[[Any], Any]) -> [str]:


    with open(fn.__code__.co_filename) as f:
        lines_with_import_str = ''.join([line for line in f.readlines() if 'import' in line])


    instructions = dis.get_instructions(lines_with_import_str)
    import_instructions = [__ for __ in instructions if 'IMPORT' in __.opname]

    imports = [ instr.argval for instr in import_instructions ]
    return imports
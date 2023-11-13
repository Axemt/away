from typing import Callable, Any
import inspect
import dis
import warnings

from .exceptions import EnsureException

from .exceptions import EnsureException

def __get_fn_source(source_fn: Callable[[Any], Any], __from_deco: bool=False):
    source_fn_arr = inspect.getsource(source_fn).split('\n')
    is_lambda = __is_lambda(source_fn)

    # skip line containing decorator, if it is decorated
    if __from_deco: source_fn_arr.pop(0)
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

def __get_external_dependencies(fn: Callable[[Any], Any], from_deco: bool=False) -> str:
    return __get_external_dependencies_rec(fn, set(), from_deco=from_deco)

def __get_external_dependencies_rec(fn: Callable[[Any], Any], closed_s: set[str], from_deco: bool=False) -> str:
    res = ''

    try:
        # FIXME: Fails for recursive functions defined inside another function or a class
        #         this looks like a problem on `inspect`'s end. (py3.10)
        outside_vars = inspect.getclosurevars(fn)
    except ValueError as e:
        raise Exception("A value error was raised in `inspect.getclosurevars`. This is likely because you are decorating a recursive function within a function/closure or class. For the meantime, use `builder.mirror_in_faas`: " + repr(e))

    # recursive functions with decorator always have the function itself as unbound
    is_recursive_deco = from_deco and fn.__name__ in outside_vars.unbound
    if (is_recursive_deco and len(outside_vars.unbound) > 1) or (not is_recursive_deco and len(outside_vars.unbound) > 0) :
        warnings.warn(f'The function {fn.__name__} contains unbound variables ({outside_vars.unbound})that cannot be resolved at build time. These may result in errors within the built OpenFaaS function.', SyntaxWarning)
    
    closed_s.add(fn.__name__)
    for group in [outside_vars.nonlocals, outside_vars.globals]:
        for var_name, var_obj in group.items():
            if var_name not in closed_s:
                closed_s.add(var_name)
                add = __expand_dependency_item(var_name, var_obj)
                res += add
                if inspect.isfunction(var_obj):
                    res += __get_external_dependencies_rec(var_obj, closed_s)

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

def __get_all_modules_mentioned(fn: Callable[[Any], Any]) -> [str]:

    with open(fn.__code__.co_filename) as f:
        lines_with_import_str = ''.join([line for line in f.readlines() if 'import' in line])


    instructions = dis.get_instructions(lines_with_import_str)
    import_instructions = [__ for __ in instructions if 'IMPORT' in __.opname]

    imports = [ instr.argval for instr in import_instructions ]
    return imports
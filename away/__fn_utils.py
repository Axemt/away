from typing import Callable, Any
import inspect
import dis

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
        raise Exception(f'Can only build stateless functions. The function {fn.__name__} ' + reason)


def __get_all_modules_mentioned(fn: Callable[[Any], Any]) -> [str]:

    with open(fn.__code__.co_filename) as f:
        lines_with_import_str = ''.join([line for line in f.readlines() if 'import' in line])


    instructions = dis.get_instructions(lines_with_import_str)
    import_instructions = [__ for __ in instructions if 'IMPORT' in __.opname]

    imports = [ instr.argval for instr in import_instructions ]
    return imports
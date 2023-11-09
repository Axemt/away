from typing import Callable, Any
import inspect

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
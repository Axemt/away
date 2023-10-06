def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer

def pack_args(args):
    # Arg packing/unpacking is dependent on the template used server-side to build
    #  the function. Provide this default, stop-gap solution
    if len(args) > 0: args=''.join([str(e) for e in args])

    return args
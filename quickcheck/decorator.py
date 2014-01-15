"""A decorator to make writing decorators simpler."""

import functools

__all__ = ['decorator']

def decorator(fn):
    """fn should be a function accepting a function as the first
    argument, followed by the arguments passed to it when used as a
    decorator. So, if it's intended to be used like:
    
    @fn(arg1, arg2):
    def wrapped(a, b):
        pass
    
    then after this, wrapped = fn(wrapped, arg1, arg2).
    """
    
    @functools.wraps(fn)
    def real_fn(*args, **kwargs):
        def wrapper(wrapped):
            return functools.wraps(wrapped)(fn(wrapped, *args, **kwargs))
        return wrapper
    return real_fn

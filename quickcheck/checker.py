"""Decorator for properties that will check them when called."""

from .decorator import decorator
from .interface import arbitrary, shrink

__all__ = ['QuickCheckError', 'quickcheck']

class QuickCheckError(Exception):
    pass

def _quickcheck_minimize(f, args, kwargs, used, exctype):
    """Given a function f, arguments to that function, and a set of
    quickcheck-produced values, attempt to minimize those values while
    preserving the exception type generated.
    """
    
    def arg_shrinks(arg):
        v = used[arg]
        for x in shrink(v):
            yield (arg, x)
    
    while True:
        for name, v in roundrobin(*(arg_shrinks(name) for name in used)):
            kwargs_new = kwargs.copy()
            kwargs_new.update(used)
            kwargs_new[name] = v
            try:
                f(*args, **kwargs_new)
            except exctype:
                # successful minimization!
                used[name] = v
                break
        else:
            # we never minimized anything, so
            break
    
    return used

@decorator
def quickcheck(f, tries=100, max_size=100, max_discard_ratio=10):
    def inner(*args, **kwargs):
        i = 0
        successes = 0
        discards = 0
        while successes < tries:
            # compute size
            size = i % max_size
            
            kwargs_new = kwargs.copy()
            used = {}
            for name, spec in f.__annotations__.items():
                if name in kwargs:
                    continue
                v = arbitrary(spec, size=size)
                kwargs_new[name] = v
                used[name] = v
            
            reemit_error = False
            try:
                ret = f(*args, **kwargs_new)
            except Exception as e:
                # attempt to minimize
                used = _quickcheck_minimize(f, args, kwargs, used, type(e))
                reemit_error = True
            
            if reemit_error:
                kwargs_new.update(used)
                try:
                    f(*args, **kwargs_new)
                except Exception as e:
                    raise QuickCheckError(used) from e

            if ret is None:
                raise RuntimeError("received None from quickcheckified function")
            
            i += 1
            if ret:
                successes += 1
            else:
                discards += 1
                if discards / (successes + 1) >= max_discard_ratio:
                    raise RuntimeError("too many tests discarded, aborting")
    
    return inner

"""Decorator for properties that will check them when called."""

from .decorator import decorator

__all__ = ['quickcheck']

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

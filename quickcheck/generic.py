"""Defines a way to create single-dispatch generic functions."""

from .decorator import decorator

__all__ = ['generic']

class SingleDispatchGeneric:
    """An object that looks like a function that chooses which
    implementation to use based on the first argument. Implementations
    can be registered with register(). The checker function is used to
    determine which implementation to use: if you call
    self.register(impl, typ) and then self(obj), impl will be used if
    and only if checker(obj, typ) is true. Good examples of checker
    are issubclass and isinstance.
    """
    def __init__(self, dispatcher, checker):
        self.dispatcher = dispatcher
        self.checker = checker
        self.implementations = []
    
    @decorator
    def register(fn, self, typ, checker=None):
        if not checker:
            checker = self.checker
        self.implementations.insert(0, (typ, fn, checker))
        return fn
        
    def __call__(self, obj, *args, **kwargs):
        for typ, impl, checker in self.implementations:
            try:
                if not checker(obj, typ):
                    continue
            except Exception:
                # some of our checkers will raise exceptions when mixed
                # like mixing isinstance and issubclass
                continue
            return self.dispatcher(impl, obj, *args, **kwargs)
        return self.dispatcher(None, obj, *args, **kwargs)

@decorator
def generic(dispatcher, checker):
    """Decorator for making a single-dispatch function out of a
    implementation dispatcher.
    """
    obj = SingleDispatchGeneric(dispatcher, checker)
    def inner(*args, **kwargs):
        return obj(*args, **kwargs)
    inner.register = obj.register
    return inner

"""Defines the arbitrary() and shrink() interfaces."""

from .generic import generic

import threading
import contextlib

__all__ = ['arbitrary', 'shrink']

thread_locals = threading.local()

@contextlib.contextmanager
def set_thread_local(name, val):
    """Small context manager to push a value on thread-locals, and pop
    it off when done.
    """
    was_set = hasattr(thread_locals, name)
    old_val = getattr(thread_locals, name, None)
    setattr(thread_locals, name, val)
    try:
        yield
    finally:
        if was_set:
            setattr(thread_locals, name, old_val)
        else:
            delattr(thread_locals, name)

@generic(issubclass)
def arbitrary(impl, typ, size=None):
    """Return an arbitrary, random value of the given type. Must be
    implemented for every type you want to use with pyquickcheck. If
    size is not given, arbitrary will attempt to infer it from calls
    to arbitrary higher up the stack.
    """
    if not impl:
        raise NotImplementedError("arbitrary({})".format(typ))
    
    def impl_with_size():
        try:
            return impl(typ, size=size)
        except TypeError:
            return impl(typ)
    
    SIZE_KEY = '_quickcheck_arbitrary_size'
    
    if size is not None:
        with set_thread_local(SIZE_KEY, size):
            return impl_with_size()
    
    if size is None and hasattr(thread_locals, SIZE_KEY):
        size = getattr(thread_locals, SIZE_KEY)
    
    return impl_with_size()

@generic(isinstance)
def shrink(impl, v):
    """Given a value, produce an iterable of simpler values based on
    that value. For example, shrinking a list should yield sublists,
    and lists where individual elements have been simplified. The
    default implementation simply produces an empty list. This should
    not continue to shrink values that were yielded earlier.
    """
    if impl:
        return impl(v)
    return []

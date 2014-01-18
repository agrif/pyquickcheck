"""Defines the arbitrary() and shrink() interfaces."""

from .generic import generic

import threading
import contextlib

__all__ = ['arbitrary', 'shrink', 'sized']

thread_locals = threading.local()

@contextlib.contextmanager
def thread_local(name, val=None):
    """Small context manager to push a value on thread-locals, and pop
    it off when done.
    """
    was_set = hasattr(thread_locals, name)
    old_val = getattr(thread_locals, name, None)
    if val is not None:
        setattr(thread_locals, name, val)
    try:
        if val is None:
            yield old_val
        else:
            yield val
    finally:
        if val is not None:
            if was_set:
                setattr(thread_locals, name, old_val)
            else:
                delattr(thread_locals, name)

def sized(size=None):
    """A context manager that implicitly sets the size parameter for
    arbitrary() for all code within its block. Yields the new default
    value of the size parameter. If given no arguments, or None as a
    single argument, this simply retrieves the default value."""
    return thread_local('_quickcheck_arbitrary_size', size)

@generic(issubclass)
def arbitrary(impl, typ, size=None):
    """Return an arbitrary, random value of the given type. Must be
    implemented for every type you want to use with pyquickcheck. If
    size is not given, arbitrary will attempt to infer it from calls
    to arbitrary higher up the stack.
    """
    if not impl:
        raise NotImplementedError("arbitrary({})".format(typ))
    
    def impl_with_size(effective_size):
        try:
            return impl(typ, size=effective_size)
        except TypeError:
            pass
        return impl(typ)
    
    with sized(size) as effective_size:
        return impl_with_size(effective_size)

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

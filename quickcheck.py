import functools
import random
import copy
import itertools
import sys
import threading
import contextlib

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

def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = itertools.cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = itertools.cycle(itertools.islice(nexts, pending))

def shrink_sequence(v, factory=None):
    """Yields 1-element smaller subsequences, and subsequences where 1
    element has been simplified. If provided, factory must produce a
    sequence out of something returned by v[i]. By default, factory(x)
    = type(v)([x]).
    """
    if factory is None:
        factory = lambda x: type(v)([x])
    
    for i in range(len(v)):
        vc = copy.copy(v)
        try:
            del vc[i]
        except TypeError:
            # immutable sequences. gotta love 'em.
            vc = vc[:i] + vc[i+1:]
        yield vc
    
    def makeshrinks(i):
        for s in shrink(v[i]):
            vc = copy.copy(v)
            try:
                vc[i] = s
            except TypeError:
                # immutable
                vc = vc[:i] + factory(s) + vc[i+1:]
            yield vc
    
    for x in roundrobin(*(makeshrinks(i) for i in range(len(v)))):
        yield x

class ArbitrarySpec:
    """Can be used in place of a type name in arbitrary(), for when
    you need more control over generated values.
    """
    def arbitrary(self, size=None):
        raise NotImplementedError("{}.arbitrary".format(self.__class__.__name__))

@arbitrary.register(ArbitrarySpec, checker=isinstance)
def arbitrary_spec(spec, size=None):
    if size is None:
        return spec.arbitrary()
    try:
        return spec.arbitrary(size=size)
    except TypeError:
        return spec.arbitrary()

class Constant(ArbitrarySpec):
    def __init__(self, v):
        self.v = v
    
    def arbitrary(self):
        return self.v

class Float(ArbitrarySpec):
    def __init__(self, min=None, max=None, add_sign=True, distribution=lambda: random.random()):
        self.min = min
        self.max = max
        self.add_sign = add_sign
        self.distribution = distribution
    
    def arbitrary(self, size=0xffff):
        mult = size
        add = 0.0
        add_sign = self.add_sign
        
        if self.min is not None:
            # grow up
            add_sign = False
            add = self.min
            if self.max is not None:
                # but only until max
                mult = self.max - self.min
        elif self.max is not None:
            # grow down
            add_sign = False
            add = self.max
            mult = - size
        
        if add_sign:
            mult *= random.choice([-1, 1])
        
        # clamp mult to size
        if mult > size:
            mult = size
        if mult < -size:
            mult = -size
        
        while True:
            dist = self.distribution()
            if add_sign:
                dist = abs(dist)
            
            f = dist * mult + add
            
            if self.max is not None and f > self.max:
                continue
            if self.min is not None and f < self.min:
                continue
            
            return f

@arbitrary.register(float)
def arbitrary_float(_):
    return arbitrary(Float())

@shrink.register(float)
def shrink_float(v):
    if v < 0:
        yield -v
    
    x = float(int(v))
    if abs(x) < abs(v):
        yield x

class Integer(Float):
    def arbitrary(self, size=0xffff):
        return int(round(super().arbitrary(size=size)))

@arbitrary.register(int)
def arbitrary_int(_):
    return arbitrary(Integer())

@shrink.register(int)
def shrink_int(v):
    if v < 0:
        yield -v
    if v != 0:
        yield 0
    
    i = v
    while True:
        i = i // 2
        if abs(v - i) < abs(v):
            yield v - i
        else:
            break

# bool needs to come *after* int, as bool is a subtype of int
# which is totally awesome and not at all terrible

@arbitrary.register(bool)
def arbitrary_bool(_):
    return random.choice([True, False])

@shrink.register(bool)
def shrink_bool(v):
    if v:
        yield False

class Char(ArbitrarySpec):
    # turns out, this is hard
    # http://stackoverflow.com/a/1477572
    # from table 3-7 of the Unicode Standard 5.0.0
    
    def __init__(self):
        self.first_values = self.byte_range(0x00, 0x7f) + self.byte_range(0xc2, 0xf4)
        self.trailing_values = self.byte_range(0x80, 0xbf)

    @staticmethod
    def byte_range(first, last):
        return list(range(first, last + 1))

    def arbitrary(self):
        byte_range = self.byte_range
        first = random.choice(self.first_values)
        ret = b''
        if first <= 0x7f:
            ret = bytes([first])
        elif first <= 0xDF:
            ret = bytes([first, random.choice(self.trailing_values)])
        elif first == 0xE0:
            ret = bytes([first, random.choice(byte_range(0xA0, 0xBF)), random.choice(self.trailing_values)])
        elif first == 0xED:
            ret = bytes([first, random.choice(byte_range(0x80, 0x9F)), random.choice(self.trailing_values)])
        elif first <= 0xEF:
            ret = bytes([first, random.choice(self.trailing_values), random.choice(self.trailing_values)])
        elif first == 0xF0:
            ret = bytes([first, random.choice(byte_range(0x90, 0xBF)), random.choice(self.trailing_values), random.choice(self.trailing_values)])
        elif first <= 0xF3:
            ret = bytes([first, random.choice(self.trailing_values), random.choice(self.trailing_values), random.choice(self.trailing_values)])
        elif first == 0xF4:
            ret = bytes([first, random.choice(byte_range(0x80, 0x8F)), random.choice(self.trailing_values), random.choice(self.trailing_values)])
        return str(ret, 'utf-8')

class List(ArbitrarySpec):
    def __init__(self, elspec):
        self.elspec = elspec
    
    def arbitrary(self, size=30):
        l = arbitrary(Integer(min=0), size=size)
        return [arbitrary(self.elspec) for _ in range(l)]

@shrink.register(list)
def shrink_list(v):
    return shrink_sequence(v)

@shrink.register(tuple)
def shrink_tuple(v):
    def shrinki(i):
        for s in shrink(v[i]):
            yield v[:i] + (s,) + v[i+1:]
    return roundrobin(*(shrinki(i) for i in range(len(v))))

@arbitrary.register(str)
def arbitrary_str(_):
    return "".join(arbitrary(List(Char())))

@shrink.register(str)
def shrink_str(v):
    # we need this because type(v[0]) == str
    # (characters are represented as single-character strings!)
    if len(v) == 1:
        return (chr(x) for x in shrink(ord(v)))
    return shrink_sequence(v, factory=lambda x: x)

@arbitrary.register(bytes)
def arbitrary_bytes(_):
    return bytes(arbitrary(List(Integer(min=0x00, max=0xff))))

@shrink.register(bytes)
def shrink_bytes(v):
    return shrink_sequence(v)

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

if __name__ == '__main__':
    import code
    code.interact(local=locals())

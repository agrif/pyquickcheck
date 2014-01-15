"""Default implementations for arbitrary() and shrink()."""

from .interface import arbitrary, shrink
from .decorator import decorator

__all__ = ['roundrobin', 'shrink_sequence']

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

# make sure we export all ArbitrarySpec subclasses
for name, val in list(locals().items()):
    if type(val) == type and issubclass(val, ArbitrarySpec):
        __all__.append(name)

"""Default implementations for arbitrary() and shrink()."""

from .interface import arbitrary, shrink
from .decorator import decorator
from .roundrobin import roundrobin

import random
import math
import copy

__all__ = ['shrink_sequence']

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

class Choice(ArbitrarySpec):
    def __init__(self, first, *values):
        self.values = [first] + list(values)
    
    def arbitrary(self):
        return random.choice(self.values)

class Any(ArbitrarySpec):
    def __init__(self, first, *specs):
        self.specs = [first] + list(specs)
    
    def arbitrary(self):
        return arbitrary(random.choice(self.specs))

class Maybe(ArbitrarySpec):
    def __init__(self, spec, none_chance=0.1):
        self.spec = spec
        self.none_chance = none_chance
    
    def arbitrary(self):
        if random.random() < self.none_chance:
            return None
        return arbitrary(self.spec)

@arbitrary.register(None, checker=lambda a, b: a is b)
def arbitrary_none(_):
    return None

class Float(ArbitrarySpec):
    def __init__(self, min=None, max=None, add_sign=True, distribution=lambda: random.random()):
        self.min = min
        self.max = max
        self.add_sign = add_sign
        self.distribution = distribution
        
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("specified min is greater than specified max")
    
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
        i = math.trunc(i / 2)
        if abs(v - i) < abs(v):
            yield v - i
        else:
            break

# bool needs to come *after* int, as bool is a subtype of int
# which is totally awesome and not at all terrible

@arbitrary.register(bool)
def arbitrary_bool(_):
    return arbitrary(Choice(True, False))

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
    def __init__(self, elspec, lengthmin=0, lengthmax=None):
        if lengthmin is None:
            lengthmin = 0
        if lengthmax is not None and lengthmin > lengthmax:
            raise ValueError("length minimum is greater than length maximum")
        if not lengthmin >= 0:
            raise ValueError("length minimum is not greater than 0")
        if lengthmax is not None and not lengthmax >= 0:
            raise ValueError("length maximum is not greater than 0")
        self.lengthmin = lengthmin
        self.lengthmax = lengthmax
        self.elspec = elspec
    
    def arbitrary(self, size=30):
        l = arbitrary(Integer(min=self.lengthmin, max=self.lengthmax), size=size)
        return [arbitrary(self.elspec) for _ in range(l)]

@arbitrary.register(list, checker=isinstance)
def arbitrary_list(v):
    return arbitrary(List(Any(*v)))

@shrink.register(list)
def shrink_list(v):
    return shrink_sequence(v)

class Tuple(ArbitrarySpec):
    def __init__(self, *specs):
        self.specs = list(specs)
    
    def arbitrary(self):
        return tuple(arbitrary(spec) for spec in self.specs)

@arbitrary.register(tuple, checker=isinstance)
def arbitrary_tuple(v):
    return arbitrary(Tuple(*v))

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

# make sure we export all ArbitrarySpec subclasses
for name, val in list(locals().items()):
    if type(val) == type and issubclass(val, ArbitrarySpec):
        __all__.append(name)

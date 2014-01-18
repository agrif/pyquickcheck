import quickcheck as qc
import unittest

class LeafSpec(qc.ArbitrarySpec):
    def __init__(self, simple_only=False):
        self.simple_only = simple_only
    
    def arbitrary(self):
        specs = [float, int, bool, str, bytes]
        if not self.simple_only:
            specs.append(qc.arbitrary(qc.Float))
            specs.append(qc.arbitrary(qc.Integer))
            specs.append(qc.Char())
        return qc.arbitrary(qc.Choice(*specs))        

@qc.arbitrary.register(qc.Float)
def arbitrary_float_spec(_):
    min = None
    if qc.arbitrary(bool):
        min = qc.arbitrary(float)
    max = None
    if qc.arbitrary(bool):
        max = qc.arbitrary(float)
    if min is not None and max is not None and min > max:
        max, min = min, max
    add_sign = qc.arbitrary(bool)
    return qc.Float(min=min, max=max, add_sign=add_sign)

@qc.arbitrary.register(qc.Integer)
def arbitrary_int_spec(_):
    min = None
    if qc.arbitrary(bool):
        min = qc.arbitrary(int)
    max = None
    if qc.arbitrary(bool):
        max = qc.arbitrary(int)
    if min is not None and max is not None and min > max:
        max, min = min, max
    add_sign = qc.arbitrary(bool)
    return qc.Integer(min=min, max=max, add_sign=add_sign)

class TestSpecs(unittest.TestCase):
    @qc.quickcheck()
    def test_spec(self, spec: LeafSpec(simple_only=True)):
        self.assertIsInstance(qc.arbitrary(spec), spec)
        return True
    
    @qc.quickcheck()
    def test_constant_spec(self, subspec: LeafSpec()):
        v = qc.arbitrary(subspec)
        vp = qc.arbitrary(qc.Constant(v))
        self.assertEqual(v, vp)
        return True
    
    @qc.quickcheck()
    def test_choice_spec(self, subspecs: qc.List(LeafSpec(), lengthmin=1)):
        vals = [qc.arbitrary(spec) for spec in subspecs]
        v = qc.arbitrary(qc.Choice(*vals))
        self.assertIn(v, vals)
        return True
    
    @qc.quickcheck()
    def test_any_spec(self, subspecs: qc.List(LeafSpec(simple_only=True), lengthmin=1)):
        val = qc.arbitrary(qc.Any(*subspecs))
        assert any(isinstance(val, t) for t in subspecs)
        return True
    
    @qc.quickcheck()
    def test_maybe_spec(self, spec: LeafSpec(simple_only=True)):
        v = qc.arbitrary(qc.Maybe(spec))
        if v is not None:
            self.assertIsInstance(v, spec)
        return True
    
    @qc.quickcheck()
    def test_list_spec(self, subspecs: qc.List(LeafSpec(simple_only=True), lengthmin=1)):
        val = qc.arbitrary(list(subspecs))
        for v in val:
            assert any(isinstance(v, t) for t in subspecs)
        return True
    
    @qc.quickcheck()
    def test_list_len_spec(self, min: qc.Maybe(qc.Integer(min=0)), max: qc.Maybe(qc.Integer(min=0))):
        if min is not None and max is not None and min > max:
            max, min = min, max
        v = qc.arbitrary(qc.List(None, lengthmin=min, lengthmax=max))
        if min is not None:
            self.assertGreaterEqual(len(v), min)
        if max is not None:
            self.assertLessEqual(len(v), max)
        return True
    
    @qc.quickcheck()
    def test_tuple_spec(self, subspecs: qc.List(LeafSpec(simple_only=True))):
        val = qc.arbitrary(tuple(subspecs))
        self.assertEqual(len(val), len(subspecs))
        for v, spec in zip(val, subspecs):
            self.assertIsInstance(v, spec)
        return True
    
    @qc.quickcheck()
    def test_float_spec(self, spec: qc.Float):
        v = qc.arbitrary(spec)
        if spec.max is not None:
            self.assertLessEqual(v, spec.max)
        if spec.min is not None:
            self.assertGreaterEqual(v, spec.min)
        return True

    @qc.quickcheck()
    def test_int_spec(self, spec: qc.Integer):
        v = qc.arbitrary(spec)
        if spec.max is not None:
            self.assertLessEqual(v, spec.max)
        if spec.min is not None:
            self.assertGreaterEqual(v, spec.min)
        return True

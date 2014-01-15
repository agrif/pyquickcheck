import quickcheck as qc
import unittest

@qc.arbitrary.register(qc.ArbitrarySpec)
def arbitrary_spec(_):
    specs = [float, int, bool, str, bytes]
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
    def test_spec(self, spec: qc.ArbitrarySpec):
        if isinstance(spec, qc.ArbitrarySpec):
            return False
        self.assertIsInstance(qc.arbitrary(spec), spec)
        return True
    
    @qc.quickcheck()
    def test_constant_spec(self, subspec: qc.ArbitrarySpec):
        v = qc.arbitrary(subspec)
        vp = qc.arbitrary(qc.Constant(v))
        self.assertEqual(v, vp)
        return True
    
    @qc.quickcheck()
    def test_choice_spec(self, subspecs: qc.List(qc.ArbitrarySpec)):
        if len(subspecs) == 0:
            return False
        vals = [qc.arbitrary(spec) for spec in subspecs]
        v = qc.arbitrary(qc.Choice(*vals))
        self.assertIn(v, vals)
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

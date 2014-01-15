import quickcheck as qc
import unittest

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
    def test_float_spec(self, spec: qc.Float):
        v = qc.arbitrary(spec)
        if spec.max is not None:
            assert v <= spec.max
        if spec.min is not None:
            assert v >= spec.min
        return True

    @qc.quickcheck()
    def test_int_spec(self, spec: qc.Integer):
        v = qc.arbitrary(spec)
        if spec.max is not None:
            assert v <= spec.max
        if spec.min is not None:
            assert v >= spec.min
        return True

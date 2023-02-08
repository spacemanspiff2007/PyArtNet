from pyartnet.base.seq_counter import SequenceCounter


def test_seq():
    s = SequenceCounter()
    assert s.value == 0
    assert s.value == 1
    assert s.value == 2

    s._ctr = 254
    assert s.value == 254
    assert s.value == 255
    assert s.value == 0
    assert s.value == 1


def test_seq_artnet():
    s = SequenceCounter(1)
    assert s.value == 1
    assert s.value == 2

    s._ctr = 254
    assert s.value == 254
    assert s.value == 255
    assert s.value == 1


def test_seq_const():
    s = SequenceCounter(0, 0)
    assert s.value == 0
    assert s.value == 0
    assert s.value == 0


def test_repr():
    s = SequenceCounter()
    assert repr(s) == '<SequenceCounter 0>'
    assert repr(s) == '<SequenceCounter 0>'
    assert s.value == 0
    assert repr(s) == '<SequenceCounter 1>'

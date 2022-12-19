from typing import Iterable, Optional
from unittest.mock import Mock

from pyartnet.node.channel import Channel


def to_buf(c: Channel, v: Iterable[int], buf: Optional[bytearray] = None) -> bytearray:
    c.set_values(v)
    assert c.get_values() == list(v)

    if buf is None:
        buf = bytearray(b'\x00' * 5)
    c.to_buffer(buf)
    return buf


def test_channel_1b_values_single():
    universe = Mock()
    universe.output_correction = None

    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]
    assert to_buf(a, [255]) == b'\xff\x00\x00\x00\x00'

    b = Channel(universe, 3, 1)
    assert to_buf(b, [255]) == b'\x00\x00\xff\x00\x00'

    c = Channel(universe, 5, 1)

    buf = bytearray(b'\x00' * 5)
    to_buf(a, [0xF0], buf=buf)
    to_buf(b, [0xFF], buf=buf)
    to_buf(c, [0x0F], buf=buf)
    assert buf == b'\xf0\x00\xff\x00\x0f'


def test_channel_1b_values_multiple():
    universe = Mock()
    universe.output_correction = None

    c = Channel(universe, 1, 3)
    assert c.get_values() == [0, 0, 0]
    assert to_buf(c, [128, 0, 255]) == b'\x80\x00\xff\x00\x00'

    c = Channel(universe, 3, 3)
    assert to_buf(c, [128, 0, 255]) == b'\x00\x00\x80\x00\xff'


def test_channel_2b_values_single():
    universe = Mock()
    universe.output_correction = None

    c = Channel(universe, 1, 1, byte_size=2)
    assert c.get_values() == [0]
    assert to_buf(c, [65535]) == b'\xff\xff\x00\x00\x00'
    assert to_buf(c, [0xF00F]) == b'\x0f\xf0\x00\x00\x00'

    c = Channel(universe, 3, 1, byte_size=2)
    assert to_buf(c, [0xF00F]) == b'\x00\x00\x0f\xf0\x00'

    c = Channel(universe, 4, 1, byte_size=2)
    assert to_buf(c, [0xF00F]) == b'\x00\x00\x00\x0f\xf0'

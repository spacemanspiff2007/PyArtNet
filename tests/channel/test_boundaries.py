from unittest.mock import Mock

import pytest

from pyartnet.errors import ChannelOutOfUniverseError, ChannelValueOutOfBounds
from pyartnet.node import Universe
from pyartnet.node.channel import Channel


def test_channel_boundaries():
    univ = Mock()

    with pytest.raises(ChannelOutOfUniverseError) as r:
        Channel(univ, 0, 1)
    assert str(r.value) == 'Start position of channel out of universe (1..512): 0'
    Channel(univ, 1, 1)

    with pytest.raises(ChannelOutOfUniverseError) as r:
        Channel(univ, 513, 1)
    assert str(r.value) == 'Start position of channel out of universe (1..512): 513'
    Channel(univ, 512, 1)

    with pytest.raises(ChannelOutOfUniverseError) as r:
        Channel(univ, 512, 2)
    assert str(r.value) == 'End position of channel out of universe (1..512): start: 512 width: 2 * 1bytes -> 513'
    Channel(univ, 511, 2)

    # 16 Bit Channels
    with pytest.raises(ChannelOutOfUniverseError) as r:
        Channel(univ, 512, 1, byte_size=2)
    assert str(r.value) == 'End position of channel out of universe (1..512): start: 512 width: 1 * 2bytes -> 513'
    Channel(univ, 511, 1, byte_size=2)


def test_set_value_invalid():
    universe = Mock()
    universe.output_correction = None

    b = Channel(universe, 1, 1)
    with pytest.raises(ChannelValueOutOfBounds) as e:
        b.set_values([256])
    assert str(e.value) == 'Channel value out of bounds! 0 <= 256 <= 255'
    b.set_values([255])

    b = Channel(universe, 1, 1, byte_size=2)
    with pytest.raises(ChannelValueOutOfBounds) as e:
        b.set_values([65536])
    assert str(e.value) == 'Channel value out of bounds! 0 <= 65536 <= 65535'
    b.set_values([65535])

    b = Channel(universe, 3, 3)
    with pytest.raises(ChannelValueOutOfBounds) as e:
        b.set_values([0, 0, 256])
    assert str(e.value) == 'Channel value out of bounds! 0 <= 256 <= 255'
    b.set_values([0, 0, 255])

    b = Channel(universe, 3, 3, byte_size=2)
    with pytest.raises(ChannelValueOutOfBounds) as e:
        b.set_values([0, 0, 65536])
    assert str(e.value) == 'Channel value out of bounds! 0 <= 65536 <= 65535'
    b.set_values([0, 0, 65535])


def test_values_add_channel(universe: Universe):
    u = universe.add_channel(1, 2, byte_size=3, byte_order='big')
    assert u._start == 1
    assert u._width == 2
    assert u._byte_size == 3
    assert u._byte_order == 'big'

    u = universe.add_channel(10, 5, byte_size=2, byte_order='little')
    assert u._start == 10
    assert u._width == 5
    assert u._byte_size == 2
    assert u._byte_order == 'little'

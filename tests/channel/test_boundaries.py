from unittest.mock import Mock

import pytest

from pyartnet.base.channel import Channel
from pyartnet.errors import ChannelOutOfUniverseError, \
    ChannelValueOutOfBoundsError, ValueCountDoesNotMatchChannelWidthError


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


def get_node_universe_mock():
    node = Mock()
    node._process_every = 0.001

    universe = Mock()
    universe._node = node
    universe.output_correction = None
    return node, universe


@pytest.mark.parametrize(
    ('width', 'byte_size', 'invalid', 'valid'),
    ((1, 1, -1, 255), (1, 1, 256, 255), (3, 1, 256, 255),
     (1, 2, -1, 65535), (1, 2, 65536, 65535), (3, 2, 65536, 65535), ))
def test_set_invalid(width, byte_size, invalid, valid):
    node, universe = get_node_universe_mock()

    invalid_values = [0] * (width - 1) + [invalid]
    valid_values = [0] * (width - 1) + [valid]

    # test set_values
    c = Channel(universe, 1, width, byte_size=byte_size)
    with pytest.raises(ChannelValueOutOfBoundsError) as e:
        c.set_values(invalid_values)
    assert str(e.value) == f'Channel value out of bounds! 0 <= {invalid:d} <= {valid}'
    c.set_values(valid_values)

    # test set_fade
    c = Channel(universe, 1, width, byte_size=byte_size)
    with pytest.raises(ChannelValueOutOfBoundsError) as e:
        c.set_fade(invalid_values, 100)
    assert str(e.value) == f'Target value out of bounds! 0 <= {invalid:d} <= {valid}'
    c.set_fade(valid_values, 100)


async def test_set_missing():
    node, universe = get_node_universe_mock()

    c = Channel(universe, 1, 1)
    with pytest.raises(ValueCountDoesNotMatchChannelWidthError) as e:
        c.set_values([0, 0, 255])
    assert str(e.value) == 'Not enough fade values specified, expected 1 but got 3!'

    with pytest.raises(ValueCountDoesNotMatchChannelWidthError) as e:
        c.set_fade([0, 0, 255], 0)
    assert str(e.value) == 'Not enough fade values specified, expected 1 but got 3!'

    c = Channel(universe, 1, 3)
    with pytest.raises(ValueCountDoesNotMatchChannelWidthError) as e:
        c.set_values([0, 255])
    assert str(e.value) == 'Not enough fade values specified, expected 3 but got 2!'

    with pytest.raises(ValueCountDoesNotMatchChannelWidthError) as e:
        c.set_fade([0, 255], 0)
    assert str(e.value) == 'Not enough fade values specified, expected 3 but got 2!'

import pytest

from pyartnet import errors
from pyartnet.node import Universe


def test_exceptions(universe: Universe):
    universe.add_channel(1, 1)

    with pytest.raises(errors.ChannelExistsError) as e:
        universe.add_channel(1, 1)
    assert str(e.value) == 'Channel "1/1" does already exist in the universe!'

    # Channels
    with pytest.raises(errors.ChannelNotFoundError) as e:
        universe.get_channel('2')
    assert str(e.value) == 'Channel "2" not found in the universe!'
    with pytest.raises(errors.ChannelNotFoundError) as e:
        _ = universe['2']
    assert str(e.value) == 'Channel "2" not found in the universe!'

    # Overlapping channels
    universe.add_channel(10, 3)

    with pytest.raises(errors.OverlappingChannelError) as e:
        universe.add_channel(1, 3)
    assert str(e.value) == 'New channel 1/3 is overlapping with channel 1/1!'

    with pytest.raises(errors.OverlappingChannelError):
        universe.add_channel(9, 2)
    with pytest.raises(errors.OverlappingChannelError):
        universe.add_channel(12, 1)
    with pytest.raises(errors.OverlappingChannelError):
        universe.add_channel(8, 20)


def test_universe_resize(universe: Universe):
    universe.add_channel(1, 1)
    assert universe._data == b'\x00\x00'

    universe.add_channel(6, 1)
    assert universe._data == b'\x00\x00\x00\x00\x00\x00'

    universe._channels.popitem()
    universe.add_channel(2, 1)
    assert universe._data == b'\x00\x00'

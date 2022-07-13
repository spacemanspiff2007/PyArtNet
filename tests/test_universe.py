import pytest

from pyartnet import DmxUniverse, errors

from .conftest import PatchedAnimationNode


def test_channel_add(artnet_node: PatchedAnimationNode):
    universe = DmxUniverse(artnet_node)

    universe.add_channel(2, 1)
    assert universe.highest_channel == 2
    assert universe.data == b'\x00\x00'

    universe.add_channel(3, 1)
    assert universe.highest_channel == 4
    assert universe.data == b'\x00\x00\x00\x00'

    universe.add_channel(4, 1)
    assert universe.highest_channel == 4
    assert universe.data == b'\x00\x00\x00\x00'

    universe.add_channel(7, 1)
    assert universe.highest_channel == 8
    assert universe.data == b'\x00\x00\x00\x00\x00\x00\x00\x00'


def test_exceptions(artnet_node: PatchedAnimationNode):
    universe = DmxUniverse(artnet_node)
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


def test_container(artnet_node: PatchedAnimationNode):
    universe = DmxUniverse(artnet_node)

    universe.add_channel(1, 1)
    assert len(universe) == 1

    universe.add_channel(2, 1)
    assert len(universe) == 2

    _ = universe['1/1']
    _ = universe['2/1']

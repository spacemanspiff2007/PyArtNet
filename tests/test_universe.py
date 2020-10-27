from pyartnet import DmxUniverse
from .conftest import PatchedArtNetNode


def test_channel_add(artnet_node: PatchedArtNetNode):
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

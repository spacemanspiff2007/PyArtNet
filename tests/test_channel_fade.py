from unittest.mock import Mock

from pyartnet.base import Channel
from pyartnet.base.channel_fade import ChannelBoundFade


def test_repr():
    universe = Mock()
    universe.output_correction = None

    a = Channel(universe, 1, 2)

    a = ChannelBoundFade(a, [])
    assert repr(a) == '<ChannelBoundFade channel=1/2, is_done=False>'

    a.is_done = True
    assert repr(a) == '<ChannelBoundFade channel=1/2, is_done=True>'

    a = ChannelBoundFade(a, [])
    a.channel = None
    assert repr(a) == '<ChannelBoundFade channel=None, is_done=False>'

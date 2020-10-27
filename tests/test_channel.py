import pytest, time
from unittest.mock import Mock

from .conftest import PatchedArtNetNode


@pytest.mark.asyncio
async def test_channel_single_step(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 0)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [255]

    channel.add_fade([0], 0)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0]

    assert running_artnet_node.values == [[255, 0], [0, 0]]


@pytest.mark.asyncio
async def test_channel_double_step(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [255]

    channel.add_fade([0], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0]

    assert running_artnet_node.values == [[128, 0], [255, 0], [128, 0], [0, 0]]


@pytest.mark.asyncio
async def test_channel_with_3(running_artnet_node: PatchedArtNetNode):

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 3)

    channel.add_fade([100, 150, 200], 5)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [100, 150, 200]

    assert running_artnet_node.values == [
        [20, 30, 40, 0], [40, 60, 80, 0], [60, 90, 120, 0], [80, 120, 160, 0], [100, 150, 200, 0]
    ]
    running_artnet_node.values.clear()

    channel.add_fade([0, 0, 0], 2)
    await channel.wait_till_fade_complete()
    assert channel.get_channel_values() == [0, 0, 0]

    assert running_artnet_node.values == [[50, 75, 100, 0], [0, 0, 0, 0]]


@pytest.mark.asyncio
async def test_channel_cb(running_artnet_node: PatchedArtNetNode):
    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.callback_fade_finished = cb_f = Mock()
    channel.callback_value_changed = cb_v = Mock()

    channel.add_fade([100], 5)
    await channel.wait_till_fade_complete()

    assert cb_f.call_count == 1
    assert cb_v.call_count == 5


@pytest.mark.asyncio
async def test_channel_wait_till_complete(running_artnet_node: PatchedArtNetNode):
    # under windows we can't use the quick ms sleeps
    running_artnet_node.sleep_time = 0.05

    universe = running_artnet_node.add_universe(0)
    channel = universe.add_channel(1, 1)

    channel.add_fade([255], 500)

    start = time.time()
    await channel.wait_till_fade_complete()
    duration = time.time() - start

    assert channel.get_channel_values() == [255]
    assert 0.4 <= duration <= 0.6

import asyncio
from time import monotonic

from pyartnet.base import BaseUniverse
from pyartnet.base.channel import Channel
from tests.conftest import STEP_MS, TestingNode


async def test_channel_await(node: TestingNode, universe: BaseUniverse, caplog):
    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]

    a.set_fade([255], 200)

    start = monotonic()
    await asyncio.wait_for(a, 1)
    stop = monotonic()

    assert stop - start >= 0.2


async def test_single_step(node: TestingNode, universe: BaseUniverse, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]

    a.set_fade([255], 0)
    assert a.get_values() == [0]

    assert list(caplog.messages) == [
        'Added fade with 1 steps:',
        'CH 1: 000 -> 255 | step: +255.0'
    ]

    await node.sleep_steps(2)
    assert a.get_values() == [255]
    assert node.data == ['ff']

    await node.wait_for_task_finish()
    assert node.data == ['ff']


async def test_single_fade(node: TestingNode, universe: BaseUniverse, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]

    a.set_fade([2], 2 * STEP_MS)
    assert a.get_values() == [0]

    assert list(caplog.messages) == [
        'Added fade with 2 steps:',
        'CH 1: 000 -> 002 | step:  +1.0'
    ]

    await node.sleep_steps(3)
    assert a.get_values() == [2]
    assert node.data == ['01', '02']

    await node.wait_for_task_finish()
    assert node.data == ['01', '02']


async def test_tripple_fade(node: TestingNode, universe: BaseUniverse, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 3)
    assert a.get_values() == [0, 0, 0]

    a.set_fade([3, 6, 9], 3 * STEP_MS)
    assert a.get_values() == [0, 0, 0]

    assert list(caplog.messages) == [
        'Added fade with 3 steps:',
        'CH 1: 000 -> 003 | step:  +1.0',
        'CH 2: 000 -> 006 | step:  +2.0',
        'CH 3: 000 -> 009 | step:  +3.0'
    ]

    await node.sleep_steps(4)
    assert a.get_values() == [3, 6, 9]
    assert node.data == ['010203', '020406', '030609']

    await node.wait_for_task_finish()
    assert node.data == ['010203', '020406', '030609']


async def test_fade_await(node: TestingNode, universe: BaseUniverse, caplog):
    caplog.set_level(0)

    channel = Channel(universe, 1, 1)
    assert channel.get_values() == [0]

    async def check_no_wait_time_when_no_fade():
        start = monotonic()
        for _ in range(1000):
            assert not await channel
        assert monotonic() - start < 0.001

    await check_no_wait_time_when_no_fade()

    channel.set_fade([2], 2 * STEP_MS)
    assert channel.get_values() == [0]

    assert list(caplog.messages) == [
        'Added fade with 2 steps:',
        'CH 1: 000 -> 002 | step:  +1.0'
    ]

    assert channel._current_fade is not None
    assert await channel
    assert channel._current_fade is None
    assert channel.get_values() == [2]
    assert node.data == ['01', '02']

    await check_no_wait_time_when_no_fade()

    channel.set_fade([10], 2 * STEP_MS)

    assert channel._current_fade is not None
    await channel
    assert channel._current_fade is None
    assert node.data == ['01', '02', '06', '0a']

    await check_no_wait_time_when_no_fade()
    await node.wait_for_task_finish()


async def test_up_down_fade(node: TestingNode, universe: BaseUniverse, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 1)
    for _ in range(5):
        node.data.clear()
        assert a.get_values() == [0]

        a.set_fade([255], 2 * STEP_MS)
        assert a.get_values() == [0]

        await a

        assert a.get_values() == [255]
        assert node.data == ['80', 'ff']

        # Fade down
        a.set_fade([0], 2 * STEP_MS)
        assert a.get_values() == [255]

        await a

        assert a.get_values() == [0]
        assert node.data == ['80', 'ff', '80', '00']

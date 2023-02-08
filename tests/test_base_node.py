from time import monotonic

import pytest

from pyartnet.base import BaseUniverse
from pyartnet.base.channel import Channel
from pyartnet.errors import DuplicateUniverseError
from tests.conftest import STEP_MS, TestingNode


def test_universe_add_get(node: TestingNode):
    for i in (1.3, -1):
        with pytest.raises(ValueError, match='BaseUniverse must be an int >= 0!'):
            node.add_universe(i)

        with pytest.raises(ValueError, match='BaseUniverse must be an int >= 0!'):
            node.get_universe(i)

    u = node.add_universe()
    assert len(node) == 1
    assert node.get_universe(0) is u
    assert node[0] is u

    # Duplicate
    with pytest.raises(DuplicateUniverseError, match='BaseUniverse 0 does already exist!'):
        node.add_universe()

    # Check that the nodes are ascending
    node.add_universe(50)
    node.add_universe(3)

    assert len(node) == 3
    assert node._universes == (
        node.get_universe(0), node.get_universe(3), node.get_universe(50)
    )


async def test_fade_await(node: TestingNode, universe: BaseUniverse, caplog):
    async def check_no_wait_time_when_no_fade():
        start = monotonic()
        for _ in range(1000):
            assert not await node
        assert monotonic() - start < 0.001

    async def check_wait_time_when_fade(steps: int):
        start = monotonic()
        await node
        assert monotonic() - start >= ((steps - 1) * STEP_MS) / 1000

    caplog.set_level(0)

    channel = Channel(universe, 1, 1)

    await check_no_wait_time_when_no_fade()

    channel.add_fade([2], 2 * STEP_MS)
    assert channel.get_values() == [0]

    assert list(caplog.messages) == [
        'Added fade with 2 steps:',
        'CH 1: 000 -> 002 | step:  +1.0'
    ]

    assert channel._current_fade is not None
    await check_wait_time_when_fade(2)
    assert channel._current_fade is None
    assert channel.get_values() == [2]
    assert node.data == ['01', '02']

    await check_no_wait_time_when_no_fade()

    channel.add_fade([10], 2 * STEP_MS)

    assert channel._current_fade is not None
    await check_wait_time_when_fade(2)
    assert channel._current_fade is None
    assert node.data == ['01', '02', '05', '0a']

    await check_no_wait_time_when_no_fade()
    await node.wait_for_task_finish()

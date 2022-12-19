from pyartnet.node import Universe
from pyartnet.node.channel import Channel
from tests.conftest import STEP_MS, TestingNode


async def test_single_fade(node: TestingNode, universe: Universe, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]

    a.add_fade([2], 2 * STEP_MS)
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


async def test_tripple_fade(node: TestingNode, universe: Universe, caplog):
    caplog.set_level(0)

    a = Channel(universe, 1, 3)
    assert a.get_values() == [0, 0, 0]

    a.add_fade([3, 6, 9], 3 * STEP_MS)
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

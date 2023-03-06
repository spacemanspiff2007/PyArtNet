from pyartnet.base import BaseUniverse
from pyartnet.base.channel import Channel
from tests.conftest import TestingNode


async def test_channel_set_values(node: TestingNode, universe: BaseUniverse, caplog):
    a = Channel(universe, 1, 1)
    assert a.get_values() == [0]

    a.set_values([255])
    assert a.get_values() == [255]

    await node.sleep_steps(2)
    assert node.data == ['ff']

    a.set_values([125])
    assert a.get_values() == [125]

    await node.sleep_steps(1)
    assert node.data == ['ff', '7d']

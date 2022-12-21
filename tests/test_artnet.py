import logging
from asyncio import sleep
from unittest.mock import Mock

import pytest

import pyartnet.node
from pyartnet import ArtNetNode, KiNetNode, SacnNode
from tests.conftest import TestingNode


@pytest.fixture(autouse=True)
def patch_artnet_node(monkeypatch):
    monkeypatch.setattr(pyartnet.node.base_node, 'socket', Mock())


@pytest.mark.parametrize('cls', [ArtNetNode, SacnNode, KiNetNode])
async def test_arnet(node: TestingNode, caplog, cls):
    caplog.set_level(logging.DEBUG)

    n = cls('ip', 9999)
    u = n.add_universe(1)
    c = u.add_channel(1, 1)

    c.set_values([5])
    await sleep(0.1)

    c.add_fade([250], 700)
    await sleep(1.2)

    for rec in caplog.records:
        assert rec.levelno <= 10

    # for msg in caplog.messages:
    #     print(msg)

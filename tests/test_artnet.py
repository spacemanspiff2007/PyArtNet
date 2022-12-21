import logging
from asyncio import sleep
from unittest.mock import Mock

import pytest

import pyartnet.base
from pyartnet import ArtNetNode, KiNetNode, SacnNode
from tests.conftest import TestingNode


@pytest.fixture(autouse=True)
def patch_socket(monkeypatch):
    monkeypatch.setattr(pyartnet.base.base_node, 'socket', Mock())


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

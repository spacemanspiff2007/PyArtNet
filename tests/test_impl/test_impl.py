import inspect
import logging
from asyncio import sleep

import pytest

from pyartnet import ArtNetNode, KiNetNode, SacnNode
from pyartnet.base import BaseNode
from tests.conftest import TestingNode


@pytest.mark.parametrize('c', (ArtNetNode, KiNetNode, SacnNode))
def test_same_cls_signature(c):
    sig_base = inspect.signature(BaseNode)
    sig_obj = inspect.signature(c)

    for name, parameter in sig_base.parameters.items():
        assert name in sig_obj.parameters
        assert sig_obj.parameters[name] == parameter


@pytest.mark.parametrize('cls', [ArtNetNode, SacnNode, KiNetNode])
async def test_set_funcs(node: TestingNode, caplog, cls):
    caplog.set_level(logging.DEBUG)

    n = cls('ip', 9999)
    u = n.add_universe(1)
    c = u.add_channel(1, 1)

    c.set_values([5])
    await sleep(0.1)

    c.set_fade([250], 700)
    await c

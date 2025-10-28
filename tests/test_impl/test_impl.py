import inspect
import logging
from asyncio import sleep

import pytest
from tests.conftest import TestingNode
from tests.helper import UnicastNetworkTestingTarget

from pyartnet import ArtNetNode, KiNetNode, SacnNode
from pyartnet.base import BaseNode
from pyartnet.errors import InvalidUniverseAddressError


@pytest.mark.parametrize('c', (ArtNetNode, KiNetNode, SacnNode))
def test_same_cls_signature(c) -> None:
    sig_base = inspect.signature(BaseNode)
    sig_obj = inspect.signature(c)

    for name, base_parameter in sig_base.parameters.items():
        assert name in sig_obj.parameters
        # network parameter can be different
        if name == 'network':
            continue
        obj_parameter = sig_obj.parameters[name]
        assert obj_parameter == base_parameter


def test_same_unicast_signature() -> None:
    classes = (ArtNetNode, KiNetNode, SacnNode)

    cls_base = classes[0]
    sig_base = inspect.signature(cls_base.create)

    for cls in classes[1:]:

        assert cls.__doc__ == cls_base.__doc__

        sig_obj = inspect.signature(cls.create)

        for name, base_parameter in sig_base.parameters.items():
            assert name in sig_obj.parameters
            obj_parameter = sig_obj.parameters[name]

            # some ports have a default which we ignore here
            if name == 'port':
                obj_parameter = obj_parameter.replace(default=inspect.Parameter.empty)
                base_parameter = base_parameter.replace(default=inspect.Parameter.empty)

            assert obj_parameter == base_parameter


@pytest.mark.parametrize('cls', [ArtNetNode, SacnNode, KiNetNode])
async def test_set_funcs(node: TestingNode, caplog, cls) -> None:
    caplog.set_level(logging.DEBUG)

    async with cls(UnicastNetworkTestingTarget(('ip', 9999999))) as n:
        u = n.add_universe(1)
        c = u.add_channel(1, 1)

        c.set_values([5])
        await sleep(0.1)

        c.set_fade([250], 700)
        await c


@pytest.mark.parametrize('cls', [ArtNetNode, SacnNode, KiNetNode])
async def test_universe_validation(node: TestingNode, cls) -> None:

    n = cls(UnicastNetworkTestingTarget(('ip', 9999999)))
    with pytest.raises(TypeError):
        n.add_universe(1.3)

    with pytest.raises(InvalidUniverseAddressError):
        n.add_universe(2 ** 16)

from unittest.mock import Mock

import pytest

import pyartnet.node.base_node
from pyartnet.node import BaseNode, Universe


@pytest.fixture
def node(monkeypatch):
    monkeypatch.setattr(pyartnet.node.base_node, 'socket', Mock())
    node = pyartnet.node.base_node.BaseNode('IP', 9999)
    yield node


@pytest.fixture
def universe(node: BaseNode):
    universe = Universe(node, 1)
    node._universes.append(universe)
    yield universe

import pytest

from pyartnet.errors import DuplicateUniverseError
from tests.conftest import TestingNode


def test_universe_add_get(node: TestingNode):
    for i in (1.3, -1):
        with pytest.raises(ValueError) as e:
            node.add_universe(i)
        assert str(e.value) == 'BaseUniverse must be an int >= 0!'

        with pytest.raises(ValueError) as e:
            node.get_universe(i)
        assert str(e.value) == 'BaseUniverse must be an int >= 0!'

    u = node.add_universe()
    assert len(node) == 1
    assert node.get_universe(0) is u
    assert node[0] is u

    # Duplicate
    with pytest.raises(DuplicateUniverseError) as e:
        node.add_universe()
    assert str(e.value) == 'BaseUniverse 0 does already exist!'

    # Check that the nodes are ascending
    node.add_universe(50)
    node.add_universe(3)

    assert len(node) == 3
    assert node._universes == (
        node.get_universe(0), node.get_universe(3), node.get_universe(50)
    )

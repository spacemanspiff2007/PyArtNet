from pyartnet.base import BaseUniverse


def test_values_add_channel(universe: BaseUniverse):
    u = universe.add_channel(1, 2, byte_size=3, byte_order='big')
    assert u._start == 1
    assert u._width == 2
    assert u._byte_size == 3
    assert u._byte_order == 'big'

    u = universe.add_channel(10, 5, byte_size=2, byte_order='little')
    assert u._start == 10
    assert u._width == 5
    assert u._byte_size == 2
    assert u._byte_order == 'little'

import logging
from asyncio import sleep
from binascii import a2b_hex

import pytest

from pyartnet import ArtNetNode, KiNetNode, SacnNode
from tests.conftest import TestingNode


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


async def test_sacn(patched_socket):
    sacn = SacnNode(
        'ip', 9999999,
        cid=b'\x41\x68\xf5\x2b\x1a\x7b\x2d\xe1\x17\x12\xe9\xee\x38\x3d\x22\x58',
        source_name="default source name")
    universe = sacn.add_universe(1)
    channel = universe.add_channel(1, 10)
    channel.set_values(range(1, 11))

    universe.send_data()

    data = '001000004153432d45312e31370000007078000000044168f52b1a7b2de11712e9ee383d225870620000000264656661756c7420' \
           '736f75726365206e616d650000000000000000000000000000000000000000000000000000000000000000000000000000000000' \
           '0000000064003200000001701502a100000001000b000102030405060708090a'

    m = sacn._socket
    m.sendto.assert_called_once_with(bytearray(a2b_hex(data)), ('ip', 9999999))


    await sleep(1.2)

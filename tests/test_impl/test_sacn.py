import asyncio
import logging
from binascii import a2b_hex
from unittest.mock import call

import pytest

from pyartnet import SacnNode


async def test_sacn() -> None:
    sacn = SacnNode(
        'ip', 9999999,
        cid=b'\x41\x68\xf5\x2b\x1a\x7b\x2d\xe1\x17\x12\xe9\xee\x38\x3d\x22\x58',
        source_name='default source name',
        start_refresh_task=True
    )

    channel = sacn.add_universe(1).add_channel(1, 10)
    channel.set_values(range(1, 11))

    data = ('001000004153432d45312e31370000007078000000044168f52b1a7b2de11712e9ee383d225870620000000264656661756c7420'
            '736f75726365206e616d650000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '0000000064000000000001701502a100000001000b000102030405060708090a')

    await channel
    await sacn._process_task.task
    await asyncio.sleep(0.3)

    m = sacn._socket
    m.sendto.assert_called_once_with(bytearray(a2b_hex(data)), ('ip', 9999999))

    await channel


@pytest.mark.parametrize('multicast', [False, True])
async def test_sacn_with_sync(caplog, multicast) -> None:
    caplog.set_level(logging.DEBUG)

    sacn = SacnNode(
        'ip', 9999999,
        cid=b'\x41\x68\xf5\x2b\x1a\x7b\x2d\xe1\x17\x12\xe9\xee\x38\x3d\x22\x58',
        source_name='default source name',
        start_refresh_task=False
    )
    sacn.set_synchronous_mode(True, 2)
    sacn.set_multicast_mode(multicast)

    channel = sacn.add_universe(1).add_channel(1, 10)
    channel.set_values(range(1, 11))

    data = ('001000004153432d45312e31370000007078000000044168f52b1a7b2de11712e9ee383d225870620000000264656661756c7420'
            '736f75726365206e616d650000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '0000000064000200000001701502a100000001000b000102030405060708090a')

    sync_data = '001000004153432d45312e31370000007021000000084168f52b1a7b2de11712e9ee383d2258700b000000010000020000'

    await channel
    await sacn._process_task.task
    await asyncio.sleep(0.3)

    data_dst = ('ip', 9999999) if not multicast else ('239.255.0.1', 5568)
    sync_dst = ('ip', 9999999) if not multicast else ('239.255.0.2', 5568)
    data_msg = 'ip:9999999' if not multicast else '239.255.0.1:5568'
    sync_msg = 'ip:9999999' if not multicast else '239.255.0.2:5568'

    m = sacn._socket
    assert m.sendto.call_args_list == [
        call(bytearray(a2b_hex(data)), data_dst),
        call(bytearray(a2b_hex(sync_data)), sync_dst),
    ]

    assert caplog.record_tuples == [
        ('pyartnet.Universe', 10, 'Added channel "1/10": start: 1, stop: 10'),
        ('pyartnet.Task', 10, 'Started Process task ip:9999999'),
        ('pyartnet.SacnNode', 10, f'Sending sACN frame to {data_msg:s}: {data:s}'),
        ('pyartnet.SacnNode', 10, f'Sending sACN Synchronization Packet to {sync_msg}: {sync_data:s}'),
        ('pyartnet.Task', 10, 'Stopped Process task ip:9999999')
    ]

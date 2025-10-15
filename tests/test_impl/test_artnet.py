
import asyncio
import logging
from binascii import a2b_hex
from unittest.mock import call

from pyartnet import ArtNetNode


async def test_artnet() -> None:
    arnet = ArtNetNode('ip', 9999999, start_refresh_task=True)
    channel = arnet.add_universe(1).add_channel(1, 10)
    channel.set_values(range(1, 11))

    data = '4172742d4e6574000050000e01000100000a0102030405060708090a'

    await channel
    await arnet._process_task.task
    await asyncio.sleep(0.3)

    m = arnet._socket
    m.sendto.assert_called_once_with(bytearray(a2b_hex(data)), ('ip', 9999999))

    await channel


async def test_artnet_with_sync(caplog) -> None:
    caplog.set_level(logging.DEBUG)

    artnet = ArtNetNode('ip', 9999999, start_refresh_task=False)
    artnet.set_synchronous_mode(True)

    channel = artnet.add_universe(1).add_channel(1, 10)
    channel.set_values(range(1, 11))

    data = '4172742d4e6574000050000e01000100000a0102030405060708090a'
    sync_data = '4172742d4e6574000052000e0000'

    await channel
    await artnet._process_task.task
    await asyncio.sleep(0.3)

    m = artnet._socket
    assert m.sendto.call_args_list == [
        call(bytearray(a2b_hex(data)), ('ip', 9999999)),
        call(bytearray(a2b_hex(sync_data)), ('ip', 9999999)),
    ]

    assert caplog.record_tuples == [
        ('pyartnet.Universe', 10, 'Added channel "1/10": start: 1, stop: 10'),
         ('pyartnet.Task', 10, 'Started Process task ip:9999999'),
        ('pyartnet.ArtNetNode', 10, '                                       Sq    Univ  Len   1   2   3   4   5     6   7   8   9   10 '),  # noqa: E501
        ('pyartnet.ArtNetNode', 10, 'Packet to ip: 4172742D4E6574000050000E 01 00 0001 000a   001 002 003 004 005   006 007 008 009 010'),  # noqa: E501
        ('pyartnet.ArtNetNode', 10, 'Sync   to ip: 4172742D4E6574000052000E 00 00'),
        ('pyartnet.Task', 10, 'Stopped Process task ip:9999999'),
    ]


import asyncio
import logging
from binascii import a2b_hex
from unittest.mock import call

from pyartnet import ArtNetNode
from pyartnet.base.network import UnicastNetworkTarget


async def test_artnet() -> None:
    async with ArtNetNode(UnicastNetworkTarget(('ip', 9999999))) as artnet:
        channel = artnet.add_universe(1).add_channel(1, 10)
        channel.set_values(range(1, 11))

        data = '4172742d4e6574000050000e01000100000a0102030405060708090a'

        await channel
        await artnet._process_task.task
        await asyncio.sleep(0.3)

        m = artnet._socket
        m.sendto.assert_called_once_with(bytearray(a2b_hex(data)), ('ip', 9999999))

        await channel


async def test_artnet_with_sync(caplog) -> None:
    caplog.set_level(logging.DEBUG)

    async with ArtNetNode(UnicastNetworkTarget(('ip', 9999999)), name='device1') as artnet:
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
            ('pyartnet.Task', 10, 'Started Refresh task device1'),
            ('pyartnet.Task', 10, 'Started Process task device1'),
            ('pyartnet.ArtNetNode', 10, '                                       Sq    Univ  Len   1   2   3   4   5     6   7   8   9   10 '),  # noqa: E501
            ('pyartnet.ArtNetNode', 10, 'Packet to ip: 4172742D4E6574000050000E 01 00 0001 000a   001 002 003 004 005   006 007 008 009 010'),  # noqa: E501
            ('pyartnet.ArtNetNode', 10, 'Sync   to ip: 4172742D4E6574000052000E 00 00'),
            ('pyartnet.Task', 10, 'Stopped Process task device1'),
        ]

        caplog.clear()

    # context manager cancels the refresh task, too
    assert caplog.record_tuples == [
        ('pyartnet.Task', 10, 'Stopped Refresh task device1'),
    ]

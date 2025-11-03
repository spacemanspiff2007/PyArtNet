from __future__ import annotations

import logging
from typing import Final

from typing_extensions import Self, override

import pyartnet
from pyartnet.base import BaseNode
from pyartnet.base.network import UnicastNetworkTarget
from pyartnet.base.seq_counter import SequenceCounter
from pyartnet.errors import InvalidUniverseAddressError


# -----------------------------------------------------------------------------
# Documentation for ArtNet Protocol:
# https://artisticlicence.com/support-and-resources/art-net-4/
# -----------------------------------------------------------------------------

ARTNET_PORT: Final = 6454

log = logging.getLogger('pyartnet.ArtNetNode')


class ArtNetNode(BaseNode['pyartnet.impl_artnet.ArtNetUniverse']):
    def __init__(self, network: UnicastNetworkTarget, *,
                 name: str | None = None,
                 max_fps: int = 25,
                 refresh_every: float = 2,

                 # ArtNet specific fields
                 sequence_counter: bool = True
                 ) -> None:
        super().__init__(network, name=name, max_fps=max_fps, refresh_every=refresh_every)

        self._dst: Final = network.dst
        self._ip: Final = self._dst[0]

        # ArtNet specific fields
        self._sequence_ctr: Final = SequenceCounter(1) if sequence_counter else SequenceCounter(0, 0)

        # build base packet
        packet = bytearray()
        packet.extend(map(ord, 'Art-Net'))
        packet.append(0x00)          # Null terminate Art-Net
        self._packet_base = bytes(packet)

        self._sync_enabled : bool = False

    @classmethod
    def create(cls, host: str, port: int = ARTNET_PORT, *,
               source_ip: str | None = None, source_port: int = 0,
               name: str | None = None, max_fps: int = 25, refresh_every: float = 2) -> Self:
        """Creates a new node. The packages will be sent directly to the node (unicast).

        :param host: ip or hostname of the device
        :param port: port of device
        :param source_ip: ip of the network interface that shall be used to send data
        :param source_port: source port
        :param name: a custom name of the node
        :param max_fps: maximum frames per second to send
        :param refresh_every: refresh interval in seconds
        """

        network = UnicastNetworkTarget.create(host, port, source_ip=source_ip, source_port=source_port)
        return cls(network, name=name, max_fps=max_fps, refresh_every=refresh_every)

    @override
    def _send_universe(self, id: int, byte_size: int, values: bytearray,
                       universe: pyartnet.impl_artnet.ArtNetUniverse) -> None:

        # pre allocate the bytearray
        _size = 10 + byte_size
        packet = bytearray(_size)

        packet[0:2] = (0x00, 0x50)                      # 2 | Opcode ArtDMX 0x5000 (Little Endian)
        packet[2:4] = (0x00, 0x0e)                      # 2 | Protocol version 14  (Little Endian)

        packet[4] = self._sequence_ctr.value            # 1 | Sequence,
        packet[5] = 0x00                                # 1 | Physical input port (not used)
        packet[6:8] = id.to_bytes(2, 'little')          # 2 | Universe (Little endian)

        packet[8:10] = byte_size.to_bytes(2, 'big')     # 2       | Number of channels Big Endian
        packet[10: _size] = values                      # 0 - 512 | Channel values

        self._send_data(packet, self._dst)

        # log complete packet
        if log.isEnabledFor(logging.DEBUG):
            self.__log_artnet_frame(self._packet_base + packet)

    @override
    def _create_universe(self, nr: int) -> pyartnet.impl_artnet.ArtNetUniverse:
        return pyartnet.impl_artnet.ArtNetUniverse(self, self._validate_universe_nr(nr))

    @override
    def _validate_universe_nr(self, nr: int) -> int:
        if not isinstance(nr, int):
            raise TypeError()
        if not 0 <= nr <= 32_768:
            raise InvalidUniverseAddressError()
        return int(nr)

    def __log_artnet_frame(self, p: bytearray | bytes) -> None:
        """Log Artnet Frame"""
        if not isinstance(p, (bytearray, bytes)):
            raise TypeError()

        # runs the first time
        if not hasattr(self, '_log_ctr'):
            self._log_ctr = -1
            self._log_show = [False for k in range(103)]

        self._log_ctr += 1
        if self._log_ctr >= 10:
            self._log_ctr = 0
        show_description: bool = self._log_ctr == 0

        host_fmt = ' ' * (36 + len(self._ip))
        out_desc = '{:s} {:2s} {:2s} {:4s} {:4s}'.format(host_fmt, 'Sq', '', 'Univ', ' Len')

        pre = bytearray(p[:12]).hex().upper()

        # low byte first: 5200 -> 0052
        if p[8:10] == b'\x00\x52':
            log.debug(f'Sync   to {self._ip:s}: {pre} {p[12]:02x} {p[13]:02x}')
            return None

        _max_channel = p[16] << 8 | p[17]
        out = f'Packet to {self._ip:s}: {pre} {p[12]:02x} {p[13]:02x} {p[13]:02x}{p[14]:02x} {_max_channel:04x}'

        # check what to print
        for k in range(_max_channel):
            if p[18 + k]:
                # once we change something print channel index
                if self._log_show[k // 5] is False:
                    show_description = True
                self._log_show[k // 5] = True

        for k in range(0, _max_channel, 5):

            # if there was never anything active do not print, but print the last block
            if not self._log_show[k // 5] and not k + 5 > _max_channel:
                # do not print multiple dots
                if out.endswith('...'):
                    continue

                out_desc += '  - '
                out += ' ...'
                continue

            # format block of channels
            _block_vals = []
            _block_desc = []
            for i in range(5):
                if k + i < _max_channel:
                    if show_description:
                        _block_desc.append(f'{k + i + 1:<3d}')
                    _block_vals.append(f'{p[18 + k + i]:03d}')

            # separator
            if out.endswith('...'):
                out_desc += ' '
                out += ' '
            else:
                out_desc += '   '
                out += '   '

            out += ' '.join(_block_vals)
            if show_description:
                out_desc += ' '.join(_block_desc)

        if show_description:
            log.debug(out_desc)
        log.debug(out)
        return None

    @override
    def set_synchronous_mode(self, enabled: bool) -> Self:
        """Enable or disable synchronous mode for this node. In synchronous mode multiple universes are sent to the
        node and then a synchronization packet is sent to make the node output all universes at the same time.
        This prevents tearing in multi universe panels.

        :param enabled: Enable or disable synchronous mode
        """
        if self._refresh_every > 3.5:
            msg = 'ArtNet synchronization requires refresh_every <= 3.5s'
            raise ValueError(msg)

        self._sync_enabled = enabled
        return self

    @override
    def _send_synchronization(self) -> None:
        if not self._sync_enabled:
            return

        # pre allocate the bytearray
        packet = bytearray(6)

        packet[0:2] = (0x00, 0x52)  # 2 | Opcode ArtSync 0x5200 (Little Endian)
        packet[2:4] = (0x00, 0x0e)  # 2 | Protocol Version 14   (Little Endian)

        packet[4] = 0               # 1 | Aux1
        packet[5] = 0               # 1 | Aux2

        self._send_data(packet, self._dst)

        # log complete packet
        if log.isEnabledFor(logging.DEBUG):
            self.__log_artnet_frame(self._packet_base + packet)

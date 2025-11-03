from __future__ import annotations

import logging
from logging import DEBUG as LVL_DEBUG
from struct import pack as s_pack
from typing import Final

from typing_extensions import Self, override

import pyartnet
from pyartnet.base import BaseNode
from pyartnet.base.network import UnicastNetworkTarget
from pyartnet.errors import InvalidUniverseAddressError


# -----------------------------------------------------------------------------
# Documentation for KiNet Protocol is unclear
# -----------------------------------------------------------------------------

KINET_PORT: Final = 6038

log = logging.getLogger('pyartnet.KiNetNode')


class KiNetNode(BaseNode['pyartnet.impl_kinet.KiNetUniverse']):
    def __init__(self, network: UnicastNetworkTarget, *,
                 name: str | None = None,
                 max_fps: int = 25,
                 refresh_every: float = 2) -> None:
        super().__init__(network, name=name, max_fps=max_fps, refresh_every=refresh_every)

        self._dst: Final = network.dst

        # build base packet
        packet = bytearray()
        packet.extend(s_pack('>IHH', 0x0401DC4A, 0x0100, 0x0101))   # Magic, version, type
        packet.extend(s_pack('>IBBHI', 0, 0, 0, 0, 0xFFFFFFFF))     # sequence, port, padding, flags, timer
        self._packet_base = bytes(packet)

    @classmethod
    def create(cls, host: str, port: int = KINET_PORT, *,
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
    def _send_universe(self, id: int, byte_size: int,
                       values: bytearray, universe: pyartnet.impl_kinet.KiNetUniverse) -> None:
        packet = bytearray()
        packet.append(byte_size)
        packet.extend(values)

        self._send_data(packet)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            ip, port = self._dst
            log.debug(f'Sending KiNet frame to {ip}:{port}: {(self._packet_base + packet).hex()}')

    @override
    def _create_universe(self, nr: int) -> pyartnet.impl_kinet.KiNetUniverse:
        return pyartnet.impl_kinet.KiNetUniverse(self, self._validate_universe_nr(nr))

    @override
    def _validate_universe_nr(self, nr: int) -> int:
        if not isinstance(nr, int):
            raise TypeError()
        if not 0 <= nr <= 32_768:
            raise InvalidUniverseAddressError()
        return int(nr)

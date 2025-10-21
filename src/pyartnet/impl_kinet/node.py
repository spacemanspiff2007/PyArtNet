from __future__ import annotations

import logging
from logging import DEBUG as LVL_DEBUG
from struct import pack as s_pack
from typing import Final

from typing_extensions import override

import pyartnet
from pyartnet.base import BaseNode
from pyartnet.errors import InvalidUniverseAddressError


# -----------------------------------------------------------------------------
# Documentation for KiNet Protocol:
# todo: find links
# -----------------------------------------------------------------------------

KINET_PORT: Final = 6038

log = logging.getLogger('pyartnet.KiNetNode')


class KiNetNode(BaseNode['pyartnet.impl_kinet.KiNetUniverse']):
    def __init__(self, ip: str, port: int = KINET_PORT, *,
                 max_fps: int = 25,
                 refresh_every: float = 2, start_refresh_task: bool = True,
                 source_address: tuple[str, int] | None = None) -> None:
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every, start_refresh_task=start_refresh_task,
                         source_address=source_address)

        # build base packet
        packet = bytearray()
        packet.extend(s_pack('>IHH', 0x0401DC4A, 0x0100, 0x0101))   # Magic, version, type
        packet.extend(s_pack('>IBBHI', 0, 0, 0, 0, 0xFFFFFFFF))     # sequence, port, padding, flags, timer
        self._packet_base = bytes(packet)

    @override
    def _send_universe(self, id: int, byte_size: int,
                       values: bytearray, universe: pyartnet.impl_kinet.KiNetUniverse) -> None:
        packet = bytearray()
        packet.append(byte_size)
        packet.extend(values)

        self._send_data(packet)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f'Sending KiNet frame to {self._ip}:{self._port}: {(self._packet_base + packet).hex()}')

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

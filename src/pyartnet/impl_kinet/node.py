import logging
from logging import DEBUG as LVL_DEBUG
from struct import pack as s_pack
from typing import Optional, Tuple, Union

import pyartnet
from pyartnet.base import BaseNode
from pyartnet.errors import InvalidUniverseAddressError

# -----------------------------------------------------------------------------
# Documentation for KiNet Protocol:
# todo: find links
# -----------------------------------------------------------------------------

log = logging.getLogger('pyartnet.KiNetNode')


class KiNetNode(BaseNode['pyartnet.impl_kinet.KiNetUniverse']):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float, None] = 2, start_refresh_task: bool = True,
                 source_address: Optional[Tuple[str, int]] = None):
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every, start_refresh_task=start_refresh_task,
                         source_address=source_address)

        # build base packet
        packet = bytearray()
        packet.extend(s_pack(">IHH", 0x0401DC4A, 0x0100, 0x0101))   # Magic, version, type
        packet.extend(s_pack(">IBBHI", 0, 0, 0, 0, 0xFFFFFFFF))     # sequence, port, padding, flags, timer
        self._packet_base = bytes(packet)

    def _send_universe(self, id: int, byte_size: int, values: bytearray, universe: 'pyartnet.impl_kinet.KiNetUniverse'):
        packet = bytearray()
        packet.append(byte_size)
        packet.extend(values)

        self._send_data(packet)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f"Sending KiNet frame to {self._ip}:{self._port}: {(self._packet_base + packet).hex()}")

    def _create_universe(self, nr: int) -> 'pyartnet.impl_kinet.KiNetUniverse':
        if nr >= 32_768:
            raise InvalidUniverseAddressError()
        return pyartnet.impl_kinet.KiNetUniverse(self, nr)

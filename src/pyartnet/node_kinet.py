import logging
from logging import DEBUG as LVL_DEBUG
from struct import pack as s_pack
from typing import Optional, Tuple, Union

from pyartnet.node import BaseNode

# -----------------------------------------------------------------------------
# Documentation for KiNet Protocol:
# todo: find links
# -----------------------------------------------------------------------------

log = logging.getLogger('pyartnet.KiNetNode')


class KiNetNode(BaseNode):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float] = 2,
                 sequence_counter=True,
                 source_address: Optional[Tuple[str, int]] = None):
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every,
                         sequence_counter=sequence_counter,
                         source_address=source_address)

        # build base packet
        packet = bytearray()
        packet.extend(s_pack(">IHH", 0x0401DC4A, 0x0100, 0x0101))   # Magic, version, type
        packet.extend(s_pack(">IBBHI", 0, 0, 0, 0, 0xFFFFFFFF))     # sequence, port, padding, flags, timer
        self._packet_base = bytes(packet)

    def _send_universe(self, universe: int, byte_values: int, values: bytearray):
        packet = bytearray()
        packet.append(byte_values)      # Universe
        packet.extend(values)

        self._send_data(packet)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f"Sending KiNet frame to {self._ip}:{self._port}: {(self._packet_base + packet).hex()}")

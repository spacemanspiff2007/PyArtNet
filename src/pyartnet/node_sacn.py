# flake8: noqa: E262
import logging
from logging import DEBUG as LVL_DEBUG
from typing import Final, Optional, Tuple, Union
from uuid import uuid4

from pyartnet.node import BaseNode

# -----------------------------------------------------------------------------
# Documentation for E1.31 Protocol:
# https://tsp.esta.org/tsp/documents/published_docs.php
# -----------------------------------------------------------------------------

log = logging.getLogger('pyartnet.SacnNode')


# Package constant
ACN_PACKET_IDENTIFIER: Final = (0x41, 0x53, 0x43, 0x2d, 0x45, 0x31, 0x2e, 0x31, 0x37, 0x00, 0x00, 0x00)

# Field constants
VECTOR_ROOT_E131_DATA: Final = b'\x00\x00\x00\x04'
VECTOR_E131_DATA_PACKET: Final = b'\x00\x00\x00\x02'
VECTOR_DMP_SET_PROPERTY: Final = 0x02


class SacnNode(BaseNode):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float] = 2,
                 sequence_counter=True,
                 source_address: Optional[Tuple[str, int]] = None,

                 # sACN E1.31 specific fields
                 cid: Optional[bytes] = None, source_name: Optional[str] = None
                 ):
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every,
                         sequence_counter=sequence_counter,
                         source_address=source_address)

        # CID Field
        if cid is not None:
            if not isinstance(cid, bytes) or len(cid) > 16:
                raise ValueError('CID invalid or too long!')
        else:
            cid = uuid4().bytes

        # Source field
        if source_name is None:
            source_name = 'PyArtNet'
        source_name_byte = source_name.encode('utf-8').ljust(64, b'\x00')
        if len(source_name_byte) > 64:
            raise ValueError('Source name too long!')


        # build base packet
        packet = bytearray()

        # Root layer
        packet.extend([0x00, 0x01])             #  2 | Preamble Size
        packet.extend([0x00, 0x00])             #  2 | Post-amble Size
        packet.extend(ACN_PACKET_IDENTIFIER)    # 12 | Packet Identifier
        packet.extend([0x72, 0x57])             #  2 | Flags, Length
        packet.extend(VECTOR_ROOT_E131_DATA)    #  4 | Vector
        packet.extend(cid)                      # 16 | CID, a unique identifier

        # Framing layer Part 1
        packet.extend([0x72, 0x57])                 #  2 | Flags and length
        packet.extend(VECTOR_E131_DATA_PACKET)      #  4 | Vector
        packet.extend(source_name_byte)             # 64 |Source Name
        packet.append(100)                          #  1 |Priority
        packet.extend(int(50).to_bytes(2, 'big'))   #  2 | Synchronization universe
        self._packet_base = packet


    def _send_universe(self, universe: int, byte_values: int, values: bytearray):
        packet = bytearray()

        # Framing layer Part 2
        packet.append(self._sequence_ctr)                       # 1 | Sequence,
        packet.append(0x00)                                     # 1 | Options
        packet.extend(universe.to_bytes(2, byteorder='big'))    # 2 | Universe Number


        # DMP Layer
        dmp_length = ((11 + byte_values) | 0x7000).to_bytes(2, 'big')
        packet.extend(dmp_length)               # 2 | Flags and length
        packet.append(VECTOR_DMP_SET_PROPERTY)  # 1 | Vector
        packet.append(0xA1)                     # 1 | Address Type & Data Type
        packet.extend(b'\x00\x00')              # 2 | First Property Address
        packet.extend(b'\x00\x01')              # 2 | Address Increment

        packet.extend(byte_values.to_bytes(2, 'big'))   #     2 | Property Value Count
        packet.append(0x00)                             #     1 | Property Values - DMX Start Code
        packet.extend(values)                           # 0-512 | Property Values - DMX Data


        # Update length for base packet
        base_packet = self._packet_base
        base_packet[16:18] = ((110 + byte_values) | 0x7000).to_bytes(2, 'big')  # root layer
        base_packet[38:40] = (( 88 + byte_values) | 0x7000).to_bytes(2, 'big')  # framing layer

        self._send_data(self._packet_base + packet)

        if log.isEnabledFor(LVL_DEBUG):
            log.debug(f"Sending sACN frame to {self._ip}:{self._port}: {(base_packet + packet).hex()}")

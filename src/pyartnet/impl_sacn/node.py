# flake8: noqa: E262
import logging
from logging import DEBUG as LVL_DEBUG
from typing import Final, Optional, Tuple, Union
from uuid import uuid4

import pyartnet.impl_sacn.universe
from pyartnet.base import BaseNode, SequenceCounter
from pyartnet.errors import InvalidCidError, InvalidUniverseAddressError

# -----------------------------------------------------------------------------
# Documentation for E1.31 Protocol:
# https://tsp.esta.org/tsp/documents/published_docs.php
# -----------------------------------------------------------------------------

log = logging.getLogger('pyartnet.SacnNode')


# Package constant
ACN_PACKET_IDENTIFIER: Final = (0x41, 0x53, 0x43, 0x2d, 0x45, 0x31, 0x2e, 0x31, 0x37, 0x00, 0x00, 0x00)

# Field constants
VECTOR_ROOT_E131_DATA: Final = b'\x00\x00\x00\x04'
VECTOR_ROOT_E131_EXTENDED: Final = b'\x00\x00\x00\x08'
VECTOR_E131_DATA_PACKET: Final = b'\x00\x00\x00\x02'
VECTOR_E131_EXTENDED_SYNCHRONIZATION: Final = b'\x00\x00\x00\x01'
VECTOR_DMP_SET_PROPERTY: Final = 0x02


class SacnNode(BaseNode['pyartnet.impl_sacn.SacnUniverse']):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float, None] = 2, start_refresh_task: bool = True,
                 source_address: Optional[Tuple[str, int]] = None,

                 # sACN E1.31 specific fields
                 cid: Optional[bytes] = None, source_name: Optional[str] = None,

                 # Send to multicast addresses based on universe?
                 send_to_multicast: bool = False,
                 ) -> None:
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every, start_refresh_task=start_refresh_task,
                         source_address=source_address)

        # CID Field
        if cid is not None:
            if not isinstance(cid, bytes) or len(cid) != 16:
                raise InvalidCidError('CID must be 16bytes!')
        else:
            cid = uuid4().bytes

        # Source field
        if source_name is None:
            source_name = 'PyArtNet'
        source_name_byte = source_name.encode('utf-8').ljust(64, b'\x00')
        if len(source_name_byte) > 64:
            raise ValueError('Source name too long!')
        self._source_name_byte : bytes = source_name_byte

        # build base packet
        packet = bytearray()

        # Root layer
        packet.extend(b'\x00\x10')              # |  2 | Preamble Size
        packet.extend(b'\x00\x00')              # |  2 | Post-amble Size
        packet.extend(ACN_PACKET_IDENTIFIER)    # | 12 | Packet Identifier
        packet.extend((0x72, 0x57))             # |  2 | Flags, Length
        packet.extend(VECTOR_ROOT_E131_DATA)    # |  4 | Vector
        packet.extend(cid)                      # | 16 | CID, a unique identifier

        self._packet_base: bytearray = packet

        self._synchronization_address : int = 0

        # See spec 6.3.2 E1.31 Synchronization Packet: Sequence Number
        self._sync_sequence_number: Final = SequenceCounter()

        self._send_to_multicast : bool = send_to_multicast

    def _get_ip_address_from_universe(self, addr : int) -> str:
        if self._send_to_multicast:
            return f"239.255.{addr//256}.{addr & 255}"
        return None

    def _send_universe(self, id: int, byte_size: int, values: bytearray,
                       universe: 'pyartnet.impl_sacn.universe.SacnUniverse') -> None:
        packet = bytearray()

        # DMX Start Code is not included in the byte size from the universe
        prop_count = byte_size + 1

        # Framing layer Part 1
        packet.extend((( 87 + prop_count) | 0x7000).to_bytes(2, 'big'))         # |  2 | Flags and Length
        packet.extend(VECTOR_E131_DATA_PACKET)                                  # |  4 | Vector
        packet.extend(self._source_name_byte)                                   # | 64 | Source Name
        packet.append(100)                                                      # |  1 | Priority
        packet.extend(int(self._synchronization_address).to_bytes(2, 'big'))    # |  2 | Synchronization universe

        # Framing layer Part 2
        packet.append(universe._sequence_ctr.value)             # | 1 | Sequence,
        packet.append(0x00)                                     # | 1 | Options
        packet.extend(id.to_bytes(2, byteorder='big'))          # | 2 | BaseUniverse Number

        # DMP Layer
        dmp_length = ((10 + prop_count) | 0x7000).to_bytes(2, 'big')
        packet.extend(dmp_length)               # | 2 | Flags and length
        packet.append(VECTOR_DMP_SET_PROPERTY)  # | 1 | Vector
        packet.append(0xA1)                     # | 1 | Address Type & Data Type
        packet.extend(b'\x00\x00')              # | 2 | First Property Address
        packet.extend(b'\x00\x01')              # | 2 | Address Increment

        packet.extend(prop_count.to_bytes(2, 'big'))    # |     2 | Property Value Count
        packet.append(0x00)                             # |     1 | Property Values - DMX Start Code
        packet.extend(values)                           # | 0-512 | Property Values - DMX Data

        # Update length and package type for base packet
        base_packet = self._packet_base
        base_packet[16:18] = ((109 + prop_count) | 0x7000).to_bytes(2, 'big')   # |  2 | Flags, Length
        base_packet[18:22] = VECTOR_ROOT_E131_DATA                              # |  4 | Vector

        self._send_data(packet, self._get_ip_address_from_universe(id))

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f"Sending sACN frame to {self._ip}:{self._port}: {(base_packet + packet).hex()}")

    def _create_universe(self, nr: int) -> 'pyartnet.impl_sacn.SacnUniverse':
        return pyartnet.impl_sacn.SacnUniverse(self, self._validate_universe_nr(nr))

    def _validate_universe_nr(self, nr: int) -> int:
        if not isinstance(nr, int):
            raise TypeError()
        # See spec 6.2.7 E1.31 Data Packet: Universe
        if not 1 <= nr <= 63_999:
            raise InvalidUniverseAddressError()
        return int(nr)


    def set_synchronous_mode(self, enabled: bool, synchronization_address: int = 0):
        if enabled:
            self._synchronization_address = self._validate_universe_nr(synchronization_address)
        else:
            if synchronization_address != 0:
                msg = 'synchronization_address must be 0 when disabling synchronous mode!'
                raise ValueError(msg)
            self._synchronization_address = 0

    def _send_synchronization(self) -> None:
        if not self._synchronization_address:
            return

        packet = bytearray()

        # Framing layer
        packet.extend((11 | 0x7000).to_bytes(2, 'big'))                     # |  2 | Flags and Length
        packet.extend(VECTOR_E131_EXTENDED_SYNCHRONIZATION)                 # |  4 | Vector
        packet.append(self._sync_sequence_number.value)                     # |  1 | Sequence Number
        packet.extend(self._synchronization_address.to_bytes(2, 'big'))     # |  2 | Synchronization universe
        packet.extend([0, 0])                                               # |  2 | Reserved

        # Update length and package type for base packet
        base_packet = self._packet_base
        base_packet[16:18] = (33 | 0x7000).to_bytes(2, 'big')   # |  2 | Flags, Length
        base_packet[18:22] = VECTOR_ROOT_E131_EXTENDED          # |  4 | Vector

        self._send_data(packet, self._get_ip_address_from_universe(self._synchronization_address))

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f"Sending sACN Synchronization Packet to {self._ip}:{self._port}: {(base_packet + packet).hex()}")

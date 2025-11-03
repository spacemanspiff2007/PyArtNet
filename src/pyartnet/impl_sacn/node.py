from __future__ import annotations

import logging
from ipaddress import IPv4Address, IPv6Address
from logging import DEBUG as LVL_DEBUG
from socket import AF_INET6
from typing import Final
from uuid import uuid4

from typing_extensions import Self, override

import pyartnet.impl_sacn.universe
from pyartnet.base import BaseNode, SequenceCounter
from pyartnet.base.network import MulticastNetworkTarget, UnicastNetworkTarget
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

# Defined Parameters (Appendix A)
ACN_SDT_MULTICAST_PORT: Final = 5568


class SacnNode(BaseNode['pyartnet.impl_sacn.SacnUniverse']):
    def __init__(self, network: UnicastNetworkTarget | MulticastNetworkTarget, *,
                 name: str | None = None,
                 max_fps: int = 25,
                 refresh_every: float = 2,

                 # sACN E1.31 specific fields
                 cid: bytes | None = None, source_name: str | None = None
                 ) -> None:
        super().__init__(network, name=name, max_fps=max_fps, refresh_every=refresh_every)

        # CID Field
        if cid is not None:
            if not isinstance(cid, bytes) or len(cid) != 16:
                msg = 'CID must be 16bytes!'
                raise InvalidCidError(msg)
        else:
            cid = uuid4().bytes

        # Source field
        if source_name is None:
            source_name = 'PyArtNet'
        source_name_byte = source_name.encode('utf-8').ljust(64, b'\x00')
        if len(source_name_byte) != 64:
            msg = 'Source name too long!'
            raise ValueError(msg)
        self._source_name_byte : bytes = source_name_byte

        # See spec 9.3 Allocation of Multicast Addresses
        self._multicast: bool = False

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

        # Synchronization Packet
        # See Spec 6.2.4 E1.31 Data Packet: Synchronization Address
        self._sync_address: int = 0
        # See spec 9.3 Allocation of Multicast Addresses
        self._sync_dst: tuple[str, int] = ('NOT_SET', 0)
        # See spec 6.3.2 E1.31 Synchronization Packet: Sequence Number
        self._sync_sequence_number: Final = SequenceCounter()

    # noinspection PyProtectedMember
    @override
    def _send_universe(self, id: int, byte_size: int, values: bytearray,
                       universe: pyartnet.impl_sacn.universe.SacnUniverse) -> None:
        packet = bytearray()

        # DMX Start Code is not included in the byte size from the universe
        prop_count = byte_size + 1

        # Framing layer Part 1
        packet.extend((( 87 + prop_count) | 0x7000).to_bytes(2, 'big'))         # |  2 | Flags and Length
        packet.extend(VECTOR_E131_DATA_PACKET)                                  # |  4 | Vector
        packet.extend(self._source_name_byte)                                   # | 64 | Source Name
        packet.append(100)                                                      # |  1 | Priority
        packet.extend(int(self._sync_address).to_bytes(2, 'big'))               # |  2 | Synchronization universe

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

        self._send_data(packet, universe._dst)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(f'Sending sACN frame to {_dst_str(universe._dst)}: {(base_packet + packet).hex()}')

    @classmethod
    def create(cls, host: str, port: int = ACN_SDT_MULTICAST_PORT, *,
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

    @classmethod
    def create_multicast(cls, source_ip: str, source_port: int = 0, *,
               name: str | None = None, max_fps: int = 25, refresh_every: float = 2) -> Self:
        """Creates a new node. The packages will be sent as multicast.

        :param source_ip: interface ip of the network interface that shall be used to send data
        :param source_port: source port
        :param name: a custom name of the node
        :param max_fps: maximum frames per second to send
        :param refresh_every: refresh interval in seconds
        """

        network = MulticastNetworkTarget.create(source_ip, source_port)
        return cls(network, name=name, max_fps=max_fps, refresh_every=refresh_every)


    @override
    def _create_universe(self, nr: int) -> pyartnet.impl_sacn.SacnUniverse:
        return pyartnet.impl_sacn.SacnUniverse(self, self._validate_universe_nr(nr))

    @override
    def _validate_universe_nr(self, nr: int) -> int:
        if not isinstance(nr, int):
            raise TypeError()
        # See spec 6.2.7 E1.31 Data Packet: Universe
        if not 1 <= nr <= 63_999:
            raise InvalidUniverseAddressError()
        return int(nr)

    def _get_universe_ip_port(self, universe: int) -> tuple[str, int]:
        if isinstance(network := self._network, UnicastNetworkTarget):
            return network.dst

        self._validate_universe_nr(universe)

        if (sock := self._socket) is None:
            msg = 'Socket closed! Did you forget to use "async with"?'
            raise RuntimeError(msg)

        if sock.family == AF_INET6:
            # IPv6 multicast address
            address = f'FF18::8300:{universe:04X}'
            IPv6Address(address)
            return address, ACN_SDT_MULTICAST_PORT

        # IPv4 multicast address
        address = f'239.255.{universe // 255:d}.{universe % 255:d}'
        IPv4Address(address)
        return address, ACN_SDT_MULTICAST_PORT

    @override
    def set_synchronous_mode(self, enabled: bool, synchronization_address: int = 0) -> None:    # type: ignore [override]
        """Enable or disable synchronous mode for this node. In synchronous mode multiple universes are sent to the
        node and then a synchronization packet is sent to make the node output all universes at the same time.
        This prevents tearing in multi universe panels.

        :param enabled: Enable or disable synchronous mode
        :param synchronization_address: The universe address to use for synchronization packets. This must be the
                                        same for all nodes that should be synchronized.
        """
        if enabled:
            sync_address = self._validate_universe_nr(synchronization_address)
            self._sync_dst = self._get_universe_ip_port(sync_address)
            self._sync_address = sync_address
            return None

        if synchronization_address != 0:
            msg = 'synchronization_address must be 0 when disabling synchronous mode!'
            raise ValueError(msg)

        self._sync_address = 0
        return None


    @override
    def _send_synchronization(self) -> None:
        if not self._sync_address:
            return

        packet = bytearray(11)

        # Framing layer
        packet[0:2] = (11 | 0x7000).to_bytes(2, 'big')              # |  2 | Flags and Length
        packet[2:6] = VECTOR_E131_EXTENDED_SYNCHRONIZATION          # |  4 | Vector
        packet[6]   = self._sync_sequence_number.value              # |  1 | Sequence Number
        packet[7:9] = self._sync_address.to_bytes(2, 'big')         # |  2 | Synchronization universe
        # packet[9:11] = [0, 0]                                     # |  2 | Reserved
                                                                    # +----+----------
                                                                    # = 11

        # Update length and package type for base packet
        base_packet = self._packet_base
        base_packet[16:18] = (33 | 0x7000).to_bytes(2, 'big')   # |  2 | Flags, Length
        base_packet[18:22] = VECTOR_ROOT_E131_EXTENDED          # |  4 | Vector

        self._send_data(packet, self._sync_dst)

        if log.isEnabledFor(LVL_DEBUG):
            # log complete packet
            log.debug(
                f'Sending sACN Synchronization Packet to {_dst_str(self._sync_dst):s}: '
                f'{(base_packet + packet).hex()}'
            )


def _dst_str(dst: tuple[str, int] | str) -> str:
    if isinstance(dst, str):
        return dst
    ip, port = dst
    return f'{ip:s}:{port:d}'

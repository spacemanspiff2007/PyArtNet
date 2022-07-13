import binascii
import logging
import socket
import struct

log = logging.getLogger('pyartnet.DmxClient')


class DmxClient:
    def __init__(self, host: str, port: int):
        """
        :param host: IP of the Art-Net Node
        :param port: Port of the Art-Net Node
        """
        self.__host = host
        self.__port = port

    def update(self, universe_nr, universe):
        """
        Send the current state of DMX values to the gateway via UDP packet.
        """
        raise NotImplementedError()


class ArtNetClient(DmxClient):

    def __init__(self, host: str, port: int = 0x1936, sequence_counter: bool = True, broadcast: bool = False):
        """
        :param host: IP of the Art-Net Node
        :param port: Port of the Art-Net Node
        :param broadcast: activate if you want to send the frames to a broadcast address
        """
        super().__init__(host, port)

        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self.__socket.setblocking(False)
        if broadcast:
            self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        packet = bytearray()
        packet.extend(map(ord, "Art-Net"))
        packet.append(0x00)  # Null terminate Art-Net
        packet.extend([0x00, 0x50])  # Opcode ArtDMX 0x5000 (Little endian)
        packet.extend([0x00, 0x0e])  # Protocol version 14
        self.__base_packet = packet

        self.__sequence_counter = 255 if sequence_counter else 0

    def update(self, universe_nr, universe):
        """
        Send the current state of DMX values to the gateway via UDP packet.
        """
        # Copy the base packet then add the channel array
        packet = self.__base_packet[:]

        if self.__sequence_counter:
            self.__sequence_counter += 1
            if self.__sequence_counter > 255:
                self.__sequence_counter = 1

        packet.append(self.__sequence_counter)  # Sequence,
        packet.append(0x00)  # Physical
        packet.append(universe_nr & 0xFF)  # Universe LowByte
        packet.append(universe_nr >> 8 & 0xFF)  # Universe HighByte

        packet.extend(struct.pack('>h', universe.highest_channel))  # Pack the number of channels Big endian
        packet.extend(universe.data)
        self.__socket.sendto(packet, (self.__host, self.__port))

        if log.isEnabledFor(logging.DEBUG):
            self.__log_artnet_frame(packet)

    def __log_artnet_frame(self, p: bytearray):
        """Log Artnet Frame"""
        assert isinstance(p, bytearray)

        # runs the first time
        if not hasattr(self, '_log_ctr'):
            self._log_ctr = -1
            self._log_show = [False for k in range(103)]

        self._log_ctr += 1
        if self._log_ctr >= 10:
            self._log_ctr = 0
        show_description: bool = self._log_ctr == 0

        host_fmt = ' ' * (36 + len(self.__host))
        out_desc = '{:s} {:2s} {:2s} {:4s} {:4s}'.format(host_fmt, 'Sq', '', 'Univ', ' Len')

        _max_channel = p[16] << 8 | p[17]
        pre = binascii.hexlify(bytearray(p[:12])).decode('ascii').upper()
        out = f'Packet to {self.__host:s}: {pre} {p[12]:02x} {p[13]:02x} {p[13]:02x}{p[14]:02x} {_max_channel:04x}'

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
                # do not print multiple shortings
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
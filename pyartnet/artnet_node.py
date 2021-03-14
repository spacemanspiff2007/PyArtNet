import asyncio
import binascii
import contextlib
import logging
import socket
import struct
import time
import typing
from traceback import format_exc

from .dmx_universe import DmxUniverse

log = logging.getLogger('pyartnet.ArtNetNode')


class ArtNetNode:
    def __init__(self, host: str, port: int = 0x1936, max_fps: int = 25,
                 refresh_every: int = 2, sequence_counter: bool = True, broadcast: bool = False):
        """
        :param host: IP of the Art-Net Node
        :param port: Port of the Art-Net Node
        :param max_fps: How many packets per sec shall max be send
        :param refresh_every: Resend the data every x seconds, 0 to deactivate
        :param sequence_counter: activate the sequence counter in the packages
        :param broadcast: activate if you want to send the frames to a broadcast address
        """
        self.__host = host
        self.__port = port

        self.__sequence_counter = 255 if sequence_counter else 0

        self.__universe = {}  # type: typing.Dict[int, DmxUniverse]

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.setblocking(False)
        if broadcast:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        packet = bytearray()
        packet.extend(map(ord, "Art-Net"))
        packet.append(0x00)          # Null terminate Art-Net
        packet.extend([0x00, 0x50])  # Opcode ArtDMX 0x5000 (Little endian)
        packet.extend([0x00, 0x0e])  # Protocol version 14
        self.__base_packet = packet

        self.__task = None

        max_fps = max(1, min(max_fps, 40))
        self.sleep_time = 1 / max_fps

        self.refresh_every = refresh_every
        log.debug(f'Created ArtNetNode: {max_fps}fps, {self.refresh_every}s refresh, '
                  f'[{"x" if sequence_counter else ""}] sequence counter')

    def get_universe(self, nr: int) -> DmxUniverse:
        assert isinstance(nr, int), type(nr)
        assert nr >= 0, nr
        return self.__universe[nr]

    def add_universe(self, nr: int = 0) -> DmxUniverse:
        """Creates a new universe and adds it to the node"""
        assert isinstance(nr, int), type(nr)
        assert nr >= 0, nr

        self.__universe[nr] = u = DmxUniverse(self)
        return u

    async def __worker(self):
        log.debug('Worker started')
        last_update = time.time()

        while True:
            await asyncio.sleep(self.sleep_time)

            try:
                fades_running = False
                for u in self.__universe.values():
                    if u.process():
                        fades_running = True

                if fades_running:
                    self.update()
                    last_update = time.time()
                else:
                    if self.refresh_every > 0:
                        # refresh data all 2 secs
                        if time.time() - last_update > self.refresh_every:
                            self.update()
                            last_update = time.time()
            except Exception:
                log.error(f'Error in worker for {self.__host}:')
                for line in format_exc().splitlines():
                    log.error(line)

    async def start(self):
        if self.__task:
            return None
        self.__task = asyncio.create_task(self.__worker())

    async def stop(self):
        if not self.__task:
            return None

        self.__task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await self.__task

        self.__task = None
        log.debug('Worker stopped')
        return None

    def update(self):
        """Send an update to the artnet device. This normally happens automatically"""

        for universe_nr, universe in self.__universe.items():
            assert isinstance(universe_nr, int), type(universe_nr)
            assert isinstance(universe, DmxUniverse), type(universe)

            # don't send empty universes
            if universe.highest_channel <= 0:
                continue

            # Copy the base packet then add the channel array
            packet = self.__base_packet[:]

            if self.__sequence_counter:
                self.__sequence_counter += 1
                if self.__sequence_counter > 255:
                    self.__sequence_counter = 1

            packet.append(self.__sequence_counter)              # Sequence,
            packet.append(0x00)                                 # Physical
            packet.append(universe_nr & 0xFF)                   # Universe LowByte
            packet.append(universe_nr >> 8 & 0xFF)              # Universe HighByte

            packet.extend(struct.pack('>h', universe.highest_channel))  # Pack the number of channels Big endian
            packet.extend(universe.data)
            self._socket.sendto(packet, (self.__host, self.__port))

            if log.isEnabledFor(logging.DEBUG):
                self.__log_artnet_frame(packet)

        return None

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

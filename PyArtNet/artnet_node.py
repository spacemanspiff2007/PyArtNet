import logging, asyncio
import socket, time
import struct
import typing
import contextlib, binascii

from .dmx_universe import DmxUniverse

# https://github.com/jnimmo/hass-artnet/blob/master/artnet.py
log = logging.getLogger('PyArtnet.ArtNetNode')

class ArtNetNode:
    def __init__(self, host, port = 0x1936, max_refresh = 30, sequence_counter = True):
        #target
        self.__host = host
        self.__port = port

        self.__sequence_counter = 255 if sequence_counter else 0

        self.__universe = {}  # type: typing.Dict[int, DmxUniverse]

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP

        packet = bytearray()
        packet.extend(map(ord, "Art-Net"))
        packet.append(0x00)          # Null terminate Art-Net
        packet.extend([0x00, 0x50])  # Opcode ArtDMX 0x5000 (Little endian)
        packet.extend([0x00, 0x0e])  # Protocol version 14
        self.__base_packet = packet

        self.__task = None

        max_refresh = max(1, min(max_refresh, 40))
        self.sleep_time_ms = 1 / max_refresh

    def get_universe(self, nr : int) -> DmxUniverse:
        return self.__universe[nr]

    def add_universe(self, nr : int = 0) -> DmxUniverse:
        "Creates a new niverse and adds it to the node"
        u = DmxUniverse(self)
        self.__universe[nr] = u
        return u

    async def __worker(self):
        log.debug('Worker started')
        last_update = time.time()

        while True:
            await asyncio.sleep(self.sleep_time_ms)

            fades_running = False
            for u in self.__universe.values():
                if u.process():
                    fades_running = True

            if fades_running:
                self.update()
                last_update = time.time()
            else:
                # refresh data all 2 secs
                if time.time() - last_update > 2:
                    self.update()
                    last_update = time.time()


    def start(self):
        if self.__task:
            return None

        loop = asyncio.get_event_loop()
        self.__task = loop.create_task(self.__worker())
        #self.__thread = asyncio.ensure_future(self.__worker())


    async def stop(self):
        if not self.__task:
            return None

        self.__task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await self.__task

        log.debug('Worker stopped')
        self.__task = None
        return None

    def update(self):
        "Send an update to the artnet device. This normally happens automatically"

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
            self.__log_artnet_frame(packet)
            self._socket.sendto(packet, (self.__host, self.__port))


    def __log_artnet_frame(self, p):
        "Log Artnet Frame"
        assert isinstance(p, bytearray)

        if not log.isEnabledFor(logging.DEBUG):
            return None

        #runs the first time
        if not hasattr(self, '_log_ctr'):
            self._log_ctr = -1
            self._log_show = [False for k in range(103)]

        self._log_ctr += 1
        if self._log_ctr >= 10:
            self._log_ctr = 0


        out_desc = '{:49s} {:2s} {:2s} {:4s} {:4s}'.format('', 'Sq', '', 'Univ', ' Len')

        _channels = p[16] << 8 | p[17]
        pre = binascii.hexlify(bytearray(p[:12])).decode('ascii').upper()
        out = f'Packet to {self.__host}: {pre} {p[12]:02x} {p[13]:02x} {p[13]:02x}{p[14]:02x} {_channels:04x}'

        #check what to print
        for k in range(_channels):
            if p[18 + k]:
                #once we change something print channel index
                if self._log_show[k//5] is False:
                    self._log_ctr = 0
                self._log_show[k//5] = True

        for k in range(0, _channels, 5):

            # if there was never anything active do not print, but print the last block
            if not self._log_show[k//5] and not k +5 > _channels:
                # do not print multiple shortings
                if out.endswith('...'):
                    continue

                out_desc += '  - '
                out += ' ...'
                continue

            #separator
            if out.endswith('...'):
                out_desc += ' '
                out += ' '
            else:
                out_desc += '- '
                out += '  '

            #block of channels
            for i in range(5):
                if k + i < _channels:
                    out_desc += f'{k+i + 1:<3d} '
                    out += f'{p[18 + k+i]:03d} '

        if self._log_ctr == 0:
            log.debug(out_desc)
        log.debug(out)

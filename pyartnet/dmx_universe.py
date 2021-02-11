import asyncio
import logging
import typing

import pyartnet
from .errors import ChannelExistsError, ChannelNotFoundError, OverlappingChannelError

log = logging.getLogger('pyartnet.DmxUniverse')


class DmxUniverse:
    def __init__(self, artnet_node):
        self.highest_channel: int = 0
        self.data: bytearray = bytearray()
        self.__chans: typing.Dict[str, pyartnet.DmxChannel] = {}

        assert isinstance(artnet_node, pyartnet.ArtNetNode)
        self._artnet_node: pyartnet.ArtNetNode = artnet_node

        self.__fade_running = False

        self.output_correction = None

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel(self, channel_name: str) -> pyartnet.DmxChannel:
        if not isinstance(channel_name, str):
            raise TypeError('Channel name must be str')

        try:
            return self.__chans[channel_name]
        except KeyError:
            raise ChannelNotFoundError(f'Channel "{channel_name}" not found in the universe!') from None

    def add_channel(self, start: int, width: int, channel_name: str = '',
                    channel_type: typing.Type[pyartnet.DmxChannel] = pyartnet.DmxChannel) -> pyartnet.DmxChannel:
        assert isinstance(channel_name, str), type(channel_name)
        assert issubclass(channel_type, pyartnet.DmxChannel)

        chan = channel_type(self, start, width)

        # build name if not supplied
        if not channel_name:
            channel_name = f'{start:d}/{width:d}'

        # Make sure we don't accidentally overwrite the channel
        if channel_name in self.__chans:
            raise ChannelExistsError(f'Channel "{channel_name}" does already exist in the universe!')

        # Make sure channels are not overlapping because they will overwrite each other
        # and this leads to unintended behavior
        for _n, _c in self.__chans.items():
            if _c.start > chan.stop or _c.stop < chan.start:
                continue
            for i in range(_c.start, _c.stop + 1):
                if start <= i <= chan.stop:
                    raise OverlappingChannelError(f'New channel {channel_name} is overlapping with channel {_n:s}!')

        # Keep track of highest channel so we can pad
        highest_was = self.highest_channel
        self.highest_channel = max(self.highest_channel, chan.stop)

        # round channels
        if self.highest_channel % 2:
            self.highest_channel += 1

        # pad universe with 0
        if highest_was != self.highest_channel:
            for i in range(self.highest_channel - len(self.data)):
                self.data.append(0)

        # add channel to universe
        self.__chans[channel_name] = chan
        log.debug(f'Added channel "{channel_name}": start: {start:d}, stop: {start + width - 1:d}')
        return chan

    def process(self) -> bool:
        """
        Process fades n stuff
        :return: True if something was processed
        """
        running = False
        for c in self.__chans.values():
            if not c.process():
                continue

            running = True

            # get new universe Data
            for k, val in enumerate(c.get_bytes()):
                self.data[c.start + k - 1] = val

        self.__fade_running = running
        return self.__fade_running

    async def wait_for_fades(self):
        while self.__fade_running:
            await asyncio.sleep(self._artnet_node.sleep_time)

    # -----------------------------------------------------------
    # emulate container
    def __len__(self):
        return len(self.__chans)

    def __getitem__(self, item: str) -> pyartnet.DmxChannel:
        return self.get_channel(item)

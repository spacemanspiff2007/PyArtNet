import asyncio
import typing

import pyartnet


class DmxUniverse:
    def __init__(self, artnet_node):
        self.highest_channel = 0
        self.data = bytearray()
        self.__channels = []    # type: typing.List[pyartnet.DmxChannel]
        self.__channel_names = {}

        assert isinstance(artnet_node, pyartnet.ArtNetNode)
        self.artnet_node: pyartnet.ArtNetNode = artnet_node

        self.__fade_running = False

        self.output_correction = None

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel(self, channel_name: str) -> pyartnet.DmxChannel:
        assert isinstance(channel_name, str), type(channel_name)
        return self.__channel_names[channel_name]

    def add_channel(self, start: int, width: int, channel_name: str = '') -> pyartnet.DmxChannel:
        assert isinstance(channel_name, str), type(channel_name)
        c = pyartnet.DmxChannel(self, start, width)

        self.highest_channel = max(self.highest_channel, c.start + c.width - 1)

        # round channels
        if self.highest_channel % 2:
            self.highest_channel += 1

        # pad universe with 0
        while len(self.data) < self.highest_channel:
            self.data.append(0)

        # add channel to universe
        self.__channels.append(c)
        self.__channel_names[channel_name if channel_name else f'{c.start}/{c.width}'] = c
        return c

    def process(self) -> bool:
        """
        Process fades n stuff
        :return: True if something was processed
        """
        running = False
        for c in self.__channels:
            if not c.process():
                continue

            running = True

            # get new universe Data
            new_val = c.get_channel_values()
            for k, val in enumerate(new_val):
                self.data[c.start + k - 1] = val

        self.__fade_running = running
        return self.__fade_running

    async def wait_for_fades(self):
        while self.__fade_running:
            await asyncio.sleep(self.artnet_node.sleep_time)

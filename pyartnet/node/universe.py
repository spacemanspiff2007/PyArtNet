import asyncio
import logging
from time import monotonic
from typing import Dict, Type, Final

import pyartnet
from .base_node import TYPE_NODE

from pyartnet.errors import ChannelExistsError, ChannelNotFoundError, OverlappingChannelError, InvalidUniverseAddress
from .output_correction import OutputCorrection

log = logging.getLogger('pyartnet.DmxUniverse')


class Universe(OutputCorrection):
    def __init__(self, node: TYPE_NODE, universe: int = 0):
        super().__init__()

        if not 0 <= universe <= 32767:
            raise InvalidUniverseAddress()

        self._node: Final = node
        self._universe: Final = universe

        self._data: bytearray = bytearray()
        self._data_changed = True
        self._last_send: float = 0

        self._channels: Dict[str, pyartnet.node.TYPE_CHANNEL] = {}

    def _apply_output_correction(self):
        for c in self._channels.values():   # type: pyartnet.node.TYPE_CHANNEL
            # noinspection PyProtectedMember
            c._apply_output_correction()

    def channel_changed(self, channel: 'pyartnet.node.Channel'):
        # update universe buffer
        channel.to_buffer(self._data)

        # signal that this universe has changed
        self._data_changed = True

        # start fade/refresh task if necessary
        # noinspection PyProtectedMember
        if self._node._process_task is None:
            # noinspection PyProtectedMember
            self._node._start_process_task()

    def send_data(self):
        self._node.send_universe(self._universe, self._data)
        self._last_send = monotonic()
        self._data_changed = False

    def get_channel(self, channel_name: str) -> pyartnet.DmxChannel:
        if not isinstance(channel_name, str):
            raise TypeError('Channel name must be str')

        try:
            return self._channels[channel_name]
        except KeyError:
            raise ChannelNotFoundError(f'Channel "{channel_name}" not found in the universe!') from None

    def add_channel(self, start: int, width: int, channel_name: str = '',
                    channel_type: Type['pyartnet.node.TYPE_CHANNEL'] = pyartnet.DmxChannel) -> pyartnet.DmxChannel:
        assert isinstance(channel_name, str), type(channel_name)
        assert issubclass(channel_type, pyartnet.DmxChannel)

        chan = channel_type(self, start, width) # type: 'pyartnet.node.TYPE_CHANNEL'

        # build name if not supplied
        if not channel_name:
            channel_name = f'{start:d}/{width:d}'

        # Make sure we don't accidentally overwrite the channel
        if channel_name in self._channels:
            raise ChannelExistsError(f'Channel "{channel_name}" does already exist in the universe!')

        # Make sure channels are not overlapping because they will overwrite each other
        # and this leads to unintended behavior
        for _n, _c in self._channels.items():
            if _c.start > chan.stop or _c.stop < chan.start:
                continue
            for i in range(_c.start, _c.stop + 1):
                if start <= i <= chan.stop:
                    raise OverlappingChannelError(f'New channel {channel_name} is overlapping with channel {_n:s}!')

        # Calculate highest channel
        highest_was = len(self._data)
        highest_new = max(highest_was, chan.stop)
        if highest_new % 2:
            highest_new += 1

        # pad universe with 0
        if highest_was != highest_new:
            for i in range(highest_new - highest_was):
                self._data.append(0)

        # add channel to universe
        self._channels[channel_name] = chan
        log.debug(f'Added channel "{channel_name}": start: {start:d}, stop: {start + width - 1:d}')

        # noinspection PyProtectedMember
        chan._apply_output_correction()
        return chan

    # -----------------------------------------------------------
    # emulate container
    def __len__(self):
        return len(self._channels)

    def __getitem__(self, item: str) -> pyartnet.DmxChannel:
        return self.get_channel(item)

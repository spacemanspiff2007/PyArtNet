import logging
from time import monotonic
from typing import Dict, Final, Literal

import pyartnet
from pyartnet.errors import ChannelExistsError, ChannelNotFoundError, InvalidUniverseAddress, OverlappingChannelError

from .output_correction import OutputCorrection

log = logging.getLogger('pyartnet.DmxUniverse')


# noinspection PyProtectedMember
class Universe(OutputCorrection):
    def __init__(self, node: 'pyartnet.node.BaseNode', universe: int = 0):
        super().__init__()

        if not 0 <= universe <= 32767:
            raise InvalidUniverseAddress()

        self._node: Final = node
        self._universe: Final = universe

        self._data: bytearray = bytearray()
        self._data_changed = True
        self._last_send: float = 0

        self._channels: Dict[str, 'pyartnet.node.Channel'] = {}

    def _apply_output_correction(self):
        for c in self._channels.values():
            c._apply_output_correction()

    def channel_changed(self, channel: 'pyartnet.node.Channel'):
        # update universe buffer
        channel.to_buffer(self._data)

        # signal that this universe has changed
        self._data_changed = True

        # start fade/refresh task if necessary
        # noinspection PyProtectedMember
        if self._node._process_task is None:
            self._node._start_process_task()

    def send_data(self):
        self._node._send_universe(self._universe, self._data)
        self._last_send = monotonic()
        self._data_changed = False

    def get_channel(self, channel_name: str) -> 'pyartnet.node.Channel':
        if not isinstance(channel_name, str):
            raise TypeError('Channel name must be str')

        try:
            return self._channels[channel_name]
        except KeyError:
            raise ChannelNotFoundError(f'Channel "{channel_name}" not found in the universe!') from None

    def add_channel(self,
                    start: int, width: int,
                    channel_name: str = '',
                    byte_size: int = 1, byte_order: Literal['big', 'little'] = 'little') -> 'pyartnet.node.Channel':

        chan = pyartnet.node.Channel(self, start, width)

        # build name if not supplied
        if not channel_name:
            channel_name = f'{start:d}/{width:d}'

        # Make sure we don't accidentally overwrite the channel
        if channel_name in self._channels:
            raise ChannelExistsError(f'Channel "{channel_name}" does already exist in the universe!')

        # Make sure channels are not overlapping because they will overwrite each other
        # and this leads to unintended behavior
        for _n, _c in self._channels.items():
            if _c._start > chan._stop or _c._stop < chan._start:
                continue
            for i in range(_c._start, _c._stop + 1):
                if start <= i <= chan._stop:
                    raise OverlappingChannelError(f'New channel {channel_name} is overlapping with channel {_n:s}!')

        self._resize_universe(chan._stop)

        # add channel to universe
        self._channels[channel_name] = chan
        log.debug(f'Added channel "{channel_name}": start: {start:d}, stop: {start + width - 1:d}')

        chan._apply_output_correction()
        return chan

    def _resize_universe(self, min_size: int):

        new_size = max(min_size, 2)
        for c in self._channels.values():
            new_size = max(new_size, c._stop)
        if new_size % 2:
            new_size += 1

        diff = new_size - len(self._data)
        if not diff:
            return None

        if diff < 0:
            for _ in range(- diff):
                self._data.pop()
        else:
            for _ in range(diff):
                # pad universe data with 0 is it's off
                self._data.append(0)

    # -----------------------------------------------------------
    # emulate container
    def __len__(self):
        return len(self._channels)

    def __getitem__(self, item: str) -> 'pyartnet.node.Channel':
        return self.get_channel(item)

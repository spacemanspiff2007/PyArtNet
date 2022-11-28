import asyncio
import logging
import math
from typing import Any, Callable, Iterable, List, Optional, Type, Union, Final, Literal, TypeVar

import pyartnet
from pyartnet.errors import ChannelValueOutOfBounds, ValueCountDoesNotMatchChannelWidthError, ChannelOutOfUniverseError, \
    ChannelWidthInvalid
from pyartnet.fades import FadeBase, LinearFade

from .animation_node import TYPE_ANIMATION_NODE
from array import array
from pyartnet.nodes.node_universe import DmxUniverse
from pyartnet.output_correction import linear

log = logging.getLogger('pyartnet.DmxChannel')


ARRAY_TYPE: Final = {
    1: 'B',  # unsigned char: min size 1 byte
    2: 'H',  # unsigned short: min size 2 bytes
    3: 'L',  # unsigned long: min size 4 bytes
    4: 'L'   # unsigned long: min size 4 bytes
}


HINT_CHANNEL = TypeVar('HINT_CHANNEL', bound='ChannelBytes')


class ChannelBytes:
    def __init__(self, universe: DmxUniverse,
                 start: int, width: int,
                 byte_size: int = 1, byte_order: Literal['big', 'little'] = 'little'):

        # Validate Boundaries
        if byte_size not in ARRAY_TYPE:
            raise ValueError(f'Value size must be {", ".join(map(str, ARRAY_TYPE))}')

        if start < 1 or start > 512:
            raise ChannelOutOfUniverseError(
                f'Start position of channel out of universe (1..512): {start}')

        if width <= 0 or not isinstance(width, int):
            raise ChannelWidthInvalid(
                f'Channel width must be int > 0: {width} ({type(width)})')

        total_byte_width: Final = width * byte_size

        self._start: Final = start
        self._width: Final = width
        self._stop: Final = start + total_byte_width - 1

        if self._stop > 512:
            raise ChannelOutOfUniverseError(
                f'End position of channel out of universe (1..512): '
                f'start: {self._start} width: {self._width} * {byte_size}bytes -> {self._stop}'
            )

        # value representation
        self._byte_size: Final = byte_size
        self._byte_order: Final = byte_order
        self._value_max: Final = 256 ** self._byte_size - 1

        null_vals = [0 for _ in range(self._width)]
        self._values_raw: array[int] = array(ARRAY_TYPE[self._byte_size], null_vals)    # uncorrected values
        self._values_act: array[int] = array(ARRAY_TYPE[self._byte_size], null_vals)    # values after output correction

        # Parents
        self._parent_universe: Final = universe
        self._parent_node: Final = universe._parent_node

        # ---------------------------------------------------------------------
        # Values that can be set by the user
        # ---------------------------------------------------------------------
        self.output_correction: Optional[Callable[[float, int], float]] = None

    def get_values(self) -> List[int]:
        return self._values_raw.tolist()

    def set_values(self, values: Iterable[Union[int, float]]):
        # get output correction function
        correction: Callable[[float, int], float] = linear
        if self.output_correction is not None:
            correction = self.output_correction
        elif self._parent_universe.output_correction is not None:
            correction = self.output_correction

        value_max = self._value_max
        for i, val in enumerate(values):
            if not 0 <= val <= value_max:
                raise ChannelValueOutOfBounds(f'Channel value out of bounds! 0 <= {val} <= {value_max:d}')

            self._values_raw[i] = round(val)
            if correction is not linear:
                val = correction(val, self._value_max)
            self._values_act[i] = round(val)

    def to_buffer(self, buf: bytearray):

        byte_order = self._byte_order
        byte_size = self._byte_size

        start = self._start
        for value in self._values_act:
            buf[start: start + byte_size] = value.to_bytes(byte_size, byte_order, signed=False)
            start += byte_size

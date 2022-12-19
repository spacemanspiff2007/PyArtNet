import logging
from array import array
from typing import Any, Callable, Final, Iterable, List, Literal, Optional, Union

from pyartnet.errors import ChannelOutOfUniverseError, ChannelValueOutOfBounds, \
    ChannelWidthInvalid, ValueCountDoesNotMatchChannelWidthError
from pyartnet.output_correction import linear

from .channel_fade import ChannelBoundFade
from .output_correction import OutputCorrection
from .universe import Universe

log = logging.getLogger('pyartnet.DmxChannel')



ARRAY_TYPE: Final = {
    1: 'B',  # unsigned char : min size 1 byte
    2: 'H',  # unsigned short: min size 2 bytes
    3: 'L',  # unsigned long : min size 4 bytes
    4: 'L'   # unsigned long : min size 4 bytes
}


class Channel(OutputCorrection):
    def __init__(self, universe: Universe,
                 start: int, width: int,
                 byte_size: int = 1, byte_order: Literal['big', 'little'] = 'little'):
        super().__init__()

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
        self._parent_node: Final = universe._node

        self._correction_current: Callable[[float, int], float] = linear

        # Fade
        self._current_fade: Optional[ChannelBoundFade] = None

        # ---------------------------------------------------------------------
        # Values that can be set by the user
        # ---------------------------------------------------------------------
        # Callbacks
        self.callback_fade_finished: Optional[Callable[[Channel], Any]] = None


    def _apply_output_correction(self):
        # default correction is linear
        self._correction_current = linear

        # inherit correction if it is not set first from universe and then from the node
        for obj in (self, self._parent_universe, self._parent_node):
            if obj._correction_output is not None:
                self._correction_current = obj._correction_output
                return None

    def get_values(self) -> List[int]:
        return self._values_raw.tolist()

    def set_values(self, values: Iterable[Union[int, float]]):
        # get output correction function
        correction = self._correction_current
        value_max = self._value_max

        changed = False
        i: int = -1
        for i, val in enumerate(values):
            if not 0 <= val <= value_max:
                raise ChannelValueOutOfBounds(f'Channel value out of bounds! 0 <= {val} <= {value_max:d}')

            self._values_raw[i] = raw_new = round(val)
            act_new = round(correction(val, value_max)) if correction is not linear else raw_new
            if self._values_act[i] != act_new:
                changed = True
            self._values_act[i] = act_new

        # check that we passed all values
        i += 1
        if i != self._width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self._width} but got {i}!')

        if changed:
            self._parent_universe.channel_changed(self)

    def to_buffer(self, buf: bytearray):
        byte_order = self._byte_order
        byte_size = self._byte_size

        start = self._start - 1  # universe starts count with 1
        for value in self._values_act:
            buf[start: start + byte_size] = value.to_bytes(byte_size, byte_order, signed=False)
            start += byte_size

    def __repr__(self):
        return f'<{self.__class__.__name__:s} {self._start}/{self._width} {self._byte_size * 8}bit>'

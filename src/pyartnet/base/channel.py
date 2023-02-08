import logging
from array import array
from logging import DEBUG as LVL_DEBUG
from math import ceil
from typing import Any, Callable, Final, Iterable, List, Literal, Optional, Type, Union

from pyartnet.errors import ChannelOutOfUniverseError, ChannelValueOutOfBoundsError, \
    ChannelWidthError, ValueCountDoesNotMatchChannelWidthError
from pyartnet.output_correction import linear

from ..fades import FadeBase, LinearFade
from .channel_fade import ChannelBoundFade
from .output_correction import OutputCorrection
from .universe import BaseUniverse

log = logging.getLogger('pyartnet.Channel')


ARRAY_TYPE: Final = {
    1: 'B',  # unsigned char : min size 1 byte
    2: 'H',  # unsigned short: min size 2 bytes
    3: 'L',  # unsigned long : min size 4 bytes
    4: 'L'   # unsigned long : min size 4 bytes
}


class Channel(OutputCorrection):
    def __init__(self, universe: BaseUniverse,
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
            raise ChannelWidthError(
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
        self._buf_start: Final = self._start - 1

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
        """Get the current (uncorrected) channel values

        :return: list of channel values
        """
        return self._values_raw.tolist()

    def set_values(self, values: Iterable[Union[int, float]]):
        """Set values for a channel without a fade

        :param values: Iterable of values with the same size as the channel width
        """
        # get output correction function
        correction = self._correction_current
        value_max = self._value_max

        changed = False
        i: int = -1
        for i, val in enumerate(values):
            raw_new = round(val)
            if not 0 <= raw_new <= value_max:
                raise ChannelValueOutOfBoundsError(f'Channel value out of bounds! 0 <= {val} <= {value_max:d}')

            self._values_raw[i] = raw_new
            act_new = round(correction(val, value_max)) if correction is not linear else raw_new
            if self._values_act[i] != act_new:
                changed = True
            self._values_act[i] = act_new

        # check that we passed all values
        if i + 1 != self._width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self._width} but got {i + 1}!')

        if changed:
            self._parent_universe.channel_changed(self)
        return self

    def to_buffer(self, buf: bytearray):
        byte_order = self._byte_order
        byte_size = self._byte_size

        start = self._buf_start
        for value in self._values_act:
            buf[start: start + byte_size] = value.to_bytes(byte_size, byte_order, signed=False)
            start += byte_size
        return self

    # noinspection PyProtectedMember
    def add_fade(self, values: Iterable[Union[int, FadeBase]], duration_ms: int,
                 fade_class: Type[FadeBase] = LinearFade):
        """Add and schedule a new fade for the channel

        :param values: Target values for the fade
        :param duration_ms: Duration for the fade in ms
        :param fade_class: What kind of fade
        """

        if self._current_fade is not None:
            self._current_fade.cancel()
            self._current_fade = None

        # calculate how much steps we will be having
        step_time_ms = int(self._parent_node._process_every * 1000)
        duration_ms = max(duration_ms, step_time_ms)
        fade_steps: int = ceil(duration_ms / step_time_ms)

        # build fades
        fades: List[FadeBase] = []
        i: int = -1
        for i, val in enumerate(values):    # noqa: B007
            # default is linear
            k = fade_class(val) if not isinstance(val, FadeBase) else val
            fades.append(k)

            if not 0 <= k.val_target <= self._value_max:
                raise ChannelValueOutOfBoundsError(
                    f'Target value out of bounds! 0 <= {k.val_target} <= {self._value_max}')

            k.initialize(fade_steps)

        # check that we passed all values
        if i + 1 != self._width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self._width} but got {i + 1}!')

        # Add to scheduling
        self._current_fade = ChannelBoundFade(self, fades)
        self._parent_node._process_jobs.append(self._current_fade)

        # start fade/refresh task if necessary
        self._parent_node._process_task.start()

        if log.isEnabledFor(LVL_DEBUG):
            log.debug(f'Added fade with {fade_steps} steps:')
            for i, fade in enumerate(fades):
                log.debug(f'CH {self._start + i}: {self._values_raw[i]:03d} -> {fade.val_target:03d}'
                          f' | {fade.debug_initialize():s}')
        return self

    def __await__(self):
        if self._current_fade is None:
            return False
        yield from self._current_fade.event.wait().__await__()
        return True

    def __repr__(self):
        return f'<{self.__class__.__name__:s} {self._start:d}/{self._width:d} {self._byte_size * 8:d}bit>'

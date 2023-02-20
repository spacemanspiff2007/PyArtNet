import logging
import warnings
from array import array
from logging import DEBUG as LVL_DEBUG
from math import ceil
from typing import Any, Callable, Collection, Final, List, Literal, Optional, Type, Union

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

    def set_values(self, values: Collection[Union[int, float]]):
        """Set values for a channel without a fade

        :param values: Iterable of values with the same size as the channel width
        """
        # get output correction function
        if len(values) != self._width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self._width} but got {len(values)}!')

        correction = self._correction_current
        value_max = self._value_max

        changed = False
        for i, val in enumerate(values):
            raw_new = round(val)
            if not 0 <= raw_new <= value_max:
                raise ChannelValueOutOfBoundsError(f'Channel value out of bounds! 0 <= {val} <= {value_max:d}')

            self._values_raw[i] = raw_new
            act_new = round(correction(val, value_max)) if correction is not linear else raw_new
            if self._values_act[i] != act_new:
                changed = True
            self._values_act[i] = act_new

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

    def add_fade(self, values: Collection[Union[int, FadeBase]], duration_ms: int,
                 fade_class: Type[FadeBase] = LinearFade):
        warnings.warn(
            f"{self.set_fade.__name__:s} is deprecated, use {self.set_fade.__name__:s} instead", DeprecationWarning)
        return self.set_fade(values, duration_ms, fade_class)

    # noinspection PyProtectedMember
    def set_fade(self, values: Collection[Union[int, FadeBase]], duration_ms: int,
                 fade_class: Type[FadeBase] = LinearFade):
        """Add and schedule a new fade for the channel

        :param values: Target values for the fade
        :param duration_ms: Duration for the fade in ms
        :param fade_class: What kind of fade
        """
        # check that we passed all values
        if len(values) != self._width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self._width} but got {len(values)}!')

        if self._current_fade is not None:
            self._current_fade.cancel()
            self._current_fade = None

        # calculate how much steps we will be having
        step_time_ms = int(self._parent_node._process_every * 1000)
        duration_ms = max(duration_ms, step_time_ms)
        fade_steps: int = ceil(duration_ms / step_time_ms)

        # build fades
        fades: List[FadeBase] = []
        for i, target in enumerate(values):
            # default is linear
            k = fade_class() if not isinstance(target, FadeBase) else target
            fades.append(k)

            if not 0 <= target <= self._value_max:
                raise ChannelValueOutOfBoundsError(
                    f'Target value out of bounds! 0 <= {target} <= {self._value_max}')

            k.initialize(self._values_raw[i], target, fade_steps)

        # Add to scheduling
        self._current_fade = ChannelBoundFade(self, fades)
        self._parent_node._process_jobs.append(self._current_fade)

        # start fade/refresh task if necessary
        self._parent_node._process_task.start()

        # todo: this on the ChannelBoundFade
        if log.isEnabledFor(LVL_DEBUG):
            log.debug(f'Added fade with {fade_steps} steps:')
            for i, fade in enumerate(fades):
                log.debug(f'CH {self._start + i}: {fade.debug_initialize():s}')
        return self

    def __await__(self):
        if self._current_fade is None:
            return False
        yield from self._current_fade.event.wait().__await__()
        return True

    def __repr__(self):
        return f'<{self.__class__.__name__:s} {self._start:d}/{self._width:d} {self._byte_size * 8:d}bit>'

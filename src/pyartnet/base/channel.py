from __future__ import annotations

import logging
import warnings
from array import array
from logging import DEBUG as LVL_DEBUG
from math import ceil
from typing import TYPE_CHECKING, Any, Final, Generator, Literal

from typing_extensions import Self

from pyartnet.base.channel_fade import ChannelBoundFade
from pyartnet.base.output_correction import OutputCorrection
from pyartnet.errors import (
    ChannelOutOfUniverseError,
    ChannelValueOutOfBoundsError,
    ChannelWidthError,
    ValueCountDoesNotMatchChannelWidthError,
)
from pyartnet.fades import FadeBase, LinearFade
from pyartnet.output_correction import linear


if TYPE_CHECKING:
    from collections.abc import Callable, Collection

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
                 byte_size: int = 1, byte_order: Literal['big', 'little'] = 'little') -> None:
        super().__init__()

        # Validate Boundaries
        if byte_size not in ARRAY_TYPE:
            msg = f'Value size must be {", ".join(map(str, ARRAY_TYPE))}'
            raise ValueError(msg)

        if start < 1 or start > 512:
            msg = f'Start position of channel out of universe (1..512): {start}'
            raise ChannelOutOfUniverseError(msg)

        if width <= 0 or not isinstance(width, int):
            msg = f'Channel width must be int > 0: {width} ({type(width)})'
            raise ChannelWidthError(msg)

        total_byte_width: Final = width * byte_size

        self._start: Final = start
        self._width: Final = width
        self._stop: Final = start + total_byte_width - 1

        if self._stop > 512:
            msg = (
                f'End position of channel out of universe (1..512): '
                f'start: {self._start} width: {self._width} * {byte_size}bytes -> {self._stop}'
            )
            raise ChannelOutOfUniverseError(msg)

        # value representation
        self._byte_size: Final = byte_size
        self._byte_order: Final = byte_order
        self._value_max: Final[int] = 256 ** self._byte_size - 1
        self._buf_start: Final[int] = self._start - 1

        null_vals = [0 for _ in range(self._width)]
        self._values_raw: array[int] = array(ARRAY_TYPE[self._byte_size], null_vals)    # uncorrected values
        self._values_act: array[int] = array(ARRAY_TYPE[self._byte_size], null_vals)    # values after output correction

        # Parents
        self._parent_universe: Final = universe
        self._parent_node: Final = universe._node

        self._correction_current: Callable[[float, int], float] = linear

        # Fade
        self._current_fade: ChannelBoundFade | None = None

        # ---------------------------------------------------------------------
        # Values that can be set by the user
        # ---------------------------------------------------------------------
        # Callbacks
        self.callback_fade_finished: Callable[[Channel], Any] | None = None

    def _apply_output_correction(self) -> None:
        # default correction is linear
        self._correction_current = linear

        # inherit correction if it is not set first from universe and then from the node
        for obj in (self, self._parent_universe, self._parent_node):
            if obj._correction_output is not None:
                self._correction_current = obj._correction_output
                return None
        return None

    def get_values(self) -> list[int]:
        """Get the current (uncorrected) channel values

        :return: list of channel values
        """
        return self._values_raw.tolist()

    def set_values(self, values: Collection[int | float]) -> Self:
        """Set values for a channel without a fade

        :param values: Iterable of values with the same size as the channel width
        """
        # get output correction function
        if len(values) != self._width:
            msg = f'Not enough fade values specified, expected {self._width} but got {len(values)}!'
            raise ValueCountDoesNotMatchChannelWidthError(
                msg)

        correction = self._correction_current
        value_max = self._value_max

        changed = False
        for i, val in enumerate(values):
            raw_new = round(val)
            if not 0 <= raw_new <= value_max:
                msg = f'Channel value out of bounds! 0 <= {val} <= {value_max:d}'
                raise ChannelValueOutOfBoundsError(msg)

            self._values_raw[i] = raw_new
            act_new = round(correction(val, value_max)) if correction is not linear else raw_new
            if self._values_act[i] != act_new:
                changed = True
            self._values_act[i] = act_new

        if changed:
            self._parent_universe.channel_changed(self)
        return self

    def to_buffer(self, buf: bytearray) -> Self:
        byte_order = self._byte_order
        byte_size = self._byte_size

        start = self._buf_start
        for value in self._values_act:
            buf[start: start + byte_size] = value.to_bytes(byte_size, byte_order, signed=False)
            start += byte_size
        return self

    def add_fade(self, values: Collection[int | FadeBase], duration_ms: int,
                 fade_class: type[FadeBase] = LinearFade) -> Self:
        warnings.warn(
            f'{self.set_fade.__name__:s} is deprecated, use {self.set_fade.__name__:s} instead',
            DeprecationWarning, stacklevel=2
        )
        return self.set_fade(values, duration_ms, fade_class)

    # noinspection PyProtectedMember
    def set_fade(self, values: Collection[int | FadeBase], duration_ms: int,
                 fade_class: type[FadeBase] = LinearFade) -> Self:
        """Add and schedule a new fade for the channel

        :param values: Target values for the fade
        :param duration_ms: Duration for the fade in ms
        :param fade_class: What kind of fade
        """
        # check that we passed all values
        if len(values) != self._width:
            msg = f'Not enough fade values specified, expected {self._width} but got {len(values)}!'
            raise ValueCountDoesNotMatchChannelWidthError(msg)

        if self._current_fade is not None:
            self._current_fade.cancel()
            self._current_fade = None

        # calculate how much steps we will be having
        step_time_ms = int(self._parent_node._process_every * 1000)
        duration_ms = max(duration_ms, step_time_ms)
        fade_steps: int = ceil(duration_ms / step_time_ms)

        # build fades
        fades: list[FadeBase] = []
        for i, target in enumerate(values):

            # Is a fade initialized by the user
            if isinstance(target, FadeBase):
                fades.append(target)
                continue

            if not 0 <= target <= self._value_max:
                msg = f'Target value out of bounds! 0 <= {target} <= {self._value_max}'
                raise ChannelValueOutOfBoundsError(msg)

            # default is linear
            _fade = fade_class()
            _fade.initialize(self._values_raw[i], target, fade_steps)
            fades.append(_fade)

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

    def __await__(self) -> Generator[None, None, bool]:
        if self._current_fade is None:
            return False
        yield from self._current_fade.event.wait().__await__()
        return True

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__:s} {self._start:d}/{self._width:d} {self._byte_size * 8:d}bit>'

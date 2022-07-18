import asyncio
import logging
import math
from typing import Any, Callable, Iterable, List, Optional, Type, Union

import pyartnet
from pyartnet.errors import ChannelValueOutOfBounds, ValueCountDoesNotMatchChannelWidthError
from pyartnet.fades import FadeBase, LinearFade

log = logging.getLogger('pyartnet.DmxChannel')


class DmxChannel:
    _CHANNEL_SIZE: int = 1                          # Channel size in byte
    _CHANNEL_MAX: int = 256 ** _CHANNEL_SIZE - 1    # Max value of the channel

    def __init__(self, universe: 'pyartnet.DmxUniverse', start: int, width: int):
        self.width: int = width
        byte_width: int = width * self._CHANNEL_SIZE

        self.start: int = start
        self.stop: int = start + byte_width - 1

        if self.start < 1 or self.start > 512:
            raise pyartnet.errors.ChannelOutOfUniverseError(
                f'Start position of channel out of universe (1..512): {self.start}')

        if width <= 0 or not isinstance(width, int):
            raise pyartnet.errors.ChannelWidthInvalid(f'Channel width must be int > 0: {width} ({type(width)})')

        if self.stop > 512:
            raise pyartnet.errors.ChannelOutOfUniverseError(
                f'End position of channel out of universe (1..512): '
                f'start: {self.start} width: {self.width} * {byte_width}bytes -> {self.stop}'
            )

        self.__val_raw_i = [0 for _ in range(self.width)]   # uncorrected values
        self.__val_act_i = [0 for _ in range(self.width)]   # values after output correction

        self.__fades: List[Optional[pyartnet.fades.FadeBase]] = [None for _ in range(self.width)]
        self.__fade_running = False

        self.__step_max = 0
        self.__step_is = 0

        assert isinstance(universe, pyartnet.DmxUniverse)
        self.__universe: pyartnet.DmxUniverse = universe

        # Output correction function
        self.output_correction = None

        # Callbacks
        self.callback_value_changed: Optional[Callable[[DmxChannel], Any]] = None
        self.callback_fade_finished: Optional[Callable[[DmxChannel], Any]] = None

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel_values(self) -> List[int]:
        return self.__val_act_i.copy()

    def get_bytes(self) -> Iterable:
        for obj in self.__val_act_i:
            if self._CHANNEL_SIZE == 1:
                yield obj
            else:
                for i in range(self._CHANNEL_SIZE, 0, -1):
                    val = (obj >> 8 * (i - 1)) & 0xFF
                    yield val

    async def add_fade(self, target_values: Iterable[Union[int, FadeBase]],
                 duration_ms: int, fade_class: Type[FadeBase] = LinearFade):

        fade_objs: List[FadeBase] = []
        for target_value in target_values:
            if not isinstance(target_value, FadeBase):
                k = fade_class(target_value)
            else:
                k = target_value

            fade_objs.append(k)

            assert isinstance(k, pyartnet.fades.FadeBase), type(k)
            assert isinstance(k.val_target, int)
            if not 0 <= k.val_target <= self._CHANNEL_MAX:
                raise ChannelValueOutOfBounds(f'Target value out of bounds! 0 <= {k.val_target} <= {self._CHANNEL_MAX}')

        if len(fade_objs) != self.width:
            raise ValueCountDoesNotMatchChannelWidthError(
                f'Not enough fade values specified, expected {self.width} but got {len(fade_objs)}!')

        # calculate how many steps we will be having
        step_time_ms = self.__universe.sleep_time * 1000
        duration_ms = max(duration_ms, step_time_ms)
        self.__step_max = math.ceil(duration_ms / step_time_ms)
        self.__step_is = 0

        # calculate required values
        for i, fade in enumerate(fade_objs):  # type: int, pyartnet.fades.FadeBase
            fade.val_start = self.__val_raw_i[i]
            fade.val_current = fade.val_start
            fade.initialize_fade(self.__step_max)
            self.__fades[i] = fade

        if log.isEnabledFor(logging.DEBUG):
            log._log(logging.DEBUG, f'Fade with {self.__step_max} steps:', [])
            for i in range(self.width):
                log._log(logging.DEBUG, 'CH {}: {:03d} -> {:03d} | {}'.format(
                    self.start + i, self.__val_raw_i[i], self.__fades[i].val_target, self.__fades[i].debug_initialize()
                ), [])

        self.__fade_running = True
        await self.__universe.animation_thread_start()
        return None

    async def wait_till_fade_complete(self):
        while self.__fade_running:
            await asyncio.sleep(self.__universe.sleep_time)

    def cancel_fades(self):
        self.__fade_running = False

    def process(self):
        if not self.__fade_running:
            return False

        channel_value_was = self.__val_act_i.copy()

        running = False
        for i, fade in enumerate(self.__fades):
            assert isinstance(fade, pyartnet.fades.FadeBase), type(fade)

            if fade.is_done():
                continue

            # get next value
            fade.calc_next_value()
            self.__val_raw_i[i] = current = round(fade.val_current)

            # apply output correction
            if self.output_correction is not None:
                self.__val_act_i[i] = round(self.output_correction(current, self._CHANNEL_MAX))
            elif self.__universe.output_correction is not None:
                self.__val_act_i[i] = round(self.__universe.output_correction(current, self._CHANNEL_MAX))
            else:
                self.__val_act_i[i] = round(current)

            running = True
        self.__fade_running = running

        # Channel callbacks
        if self.callback_value_changed is not None and channel_value_was != self.__val_act_i:
            self.callback_value_changed(self)
        if self.callback_fade_finished is not None and self.__fade_running is False:
            self.callback_fade_finished(self)

        # catch implementation errors
        if self.__step_is > self.__step_max:
            log.warning(f'Fades in Channel {self.start}:{self.width} did not finish! Aborting!')
            self.__fade_running = False
        self.__step_is += 1

        return self.__fade_running


class DmxChannel16Bit(DmxChannel):
    _CHANNEL_SIZE: int = 2                          # Channel size in byte
    _CHANNEL_MAX: int = 256 ** _CHANNEL_SIZE - 1    # Max value of the channel


class DmxChannel24Bit(DmxChannel):
    _CHANNEL_SIZE: int = 3                          # Channel size in byte
    _CHANNEL_MAX: int = 256 ** _CHANNEL_SIZE - 1    # Max value of the channel


class DmxChannel32Bit(DmxChannel):
    _CHANNEL_SIZE: int = 4                          # Channel size in byte
    _CHANNEL_MAX: int = 256 ** _CHANNEL_SIZE - 1    # Max value of the channel

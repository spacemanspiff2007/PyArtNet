import asyncio
import logging
import math
import typing

import pyartnet


log = logging.getLogger('pyartnet.DmxChannel')


class DmxChannel:
    _CHANNEL_SIZE: int = 1   # Channel size in byte

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

        self.__val_act_i = [0 for _ in range(self.width)]

        self.__fades: typing.List[typing.Optional[pyartnet.fades.FadeBase]] = [None for k in range(self.width)]
        self.__fade_running = False

        self.__step_max = 0
        self.__step_is = 0

        assert isinstance(universe, pyartnet.DmxUniverse)
        self.__universe: pyartnet.DmxUniverse = universe

        # Output correction function
        self.output_correction = None

        # Callbacks
        self.callback_value_changed: typing.Optional[typing.Callable[[DmxChannel], typing.Any]] = None
        self.callback_fade_finished: typing.Optional[typing.Callable[[DmxChannel], typing.Any]] = None

    def __apply_output_correction(self, channel_val):
        if self.output_correction is not None:
            return self.output_correction(channel_val, 255 ** self._CHANNEL_SIZE)

        if self.__universe.output_correction is not None:
            return self.__universe.output_correction(channel_val, 255 ** self._CHANNEL_SIZE)

        return channel_val

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel_values(self) -> typing.List[int]:
        return self.__val_act_i.copy()

    def get_bytes(self) -> typing.Iterable:
        for obj in self.__val_act_i:
            if self._CHANNEL_SIZE == 1:
                yield obj
            else:
                for i in range(self._CHANNEL_SIZE, 0, -1):
                    val = (obj >> 8 * (i - 1)) & 0xFF
                    yield val

    def add_fade(self, fade_list: typing.List[int], duration_ms: int, fade_class=pyartnet.fades.LinearFade):
        fade_list = fade_list[:]
        assert isinstance(fade_list, list)
        assert len(fade_list) == self.width, f'Not enough fade values specified, expected {self.width}!'
        for i in range(self.width):
            k = fade_list[i]

            # we conveniently convert them to the face-class
            if isinstance(k, int) and fade_class is not None:
                fade_list[i] = k = fade_class(k)

            assert isinstance(k, pyartnet.fades.FadeBase), type(k)
            assert isinstance(k.val_target, int)
            assert 0 <= k.val_target <= (256 ** self._CHANNEL_SIZE) - 1

        # calculate how much steps we will be having
        step_time_ms = self.__universe._artnet_node.sleep_time * 1000
        duration_ms = max(duration_ms, step_time_ms)
        self.__step_max = math.ceil(duration_ms / step_time_ms)
        self.__step_is = 0

        # calculate required values
        for i, fade in enumerate(fade_list):  # type: int, pyartnet.fades.FadeBase
            fade.val_start = self.__val_act_i[i]
            fade.val_current = fade.val_start
            fade.initialize_fade(self.__step_max)
            self.__fades[i] = fade

        if log.isEnabledFor(logging.DEBUG):
            log._log(logging.DEBUG, f'Fade with {self.__step_max} steps:', [])
            for i in range(self.width):
                log._log(logging.DEBUG, 'CH {}: {:03d} -> {:03d} | {}'.format(
                    self.start + i, self.__val_act_i[i], self.__fades[i].val_target, self.__fades[i].debug_initialize()
                ), [])

        self.__fade_running = True
        return None

    async def wait_till_fade_complete(self):
        while self.__fade_running:
            await asyncio.sleep(self.__universe._artnet_node.sleep_time)

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
            self.__val_act_i[i] = round(self.__apply_output_correction(fade.val_current))

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
    _CHANNEL_SIZE: int = 2   # Channel size in byte


class DmxChannel24Bit(DmxChannel):
    _CHANNEL_SIZE: int = 3   # Channel size in byte


class DmxChannel32Bit(DmxChannel):
    _CHANNEL_SIZE: int = 4   # Channel size in byte

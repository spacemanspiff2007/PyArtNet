import asyncio
import logging
import math
import typing

import pyartnet

log = logging.getLogger('pyartnet.DmxChannel')


class DmxChannel:
    def __init__(self, universe, start: int, width: int):
        assert 1 <= start <= 512
        assert width > 0
        assert start + width - 1 <= 512

        self.start = start
        self.width = width

        self.__val_act_i = [0 for k in range(width)]

        self.__fades: typing.List[typing.Optional[pyartnet.fades.FadeBase]] = [None for k in range(width)]
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
            return self.output_correction(channel_val)

        if self.__universe.output_correction is not None:
            return self.__universe.output_correction(channel_val)

        return channel_val

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel_values(self) -> typing.List[int]:
        return self.__val_act_i.copy()

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
            assert 0 <= k.val_target <= 255

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

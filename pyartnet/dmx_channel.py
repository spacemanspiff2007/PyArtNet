import logging, asyncio, math

import pyartnet


log = logging.getLogger('PyArtnet.DmxChannel')


class DmxChannel:
    def __init__(self, universe, start : int, width : int):
        assert 1 <= start <= 512
        assert width > 0
        assert start + width <= 512

        self.start = start
        self.width = width

        self.__val_act_i = [0 for k in range(width)]

        self.__fades = [ None for k in range(width)]
        self.__fade_running = False

        self.__step_max = 0
        self.__step_is = 0

        assert isinstance(universe, pyartnet.DmxUniverse)
        self.__universe : pyartnet.DmxUniverse = universe

    @property
    def fade_running(self) -> bool:
        return self.__fade_running

    def get_channel_values(self) -> list:
        return self.__val_act_i

    def add_fade(self, fade_list : list, duration_ms, fade_class = None):
        fade_list = fade_list[:]
        assert isinstance(fade_list, list)
        assert len(fade_list) == self.width
        for i in range(self.width):
            k = fade_list[i]

            # we conveniently convert them to the face-class
            if isinstance(k, int) and fade_class is not None:
                fade_list[i] = fade_class(k)
                k = fade_list[i]

            assert isinstance(k, pyartnet.fades.FadeBase), type(k)
            assert isinstance(k.val_target, int)
            assert 0 <= k.val_target <= 255

        #calculate how much steps we will be having
        step_time_ms = self.__universe.artnet_node.sleep_time_ms * 1000
        duration_ms = max(duration_ms, step_time_ms)
        self.__step_max = math.ceil(duration_ms / step_time_ms)
        self.__step_is = 0

        #calculate required values
        for i, fade in enumerate(fade_list): # type: pyartnet.fades.FadeBase
            fade.val_start = self.__val_act_i[i]
            fade.val_current = fade.val_start
            fade.initialize_fade(self.__step_max)
            self.__fades[i] = fade

        if log.isEnabledFor(logging.DEBUG):
            log._log(logging.DEBUG, f'Fade with {self.__step_max} steps',[])
            for i in range(self.width):
                log._log(logging.DEBUG, 'CH {}: {:03d} -> {:03d} | {}'.format(
                    self.start + i, self.__val_act_i[i], self.__fades[i].val_target, self.__fades[i].debug_initialize()
                ), [])

        self.__fade_running = True
        return None

    async def wait_till_fade_complete(self):
        while self.__fade_running:
            await asyncio.sleep(self.__universe.artnet_node.sleep_time_ms)

    def cancel_fades(self):
        self.__fade_running = False

    def process(self):
        if not self.__fade_running:
            return False

        running = False
        for i, fade in enumerate(self.__fades):
            assert isinstance(fade, pyartnet.fades.FadeBase), type(fade)

            if fade.is_done():
                continue

            # get next value
            fade.calc_next_value()
            if isinstance(fade.val_current, float):
                self.__val_act_i[i] = int(round(fade.val_current, 0))
            else:
                assert isinstance(fade.val_current, int)
                self.__val_act_i[i] = fade.val_current

            running = True
        self.__fade_running = running

        # catch implementation errors
        if self.__step_is > self.__step_max:
            log.warning( f'Fades in Channel {self.start}:{self.width} did not finish! Aborting!')
            running = False
        self.__step_is += 1

        
        return self.__fade_running
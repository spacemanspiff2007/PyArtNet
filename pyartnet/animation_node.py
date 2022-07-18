import asyncio
import contextlib
import logging
import time
import typing
from traceback import format_exc

from .dmx_client import DmxClient
from .dmx_universe import DmxUniverse

log = logging.getLogger('pyartnet.AnimationNode')


class AnimationNode:
    def __init__(self, dmx_client: DmxClient, max_fps: int = 25, refresh_every: int = 2):
        """
        :param dmx_client: Client to use to send DMX frames
        :param max_fps: How many packets per sec shall max be send
        :param refresh_every: Resend the data every x seconds, 0 to deactivate
        """
        self.__dmxClient = dmx_client
        self.__universe = {}  # type: typing.Dict[int, DmxUniverse]
        self.__task = None

        # Maximum fps for DMX is 44fps, more makes no sense
        max_fps = max(1, min(max_fps, 44))
        self.sleep_time = 1 / max_fps

        self.refresh_every = refresh_every
        log.debug(f'Created AnimationNode: {max_fps}fps, {self.refresh_every}s refresh')

    def get_universe(self, nr: int) -> DmxUniverse:
        assert isinstance(nr, int), type(nr)
        assert nr >= 0, nr
        return self.__universe[nr]

    def add_universe(self, nr: int = 0) -> DmxUniverse:
        """Creates a new universe and adds it to the node"""
        assert isinstance(nr, int), type(nr)
        assert nr >= 0, nr

        self.__universe[nr] = u = DmxUniverse(self)
        return u

    async def __worker(self):
        log.debug('Worker started')
        last_update = time.time()

        while True:
            await asyncio.sleep(self.sleep_time)

            try:
                fades_running = False
                for u in self.__universe.values():
                    if u.process():
                        fades_running = True

                if fades_running:
                    self.update()
                    last_update = time.time()
                else:
                    if self.refresh_every > 0:
                        # refresh data all 2 secs
                        if time.time() - last_update > self.refresh_every:
                            self.update()
                            last_update = time.time()
                    else:
                        # Stop thread
                        self.__task = None
                        return None
            except Exception as e:
                log.error(f'Error in worker {e.__str__()}')
                for line in format_exc().splitlines():
                    log.error(line)

    async def start(self):
        if self.__task:
            return None
        self.__task = asyncio.create_task(self.__worker())

    async def stop(self):
        if not self.__task:
            return None

        self.__task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await self.__task

        self.__task = None
        log.debug('Worker stopped')
        return None

    def update(self):
        """Send an update to the dmx device. This normally happens automatically"""
        for universe_nr, universe in self.__universe.items():
            assert isinstance(universe_nr, int), type(universe_nr)
            assert isinstance(universe, DmxUniverse), type(universe)

            # don't send empty universes
            if universe.highest_channel <= 0:
                continue

            self.__dmxClient.update(universe_nr, universe)

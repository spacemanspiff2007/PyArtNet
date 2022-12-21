import logging
import socket
from asyncio import create_task, sleep, Task
from time import monotonic
from traceback import format_exc
from typing import Dict, Final, Generic, List, Optional, Tuple, TypeVar, Union

import pyartnet

from ..errors import DuplicateUniverseError, UniverseNotFoundError
from .output_correction import OutputCorrection

log = logging.getLogger('pyartnet.ArtNetNode')


CREATE_TASK = create_task   # easy way to add a different way to schedule tasks (e.g. thread safe)


TYPE_U = TypeVar('TYPE_U', bound='pyartnet.base.BaseUniverse')


# noinspection PyProtectedMember
class BaseNode(Generic[TYPE_U], OutputCorrection):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float] = 2,
                 source_address: Optional[Tuple[str, int]] = None):
        super().__init__()

        # Destination
        self._ip: Final = ip
        self._port: Final = port
        self._dst: Final = (self._ip, self._port)
        self._name: Final = f'{self._ip:s}:{self._port}'

        # socket setup
        self._socket: Final = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.setblocking(False)  # nonblocking for true asyncio

        # option to set source port/ip
        if source_address is not None:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(source_address)

        # refresh task
        self._refresh_every: float = max(0.1, refresh_every)
        self._refresh_task: Optional[Task] = None

        # fade task
        self._process_every: float = 1 / max(1, max_fps)
        self._process_task: Optional[Task] = None
        self._process_jobs: List['pyartnet.base.ChannelBoundFade'] = []

        # packet data
        self._packet_base: Union[bytearray, bytes] = bytearray()
        self._last_send: float = 0

        # containing universes
        self._universes: Tuple[TYPE_U, ...] = tuple()
        self._universe_map: Dict[int, TYPE_U] = {}

    def _apply_output_correction(self):
        for u in self._universes:
            u._apply_output_correction()

    def _send_universe(self, id: int, byte_size: int, values: bytearray, universe: TYPE_U):
        raise NotImplementedError()

    def _send_data(self, data: Union[bytearray, bytes]) -> int:

        ret = self._socket.sendto(self._packet_base + data, self._dst)

        self._last_send = monotonic()
        return ret

    def _start_process_task(self):
        if self._process_task is not None:
            return None
        self._process_task = CREATE_TASK(self._process_values_task(), name=f'Process task {self._name:s}')

    async def _process_values_task(self):
        log.debug(f'Started process task {self._name:s}')

        # wait a little, so we can schedule multiple tasks/updates, and they all start together
        await sleep(0.01)

        idle_ct = 0
        try:
            while idle_ct < 5:
                idle_ct += 1

                # process jobs
                to_remove = []
                for job in self._process_jobs:
                    job.process()
                    idle_ct = 0

                    if job.is_done:
                        to_remove.append(job)

                # send data of universe
                for universe in self._universes:
                    if not universe._data_changed:
                        continue
                    universe.send_data()
                    idle_ct = 0

                if to_remove:
                    for job in to_remove:
                        self._process_jobs.remove(job)
                        job.fade_complete()

                await sleep(self._process_every)
        except Exception:
            log.error(f'Error in worker for {self._name:s}:')
            for line in format_exc().splitlines():
                log.error(line)
        finally:
            self._process_task = None
            log.debug(f'Stopped process task {self._name:s}')

    async def start(self):
        if self._refresh_task:
            return False
        self._refresh_task = CREATE_TASK(self._periodic_refresh_task(), name=f'Refresh task {self._name:s}')
        return True

    async def stop(self):
        if self._refresh_task is None:
            return False

        self._refresh_task.cancel()
        # variable gets set to None in the task
        # That's why it's also necessary to await it
        await self._refresh_task
        return True

    async def _periodic_refresh_worker(self):
        while True:
            # sync the refresh messages
            next_refresh = monotonic()
            for u in self._universes:
                next_refresh = min(next_refresh, u._last_send)

            diff = monotonic() - next_refresh
            if diff < self._refresh_every:
                await sleep(diff)
                continue

            for u in self._universes:
                u.send_data()

    async def _periodic_refresh_task(self):
        log.debug(f'Started worker for {self._name:s}')
        try:
            while True:
                try:
                    await self._periodic_refresh_worker()
                except Exception:
                    log.error(f'Error in worker for {self._name:s}:')
                    for line in format_exc().splitlines():
                        log.error(line)
        finally:
            self._refresh_task = None
            log.debug(f'Stopped worker for {self._name:s}')

    def get_universe(self, nr: int) -> TYPE_U:
        if not isinstance(nr, int) or not nr >= 0:
            raise ValueError('BaseUniverse must be an int >= 0!')
        nr = int(nr)

        try:
            return self._universe_map[nr]
        except KeyError:
            raise UniverseNotFoundError(f'BaseUniverse {nr:d} not found!') from None

    def add_universe(self, nr: int = 0) -> TYPE_U:
        """Creates a new universe and adds it to the base"""
        if not isinstance(nr, int) or not nr >= 0:
            raise ValueError('BaseUniverse must be an int >= 0!')
        nr = int(nr)

        if nr in self._universe_map:
            raise DuplicateUniverseError(f'BaseUniverse {nr:d} does already exist!')

        # add to data
        self._universe_map[nr] = universe = self._create_universe(nr)
        self._universes = tuple(u for _, u in sorted(self._universe_map.items()))   # ascending

        return universe

    def _create_universe(self, nr: int) -> TYPE_U:
        raise NotImplementedError()

    def __getitem__(self, nr: int) -> TYPE_U:
        return self.get_universe(nr)

    def __len__(self):
        return len(self._universes)

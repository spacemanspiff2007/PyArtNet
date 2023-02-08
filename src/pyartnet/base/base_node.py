import logging
import socket
from asyncio import sleep
from time import monotonic
from typing import Dict, Final, Generic, List, Optional, Tuple, TypeVar, Union

import pyartnet

from ..errors import DuplicateUniverseError, UniverseNotFoundError
from .background_task import ExceptionIgnoringTask, SimpleBackgroundTask
from .output_correction import OutputCorrection

log = logging.getLogger('pyartnet.ArtNetNode')


TYPE_U = TypeVar('TYPE_U', bound='pyartnet.base.BaseUniverse')


# noinspection PyProtectedMember
class BaseNode(Generic[TYPE_U], OutputCorrection):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float, None] = 2, start_refresh_task: bool = True,
                 source_address: Optional[Tuple[str, int]] = None):
        super().__init__()

        # Destination
        self._ip: Final = ip
        self._port: Final = port
        self._dst: Final = (self._ip, self._port)

        # socket setup
        self._socket: Final = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.setblocking(False)  # nonblocking for true asyncio

        # option to set source port/ip
        if source_address is not None:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(source_address)

        # Name used for the Tasks (e.g. in error msg)
        name: Final = f'{self._ip:s}:{self._port}'

        # refresh task
        self._refresh_every: float = max(0.1, refresh_every)
        self._refresh_task: Final = ExceptionIgnoringTask(self._periodic_refresh_worker, f'Process task {name:s}')
        if start_refresh_task:
            self._refresh_task.start()

        # fade task
        self._process_every: float = 1 / max(1, max_fps)
        self._process_task: Final = SimpleBackgroundTask(self._process_values_task, f'Refresh task {name:s}')
        self._process_jobs: List['pyartnet.base.ChannelBoundFade'] = []

        # packet data
        self._packet_base: Union[bytearray, bytes] = bytearray()
        self._last_send: float = 0

        # containing universes
        self._universes: Tuple[TYPE_U, ...] = ()
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

    async def _process_values_task(self):
        # wait a little, so we can schedule multiple tasks/updates, and they all start together
        await sleep(0.01)

        idle_ct = 0
        while idle_ct < 10:
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

    def start_refresh(self):
        """Manually start the refresh task (if not already running)"""
        self._refresh_task.start()

    def stop_refresh(self):
        """Manually stop the refresh task"""
        self._refresh_task.cancel()

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

    def get_universe(self, nr: int) -> TYPE_U:
        """Get universe by number

        :param nr: universe nr
        :return: The universe
        """
        if not isinstance(nr, int) or not nr >= 0:
            raise ValueError('BaseUniverse must be an int >= 0!')
        nr = int(nr)

        try:
            return self._universe_map[nr]
        except KeyError:
            raise UniverseNotFoundError(f'BaseUniverse {nr:d} not found!') from None

    def add_universe(self, nr: int = 0) -> TYPE_U:
        """Creates a new universe and adds it to the parent node

        :param nr: universe nr
        :return: The universe
        """
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

    def __await__(self):
        while self._process_jobs:
            for job in self._process_jobs:
                yield from job.channel.__await__()

    def __getitem__(self, nr: int) -> TYPE_U:
        return self.get_universe(nr)

    def __len__(self):
        return len(self._universes)

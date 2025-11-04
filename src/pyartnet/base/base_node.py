from __future__ import annotations

from asyncio import sleep
from time import monotonic
from typing import TYPE_CHECKING, Final, Generic, TypeVar

from typing_extensions import Self

from pyartnet.base.background_task import ExceptionIgnoringTask, SimpleBackgroundTask
from pyartnet.base.output_correction import OutputCorrection
from pyartnet.errors import DuplicateUniverseError, UniverseNotFoundError


if TYPE_CHECKING:
    from socket import socket
    from types import TracebackType

    import pyartnet
    from pyartnet.base.network import MulticastNetworkTarget, UnicastNetworkTarget


UNIVERSE_TYPE = TypeVar('UNIVERSE_TYPE', bound='pyartnet.base.BaseUniverse')


# noinspection PyProtectedMember
class BaseNode(OutputCorrection, Generic[UNIVERSE_TYPE]):
    def __init__(self, network: UnicastNetworkTarget | MulticastNetworkTarget, *,
                 name: str | None = None,
                 max_fps: int = 25,
                 refresh_every: float = 2) -> None:
        super().__init__()

        self._network: Final = network
        self._socket: socket | None = None
        self._name: Final = name if name is not None else f'{self.__class__.__name__}-{id(self):x}'

        # refresh task
        self._refresh_every: float = max(0.1, refresh_every)
        self._refresh_task: Final = ExceptionIgnoringTask(self._periodic_refresh_worker, f'Refresh task {self._name:s}')

        # fade task
        self._process_every: float = 1 / max(1, max_fps)
        self._process_task: Final = SimpleBackgroundTask(self._process_values_task, f'Process task {self._name:s}')
        self._process_jobs: list[pyartnet.base.ChannelBoundFade] = []

        # packet data
        self._packet_base: bytearray | bytes = bytearray()

        # containing universes
        self._universes: tuple[UNIVERSE_TYPE, ...] = ()
        self._universe_map: dict[int, UNIVERSE_TYPE] = {}

    def __repr__(self) -> str:
        universe_str = '-' if not self._universes else ','.join(str(u._universe) for u in self._universes)
        network = str(self._network).replace('NetworkTarget', '')
        return (f'<{self.__class__.__name__:s} name={self._name:s} network={network!s} '
                f'universe{"s" if len(self._universes) != 1 else ""}={universe_str:s}>')

    @property
    def name(self) -> str:
        return self._name

    def _apply_output_correction(self) -> None:
        for u in self._universes:
            u._apply_output_correction()

    def _send_universe(self, id: int, byte_size: int, values: bytearray, universe: UNIVERSE_TYPE) -> None:
        raise NotImplementedError()

    def set_synchronous_mode(self, enabled: bool) -> Self:
        raise NotImplementedError()

    def _send_synchronization(self) -> None:
        pass

    def _send_data(self, data: bytearray | bytes, dst: tuple[str, int] | str | None = None) -> None:
        if (sock := self._socket) is None:
            msg = 'Socket closed! Did you forget to use "async with"?'
            raise RuntimeError(msg)

        sock.sendto(self._packet_base + data, dst)  #type: ignore[arg-type]
        return None

    async def _process_values_task(self) -> None:
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

            # send synchronization only if we actually sent something
            if not idle_ct:
                self._send_synchronization()

            await sleep(self._process_every)

    async def start_refresh(self) -> None:
        """Manually start the refresh task (if not already running)"""
        self._refresh_task.start()

    async def stop_refresh(self) -> None:
        """Manually stop the refresh task"""
        return await self._refresh_task.cancel_wait()

    async def _periodic_refresh_worker(self) -> None:
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

            self._send_synchronization()

    def get_universe(self, nr: int) -> UNIVERSE_TYPE:
        """Get universe by number

        :param nr: universe nr
        :return: The universe
        """
        nr = self._validate_universe_nr(nr)

        try:
            return self._universe_map[nr]
        except KeyError:
            msg = f'BaseUniverse {nr:d} not found!'
            raise UniverseNotFoundError(msg) from None

    def add_universe(self, nr: int = 0) -> UNIVERSE_TYPE:
        """Creates a new universe and adds it to the parent node

        :param nr: universe nr
        :return: The universe
        """
        nr = self._validate_universe_nr(nr)

        if nr in self._universe_map:
            msg = f'BaseUniverse {nr:d} does already exist!'
            raise DuplicateUniverseError(msg)

        # add to data
        self._universe_map[nr] = universe = self._create_universe(nr)
        self._universes = tuple(u for _, u in sorted(self._universe_map.items()))   # ascending

        return universe

    def _create_universe(self, nr: int) -> UNIVERSE_TYPE:
        raise NotImplementedError()

    def _validate_universe_nr(self, nr: int) -> int:
        raise NotImplementedError()

    def __await__(self):
        while self._process_jobs:
            for job in self._process_jobs:
                yield from job.channel.__await__()

    def __getitem__(self, nr: int) -> UNIVERSE_TYPE:
        return self.get_universe(nr)

    def __len__(self) -> int:
        return len(self._universes)

    async def __aenter__(self) -> Self:
        if self._socket is not None:
            return self

        await self._network.resolve_hostname()
        self._socket = self._network.create_socket()

        self._refresh_task.start()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None,
                  exc_tb: TracebackType | None) -> None:
        if (sock := self._socket) is not None:
            self.socket = None
            sock.close()

        await self._process_task.cancel_wait()
        await self._refresh_task.cancel_wait()
        return None

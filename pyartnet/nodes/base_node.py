import asyncio
import binascii
import contextlib
import logging
import socket
import struct
import time
from typing import Final, Union, Optional
from asyncio import Task
from traceback import format_exc

log = logging.getLogger('pyartnet.ArtNetNode')


class BaseNode:
    def __init__(self, host: str, port: int, max_fps: Union[int, float] = 25, refresh_every: Union[int, float] = 2):
        self._host: Final = host
        self._port: Final = port

        self._base_packet: bytearray = bytearray()
        self._socket: Final = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.setblocking(False)

        max_fps = max(1, min(max_fps, 100))
        self._send_sleep: float = 1 / max_fps
        self._send_refresh: float = max(1, refresh_every)
        self._send_task: Optional[Task] = None

        self.__universe = {}  # type: typing.Dict[int, DmxUniverse]

    def send_data(self):
        raise NotImplementedError()

    async def start(self):
        if self._send_task:
            return None
        self._send_task = asyncio.create_task(self._worker_task())

    async def stop(self):
        if self._send_task is None:
            return None
        self._send_task.cancel()
        await self._send_task

    async def _worker_logic(self):
        last_update = time.time()

        while True:
            await asyncio.sleep(self._send_sleep)

            fades_running = False
            for u in self.__universe.values():
                if u.process():
                    fades_running = True

            if fades_running:
                self.send_data()
                last_update = time.time()
            else:
                if self._send_refresh > 0:
                    # refresh data all 2 secs
                    if time.time() - last_update > self._send_refresh:
                        self.send_data()
                        last_update = time.time()

    async def _worker_task(self):
        log.debug(f'Started worker for {self._host:s}')
        try:
            while True:
                try:
                    await self._worker_logic()
                except Exception:
                    log.error(f'Error in worker for {self._host}:')
                    for line in format_exc().splitlines():
                        log.error(line)
        finally:
            self._send_task = None
            log.debug(f'Stopped worker for {self._host:s}')

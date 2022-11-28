import asyncio
import binascii
import contextlib
import logging
import socket
import struct
from time import monotonic
from typing import Final, Union, Optional, Protocol
from asyncio import Task, create_task, sleep
from traceback import format_exc


log = logging.getLogger('pyartnet.ArtNetNode')


class BaseNode:
    def __init__(self, ip: str, port: int,
                 refresh_every: Union[int, float] = 2, sequence_counter=True,
                 source_ip: Optional[str] = None, source_port: Optional[int] = None):
        super().__init__()

        self._ip: Final = ip
        self._port: Final = port

        # socket setup
        self._socket: Final = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        self._socket.setblocking(False)  # nonblocking for true asyncio

        # option to set source port/ip
        if source_ip is not None and source_port is not None:
            self._socket.bind((source_ip, source_port))

        # udp packet data
        self._packet_base: Union[bytearray, bytes] = bytearray()

        # refresh
        self._refresh_every: float = max(0.1, refresh_every)
        self._refresh_task: Optional[Task] = None
        self._last_send: float = 0

        self._sequence_ctr = 1 if sequence_counter else 0

    def prepare_data(self, values: bytearray):
        raise NotImplementedError()

    def send_data(self, data: Union[bytearray, bytes]) -> int:

        ret = self._socket.sendto(self._packet_base + data, (self._ip, self._port))

        self._last_send = monotonic()

        # sequence counter only when enabled
        if ctr := self._sequence_ctr:
            ctr += 1
            if ctr > 255:
                ctr = 1
            self._sequence_ctr = ctr

        return ret

    async def start(self):
        if self._refresh_task:
            return None
        self._refresh_task = create_task(self._periodic_refresh_task())

    async def stop(self):
        if self._refresh_task is None:
            return None
        # variable gets set to None in the task
        self._refresh_task.cancel()
        await self._refresh_task

    async def _periodic_refresh_worker(self):
        while True:
            diff = monotonic() - self._last_send
            if diff < self._refresh_every:
                await sleep(diff)
                continue

            self.prepare_data()

    async def _periodic_refresh_task(self):
        log.debug(f'Started worker for {self._ip:s}')
        try:
            while True:
                try:
                    await self._periodic_refresh_worker()
                except Exception:
                    log.error(f'Error in worker for {self._ip:s}:')
                    for line in format_exc().splitlines():
                        log.error(line)
        finally:
            self._refresh_task = None
            log.debug(f'Stopped worker for {self._ip:s}')

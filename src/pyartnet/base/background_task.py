from __future__ import annotations

import logging
from asyncio import CancelledError, Task, create_task, current_task, sleep
from contextlib import suppress
from time import monotonic
from traceback import format_exc
from typing import Any, Callable, Coroutine, Final


log = logging.getLogger('pyartnet.Task')


def log_exception(e: Exception, name: str) -> None:
    log.error(f'Error in worker for {name:s}:')
    for line in format_exc().splitlines():
        log.error(line)


_BACKGROUND_TASKS: set[Task] = set()

# use variables, so it's easy to e.g. implement thread safe scheduling
CREATE_TASK = create_task
EXCEPTION_HANDLER: Callable[[Exception, str], Any] = log_exception


class SimpleBackgroundTask:

    def __init__(self, coro: Callable[[], Coroutine], name: str) -> None:
        self.coro: Final = coro
        self.name: Final = name
        self.task: Task | None = None

    def start(self) -> None:
        if self.task is not None:
            return None

        self.task = task = CREATE_TASK(self.coro_wrap(), name=self.name)
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
        return None

    def cancel(self) -> None:
        if (task := self.task) is None:
            return None

        self.task = None
        task.cancel()
        return None

    async def cancel_wait(self) -> None:
        if (task := self.task) is None:
            return None

        self.task = None
        task.cancel()

        with suppress(CancelledError):
            await task
        return None

    async def coro_wrap(self) -> None:
        log.debug(f'Started {self.name}')
        task = self.task
        assert task is current_task()

        try:
            await self.coro()
        except Exception as e:
            EXCEPTION_HANDLER(e, self.name)
        finally:
            if self.task is task:
                self.task = None
            log.debug(f'Stopped {self.name}')


class ExceptionIgnoringTask(SimpleBackgroundTask):
    async def coro_wrap(self) -> None:
        log.debug(f'Started {self.name}')
        task = self.task
        assert task is current_task()

        wait = 0

        try:
            while True:
                await sleep(wait)
                start = monotonic()
                try:
                    await self.coro()
                except Exception as e:
                    EXCEPTION_HANDLER(e, self.name)

                    # simple sleep logic with an increasing timeout
                    time_to_exception = monotonic() - start
                    wait = max(2, wait * 2) if time_to_exception < 16 or time_to_exception < wait else 0

                    log.debug(f'Retry in {wait:d} seconds')
        finally:
            if self.task is task:
                self.task = None
            log.debug(f'Stopped {self.name}')

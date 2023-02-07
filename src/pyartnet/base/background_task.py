import logging
from asyncio import create_task, sleep, Task
from time import monotonic
from traceback import format_exc
from typing import Any, Callable, Coroutine, Final, Optional, Set

log = logging.getLogger('pyartnet.Task')


def log_exception(e: Exception, name: str):
    log.error(f'Error in worker for {name:s}:')
    for line in format_exc().splitlines():
        log.error(line)


_BACKGROUND_TASKS: Set[Task] = set()

# use variables, so it's easy to e.g. implement thread safe scheduling
CREATE_TASK = create_task
EXCEPTION_HANDLER: Callable[[Exception, str], Any] = log_exception


class SimpleBackgroundTask:

    def __init__(self, coro: Callable[[], Coroutine], name: str):
        self.coro: Final = coro
        self.name: Final = name
        self.task: Optional[Task] = None

    def start(self):
        if self.task is not None:
            return None

        self.task = task = CREATE_TASK(self.coro_wrap(), name=self.name)
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

    def cancel(self):
        if self.task is None:
            return None

        self.task.cancel()
        self.task = None

    async def coro_wrap(self):
        log.debug(f'Started {self.name}')
        task = self.task
        assert task is not None

        try:
            await self.coro()
        except Exception as e:
            EXCEPTION_HANDLER(e, self.name)
        finally:
            if self.task is task:
                self.task = None
            log.debug(f'Stopped {self.name}')


class ExceptionIgnoringTask(SimpleBackgroundTask):
    async def coro_wrap(self):
        log.debug(f'Started {self.name}')
        task = self.task
        assert task is not None

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
                    if time_to_exception < 16 or time_to_exception < wait:
                        wait = max(2, wait * 2)
                    else:
                        wait = 0

                    log.debug(f'Retry in {wait:d} seconds')
        finally:
            if self.task is task:
                self.task = None
            log.debug(f'Stopped {self.name}')

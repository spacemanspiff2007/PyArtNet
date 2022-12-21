import logging
from asyncio import sleep
from time import monotonic
from unittest.mock import Mock

import pytest

import pyartnet.node.base_node
from pyartnet.node import BaseNode

STEP_MS = 15


class TestingNode(BaseNode):
    def __init__(self, ip: str, port: int):
        super().__init__(ip, port, max_fps=1_000 // STEP_MS)
        self.data = []

    def _send_universe(self, universe: int, byte_values: int, values: bytearray):
        self.data.append(values.hex())

    async def sleep_steps(self, steps: int):
        # use sleep because await sleep might actually take longer
        for _ in range(steps):
            await sleep(self._process_every)

    async def wait_for_task_finish(self):
        start = monotonic()
        steps = 0
        while self._process_task is not None:
            steps += 1
            if monotonic() - start > 0.2 or steps > 10:
                raise AssertionError(f'Process task was not finished: {monotonic() - start:.5f}s {steps}Steps')
            await sleep(self._process_every)


@pytest.fixture
def node(monkeypatch):
    monkeypatch.setattr(pyartnet.node.base_node, 'socket', Mock())

    node = TestingNode('IP', 9999)
    yield node


@pytest.fixture
def universe(node: BaseNode):
    yield node.add_universe()


@pytest.fixture(autouse=True)
def ensure_no_errors(caplog):
    yield

    for rec in caplog.records:
        assert rec.levelno <= logging.WARNING, rec

    # for msg in caplog.messages:
    #     print(msg)

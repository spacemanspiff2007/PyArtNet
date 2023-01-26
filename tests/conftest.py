import logging
import socket
from asyncio import sleep
from typing import List
from unittest.mock import Mock

import pytest

import pyartnet.base.base_node
from pyartnet.base import BaseNode, BaseUniverse
from pyartnet.base.base_node import TYPE_U

STEP_MS = 15


class TestingNode(BaseNode):
    __test__ = False    # prevent this from being collected by pytest

    def __init__(self, ip: str, port: int):
        super().__init__(ip, port, max_fps=1_000 // STEP_MS, start_refresh_task=False)
        self.data = []

    def _send_universe(self, id: int, byte_size: int, values: bytearray, universe: 'pyartnet.base.BaseUniverse'):
        self.data.append(values.hex())

    async def sleep_steps(self, steps: int):
        # use sleep because await sleep might actually take longer
        for _ in range(steps):
            await sleep(self._process_every)

    async def wait_for_task_finish(self):
        await self

    def _create_universe(self, nr: int) -> TYPE_U:
        return BaseUniverse(self, nr)


@pytest.fixture(autouse=True)
def patched_socket(monkeypatch):
    m_socket_obj = Mock(['sendto', 'setblocking'], name='socket_obj')
    m_socket_obj.sendto = m_sendto = Mock(name='socket_obj.sendto')

    m = Mock(['socket', 'AF_INET', 'SOCK_DGRAM'], name='Mock socket package')
    m.socket = Mock([], return_value=m_socket_obj, name='Mock socket obj')
    m.AF_INET = socket.AF_INET
    m.SOCK_DGRAM = socket.AF_INET

    monkeypatch.setattr(pyartnet.base.base_node, 'socket', m)

    yield m_sendto


def test_patched_socket(patched_socket):
    node = TestingNode('IP', 9999)
    assert node._socket.sendto is patched_socket


@pytest.fixture
def node():
    node = TestingNode('IP', 9999)
    yield node


@pytest.fixture
def universe(node: BaseNode):
    yield node.add_universe()


@pytest.fixture(autouse=True)
def ensure_no_errors(caplog):
    caplog.set_level(logging.DEBUG)

    yield None

    log_records: List[logging.LogRecord] = []
    name_indent = 0
    level_indent = 0

    for when in ('setup', 'call', 'teardown'):
        records = caplog.get_records(when)
        if any(map(lambda x: x.levelno >= logging.WARNING, records)):
            for rec in records:
                name_indent = max(name_indent, len(rec.name))
                level_indent = max(level_indent, len(rec.levelname))
            log_records.extend(records)

    if log_records:
        msgs = [
            f'[{rec.name:>{name_indent:d}s}] | {rec.levelname:{level_indent:d}s} | {rec.getMessage()}'
            for rec in log_records
        ]
        pytest.fail('Error in log:\n' + '\n'.join(msgs))

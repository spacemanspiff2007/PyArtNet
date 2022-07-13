import logging

import pytest

import pyartnet
from pyartnet import AnimationNode
from pyartnet.dmx_client import DmxClient


class DummySocket:
    def sendto(self, packet, dst):
        pass


class StubClient(DmxClient):
    def __init__(self, host: str = "", port: int = 0):
        super().__init__(host, port)
        self.values = []

    def update(self, universe_nr, universe):
        pass


class PatchedAnimationNode(AnimationNode):
    def __init__(self, host: str, port: int = 0x1936, max_fps: int = 25, refresh_every: int = 2,
                 sequence_counter: bool = True):
        super().__init__(StubClient(host, port), max_fps, refresh_every=0)
        self.sleep_time = 0.001

        self._socket = DummySocket()
        self.values = []

    def update(self):
        super().update()
        self.values.append([int(k) for k in self.get_universe(0).data])


@pytest.fixture
def artnet_node(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(pyartnet, 'AnimationNode', PatchedAnimationNode)

    yield PatchedAnimationNode('-')


@pytest.fixture
async def running_artnet_node(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(pyartnet, 'AnimationNode', PatchedAnimationNode)

    node = PatchedAnimationNode('-')
    await node.start()

    yield node

    await node.stop()

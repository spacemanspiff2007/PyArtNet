import logging

import pytest

import pyartnet
from pyartnet import ArtNetNode


class DummySocket:
    def sendto(self, packet, dst):
        pass


class PatchedArtNetNode(ArtNetNode):

    def __init__(self, host: str, port: int = 0x1936, max_fps: int = 25, refresh_every: int = 2,
                 sequence_counter: bool = True):
        super().__init__(host, port, max_fps, refresh_every=0, sequence_counter=sequence_counter)
        self.sleep_time = 0.001

        self._socket = DummySocket()
        self.values = []

    def update(self):
        super().update()
        self.values.append([int(k) for k in self.get_universe(0).data])


@pytest.fixture
def artnet_node(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(pyartnet, 'ArtNetNode', PatchedArtNetNode)

    yield PatchedArtNetNode('-')


@pytest.fixture
async def running_artnet_node(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(pyartnet, 'ArtNetNode', PatchedArtNetNode)

    node = PatchedArtNetNode('-')
    await node.start()

    yield node

    await node.stop()

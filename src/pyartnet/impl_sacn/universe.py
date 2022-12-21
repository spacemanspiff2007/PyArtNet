import pyartnet
from pyartnet.base import BaseUniverse


class SacnUniverse(BaseUniverse):

    def __init__(self, node: 'pyartnet.impl_sacn.SacnNode', universe: int = 0):
        super().__init__(node, universe)

        self._sequence_ctr = 1

    def send_data(self):
        super().send_data()

        # Sequence Counter only when enabled
        self._sequence_ctr += 1
        if self._sequence_ctr > 255:
            self._sequence_ctr = 0

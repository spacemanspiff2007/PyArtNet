from typing import Final

import pyartnet
from pyartnet.base import BaseUniverse
from pyartnet.base.seq_counter import SequenceCounter


class SacnUniverse(BaseUniverse):

    def __init__(self, node: 'pyartnet.impl_sacn.SacnNode', universe: int = 0):
        super().__init__(node, universe)

        # sACN has the sequence counter on the universe
        self._sequence_ctr: Final = SequenceCounter()

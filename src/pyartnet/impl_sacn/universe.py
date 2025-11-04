from typing import TYPE_CHECKING, Final

from pyartnet.base import BaseUniverse
from pyartnet.base.seq_counter import SequenceCounter


if TYPE_CHECKING:
    import pyartnet


class SacnUniverse(BaseUniverse):

    def __init__(self, node: 'pyartnet.impl_sacn.SacnNode', universe: int = 0) -> None:
        super().__init__(node, universe)

        # sACN has the sequence counter on the universe
        self._sequence_ctr: Final = SequenceCounter()

        # to support multicast
        self._dst: tuple[str, int] = node._get_universe_ip_port(universe)

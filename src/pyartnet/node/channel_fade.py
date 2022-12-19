import logging
from typing import Iterable, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import pyartnet


log = logging.getLogger('pyartnet.DmxChannel')


class ChannelBoundFade:
    def __init__(self, channel: 'pyartnet.node.Channel', fades: Iterable['pyartnet.fades.FadeBase']):
        super().__init__()
        self.channel: 'pyartnet.node.Channel' = channel

        self.fades: Tuple['pyartnet.fades.FadeBase', ...] = tuple(fades)
        self.values: List[float] = [f.val_current for f in fades]

        self.is_done = False

    def process(self):
        finished = True
        for i, fade in enumerate(self.fades):
            if fade.is_done:
                continue

            self.values[i] = fade.calc_next_value()

            if not fade.is_done:
                finished = False

        self.is_done = finished
        self.channel.set_values(self.values)

    # noinspection PyProtectedMember
    def remove(self):
        node = self.channel._parent_node

        # remove from channel
        self.channel._current_fade = None
        self.channel = None

        # remove from node
        node._process_jobs.remove(self)

    def fade_complete(self):
        c = self.channel

        # remove from channel
        self.channel._current_fade = None
        self.channel = None

        if c.callback_fade_finished is not None:
            c.callback_fade_finished(c)

import logging
from asyncio import Event
from typing import Final, Iterable, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    import pyartnet


log = logging.getLogger('pyartnet.DmxChannel')


# noinspection PyProtectedMember
class ChannelBoundFade:
    def __init__(self, channel: 'pyartnet.base.Channel', fades: Iterable['pyartnet.fades.FadeBase']):
        super().__init__()
        self.channel: 'pyartnet.base.Channel' = channel

        self.fades: Tuple['pyartnet.fades.FadeBase', ...] = tuple(fades)
        self.values: List[float] = [0 for _ in fades]

        self.is_done = False
        self.event: Final = Event()

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

    def cancel(self):
        # remove fade from channel
        c = self.channel
        self.channel = None  # type: ignore[assignment]
        c._current_fade = None

        self.event.set()

        # remove from parent node
        c._parent_node._process_jobs.remove(self)

    def fade_complete(self):
        # remove fade from channel
        c = self.channel
        self.channel = None  # type: ignore[assignment]
        c._current_fade = None

        self.event.set()

        if c.callback_fade_finished is not None:
            c.callback_fade_finished(c)

    def __repr__(self):
        # Channel part
        if self.channel is not None:
            channel_part = f'channel={self.channel._start:d}/{self.channel._width:d}'
        else:
            channel_part = 'channel=None'

        return f'<{self.__class__.__name__:s} {channel_part}, is_done={self.is_done}>'

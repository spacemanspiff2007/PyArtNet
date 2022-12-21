from typing import Final


class SequenceCounter:
    __slots__ = ('_ctr', '_start', '_upper')

    def __init__(self, start: int = 0, upper: int = 255):
        self._ctr: int = start
        assert start <= upper
        self._start: Final = start
        self._upper: Final = upper

    @property
    def value(self) -> int:
        ret = self._ctr
        self._ctr += 1
        if self._ctr > self._upper:
            self._ctr = self._start
        return ret

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self._ctr:d}>'

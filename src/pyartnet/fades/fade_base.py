import abc


class FadeBase(metaclass=abc.ABCMeta):

    def __init__(self, start: int, target: int):
        self.val_target  : int = int(target)              # Target Value
        self.val_start   : int = start                    # Start Value
        self.val_current : float = float(self.val_start)  # Current Value

        self.is_done = False

    @abc.abstractmethod
    def initialize(self, steps : int):
        raise NotImplementedError()

    def debug_initialize(self) -> str:
        """return debug string of the calculated values in initialize fade"""
        return ""

    @abc.abstractmethod
    def calc_next_value(self) -> float:
        raise NotImplementedError()

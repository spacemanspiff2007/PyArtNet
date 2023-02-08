import abc


class FadeBase(metaclass=abc.ABCMeta):

    def __init__(self, target: int):
        self.val_target  : int = int(target)  # Target Value
        self.val_start   : int = 0            # Start Value
        self.val_current : float = 0.0        # Current Value

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

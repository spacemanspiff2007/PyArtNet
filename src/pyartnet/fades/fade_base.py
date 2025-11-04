
class FadeBase:

    def __init__(self) -> None:
        self.is_done = False

    def initialize(self, current: int, target: int, steps: int) -> None:
        raise NotImplementedError()

    def debug_initialize(self) -> str:
        """return debug string of the calculated values in initialize fade"""
        return ''

    def calc_next_value(self) -> float:
        raise NotImplementedError()

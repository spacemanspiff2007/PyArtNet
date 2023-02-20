from .fade_base import FadeBase


class LinearFade(FadeBase):

    def __init__(self):
        super().__init__()
        self.target: int = 0            # Target Value
        self.current: float = 0.0       # Current Value
        self.factor: float = 1.0

    def debug_initialize(self) -> str:
        return f"{self.current:03.0f} -> {self.target:03d} | step: {self.factor:+5.1f}"

    def initialize(self, start: int, target: int, steps: int):
        self.current = start
        self.target = target
        self.factor = (self.target - start) / steps

    def calc_next_value(self) -> float:
        self.current += self.factor

        # is_done status
        curr = round(self.current)
        if self.factor <= 0:
            if curr <= self.target:
                self.is_done = True
        else:
            if curr >= self.target:
                self.is_done = True

        return self.current

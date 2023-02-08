from .fade_base import FadeBase


class LinearFade(FadeBase):

    def __init__(self, target: int):
        super().__init__(target)
        self.factor: float = 1.0

    def debug_initialize(self) -> str:
        return f"step: {self.factor:+5.1f}"

    def initialize(self, steps: int):
        self.factor = (self.val_target - self.val_start) / steps

    def calc_next_value(self) -> float:
        self.val_current += self.factor

        # is_done status
        curr = round(self.val_current)
        if self.factor <= 0:
            if curr <= self.val_target:
                self.is_done = True
        else:
            if curr >= self.val_target:
                self.is_done = True

        return curr

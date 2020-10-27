from .fade_base import FadeBase


class LinearFade(FadeBase):

    def __init__(self, target: int):
        super().__init__(target)
        self.factor = 1

    def debug_initialize(self) -> str:
        return f"step: {self.factor:+5.1f}"

    def initialize_fade(self, steps: int):
        self.factor = (self.val_target - self.val_start) / steps

    def calc_next_value(self):
        self.val_current += self.factor

    def is_done(self) -> bool:
        curr = round(self.val_current)
        if self.factor <= 0 and curr <= self.val_target:
            return True
        if self.factor >= 0 and curr >= self.val_target:
            return True

        return False

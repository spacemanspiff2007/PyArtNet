from .fade_base import FadeBase

class FadeQuadratic(FadeBase):

    def __init__(self, target: int):
        super().__init__(target)

        self.a = 0
        self.step = 0
        self.step_factor = 0

    def initialize_fade(self, steps: int):

        self.step = 0
        self.a = abs(self.val_target - self.val_start) / (steps * steps)

        if self.val_target < self.val_start:
            self.step_factor = -1 * steps
        else:
            self.step_factor = 0

    def debug_initialize(self) -> str:
        return f'{self.a:.2f} (x{self.step_factor:+})**2'

    def calc_next_value(self):
        self.step += 1
        self.val_current = self.a * (self.step + self.step_factor) ** 2

    def is_done(self) -> bool:
        curr = int(round(self.val_current, 0))
        if self.step_factor < 0 and curr <= self.val_target:
            return True
        if self.step_factor >= 0 and curr >= self.val_target:
            return True

        return False
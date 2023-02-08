class Correction:
    def correct(self, val: float, max_val: int = 0xFF) -> float:
        raise NotImplementedError()

    def reverse_correct(self, val: float, max_val: int = 0xFF) -> float:
        raise NotImplementedError()


class Linear(Correction):

    def correct(self, val: float, max_val: int = 0xFF):
        return val

    def reverse_correct(self, val: float, max_val: int = 0xFF):
        return val


class Quadratic(Correction):

    def correct(self, val: float, max_val: int = 0xFF):
        return val ** 2 / max_val

    def reverse_correct(self, val: float, max_val: int = 0xFF):
        return val ** (1. / 2.) * max_val ** (1. / 2.)


class Cubic(Correction):

    def correct(self, val: float, max_val: int = 0xFF):
        return val ** 3 / max_val ** 2

    def reverse_correct(self, val: float, max_val: int = 0xFF):
        return val ** (1. / 3.) * max_val ** (2. / 3.)


class Quadruple(Correction):

    def correct(self, val: float, max_val: int = 0xFF):
        return val ** 4 / max_val ** 3

    def reverse_correct(self, val: float, max_val: int = 0xFF):
        return val ** (1. / 4.) * max_val ** (3. / 4.)

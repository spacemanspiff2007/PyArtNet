def linear(val: float, max_val: int = 0xFF):
    return val


def quadratic(val: float, max_val: int = 0xFF):
    return (val ** 2) / max_val


def cubic(val: float, max_val: int = 0xFF):
    return (val ** 3) / (max_val * max_val)


def quadruple(val: float, max_val: int = 0xFF):
    return (val ** 4) / (max_val * max_val * max_val)

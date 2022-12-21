def linear(val: float, max_val: int = 0xFF) -> float:
    return val


def quadratic(val: float, max_val: int = 0xFF) -> float:
    return (val ** 2) / max_val


def cubic(val: float, max_val: int = 0xFF) -> float:
    return (val ** 3) / (max_val ** 2)


def quadruple(val: float, max_val: int = 0xFF) -> float:
    return (val ** 4) / (max_val ** 3)

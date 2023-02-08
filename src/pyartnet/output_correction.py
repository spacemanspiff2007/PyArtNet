def linear(val: float, max_val: int = 0xFF) -> float:
    """linear output correction"""
    return val


def quadratic(val: float, max_val: int = 0xFF) -> float:
    """Quadratic output correction"""
    return (val ** 2) / max_val


def cubic(val: float, max_val: int = 0xFF) -> float:
    """Cubic output correction"""
    return (val ** 3) / (max_val ** 2)


def quadruple(val: float, max_val: int = 0xFF) -> float:
    """Quadruple output correction"""
    return (val ** 4) / (max_val ** 3)

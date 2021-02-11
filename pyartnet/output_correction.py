

def quadratic(val: float, max_val: int = 255):
    return (val ** 2) / max_val


def cubic(val: float, max_val: int = 255):
    return (val ** 3) / (max_val * max_val)


def quadruple(val: float, max_val: int = 255):
    return (val ** 4) / (max_val * max_val * max_val)

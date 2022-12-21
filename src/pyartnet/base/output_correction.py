from typing import Callable, Optional


class OutputCorrection:
    def __init__(self):
        super().__init__()
        self._correction_output: Optional[Callable[[float, int], float]] = None

    def set_output_correction(self, func: Optional[Callable[[float, int], float]]) -> None:
        """Set the output correction function.

        :param func: None to disable output correction or the function which will be used to transform the values
        """
        self._correction_output = func
        self._apply_output_correction()
        return None

    def _apply_output_correction(self) -> None:
        raise NotImplementedError()

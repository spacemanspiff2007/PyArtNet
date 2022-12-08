from typing import Callable, Optional
from typing_extensions import Self


class OutputCorrection:
    def __init__(self):
        self._correction_output: Optional[Callable[[float, int], float]] = None

    def set_output_correction(self, func: Optional[Callable[[float, int], float]]) -> Self:
        """Set the output correction function.

        :param func: None to disable output correction or the function which will be used to transform the values
        """
        self._correction_output = func
        self._apply_output_correction()
        return self

    def _apply_output_correction(self):
        raise NotImplementedError()

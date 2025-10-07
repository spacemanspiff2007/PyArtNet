from __future__ import annotations

from typing import Callable


class OutputCorrection:
    def __init__(self) -> None:
        super().__init__()
        self._correction_output: Callable[[float, int], float] | None = None

    def set_output_correction(self, func: Callable[[float, int], float] | None) -> None:
        """Set the output correction function.

        :param func: None to disable output correction or the function which will be used to transform the values
        """
        self._correction_output = func
        self._apply_output_correction()
        return None

    def _apply_output_correction(self) -> None:
        raise NotImplementedError()

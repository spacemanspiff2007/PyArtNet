import pytest

from pyartnet.output_correction import Quadratic, Quadruple, Cubic


@pytest.mark.parametrize('max_val', [
    pytest.param(k, id=f'{k:X}') for k in (0xFF, 0xFFFF, 0xFFFFFF, 0xFFFFFFFF, 0xFFFFFFFFFF)])
@pytest.mark.parametrize('corr', [Quadratic(), Quadruple(), Cubic()])
def test_correction(corr, max_val):
    assert corr.correct(0, max_val=max_val) == 0
    assert corr.correct(max_val, max_val=max_val) == max_val

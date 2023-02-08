import pytest

from pyartnet.output_correction import cubic, quadratic, quadruple


@pytest.mark.parametrize('max_val', [
    pytest.param(k, id=f'{k:X}') for k in (0xFF, 0xFFFF, 0xFFFFFF, 0xFFFFFFFF, 0xFFFFFFFFFF)])
@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_correction(corr, max_val):
    assert corr(0, max_val=max_val) == 0
    assert corr(max_val, max_val=max_val) == max_val

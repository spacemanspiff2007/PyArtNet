import pytest

from pyartnet.output_correction import quadratic, quadruple, cubic


@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_endpoints(corr):
    assert corr(0) == 0
    assert corr(255) == 255

    i = 0
    while i <= 255:
        assert 0 <= corr(i) <= 255
        i += 0.001

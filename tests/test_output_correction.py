import pytest

from pyartnet import DmxChannel, DmxChannel16Bit, DmxChannel24Bit, DmxChannel32Bit
from pyartnet.output_correction import cubic, quadratic, quadruple


@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_endpoints_8bit(corr):
    assert corr(0) == 0
    assert corr(0xFF, max_val=DmxChannel._CHANNEL_MAX) == 0xFF


@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_endpoints_16bit(corr):
    assert corr(0, max_val=DmxChannel16Bit._CHANNEL_MAX) == 0
    assert corr(0xFFFF, max_val=DmxChannel16Bit._CHANNEL_MAX) == 0xFFFF


@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_endpoints_24bit(corr):
    assert corr(0, max_val=DmxChannel16Bit._CHANNEL_MAX) == 0
    assert corr(0xFFFFFF, max_val=DmxChannel24Bit._CHANNEL_MAX) == 0xFFFFFF


@pytest.mark.parametrize('corr', [quadratic, quadruple, cubic])
def test_endpoints_32bit(corr):
    assert corr(0, max_val=DmxChannel16Bit._CHANNEL_MAX) == 0
    assert corr(0xFFFFFFFF, max_val=DmxChannel32Bit._CHANNEL_MAX) == 0xFFFFFFFF

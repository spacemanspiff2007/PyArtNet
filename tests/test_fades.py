import pyartnet


def test_single_step():
    fade = pyartnet.fades.LinearFade(255)
    fade.factor = 255
    assert not fade.is_done()

    fade.calc_next_value()
    assert fade.is_done()

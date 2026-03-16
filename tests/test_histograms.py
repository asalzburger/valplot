import numpy as np
import pytest

from valplot.histograms import efficiency, hist1d, hist2d, profile


def test_hist1d_validates_shapes_and_integral():
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[3.0, 4.0], underflow=1.0, overflow=2.0)
    assert h.n_bins == 2
    assert h.integral() == pytest.approx(7.0)
    assert h.integral(include_flow=True) == pytest.approx(10.0)
    np.testing.assert_allclose(h.errors, np.sqrt([3.0, 4.0]))

    with pytest.raises(ValueError):
        hist1d(edges=[0.0, 1.0], counts=[1.0, 2.0])


def test_hist2d_shape_validation():
    h = hist2d(
        x_edges=[0.0, 1.0, 2.0],
        y_edges=[0.0, 1.0, 2.0, 3.0],
        counts=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
    )
    assert h.shape == (2, 3)
    assert h.integral() == pytest.approx(21.0)

    with pytest.raises(ValueError):
        hist2d(x_edges=[0.0, 1.0], y_edges=[0.0, 1.0], counts=[[1.0, 2.0]])


def test_profile_validation():
    p = profile(edges=[0.0, 1.0, 2.0], means=[0.5, 0.7], errors=[0.1, 0.2], entries=[10.0, 5.0])
    assert p.n_bins == 2

    with pytest.raises(ValueError):
        profile(edges=[0.0, 1.0, 2.0], means=[0.5, 0.7], errors=[0.1], entries=[10.0, 5.0])


def test_efficiency_computation():
    eff = efficiency(edges=[0.0, 1.0, 2.0], passed=[5.0, 0.0], total=[10.0, 0.0])
    np.testing.assert_allclose(eff.values, [0.5, 0.0])
    assert eff.errors[1] == pytest.approx(0.0)

    with pytest.raises(ValueError):
        efficiency(edges=[0.0, 1.0], passed=[2.0], total=[1.0])

import numpy as np
from pathlib import Path

import pytest

from valplot.io.root.histograms import (
    hist1d_from_tree,
    hist1d_from_uproot,
    hist2d_from_tree,
    hist2d_from_uproot,
    profile_from_tree,
    read_hist1d,
)
from valplot.histograms import efficiency, profile


TESTS_INPUT_ROOT = Path(__file__).parent / "data" / "tests_input.root"


class _FakeTH1:
    def __init__(self):
        self._counts = np.array([2.0, 3.0], dtype=float)
        self._edges = np.array([0.0, 1.0, 2.0], dtype=float)
        self._flow_counts = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
        self._variances = np.array([4.0, 9.0], dtype=float)

    def to_numpy(self, flow=False):
        if flow:
            return self._flow_counts, self._edges
        return self._counts, self._edges

    def variances(self, flow=False):
        return self._variances


class _FakeTH2:
    def __init__(self):
        self._counts = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=float)
        self._x_edges = np.array([0.0, 1.0, 2.0], dtype=float)
        self._y_edges = np.array([0.0, 5.0, 10.0], dtype=float)
        self._variances = np.array([[1.0, 4.0], [9.0, 16.0]], dtype=float)
        self._flow = np.zeros((4, 4), dtype=float)
        self._flow[0, :] = 1.0
        self._flow[:, 0] += 2.0

    def to_numpy(self, flow=False):
        if flow:
            return self._flow, self._x_edges, self._y_edges
        return self._counts, self._x_edges, self._y_edges

    def variances(self, flow=False):
        return self._variances


def test_hist1d_from_uproot():
    h = hist1d_from_uproot(_FakeTH1(), name="h")
    np.testing.assert_allclose(h.counts, [2.0, 3.0])
    np.testing.assert_allclose(h.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(h.errors, [2.0, 3.0])
    assert h.underflow == 1.0
    assert h.overflow == 4.0


def test_hist2d_from_uproot():
    h = hist2d_from_uproot(_FakeTH2(), name="h2")
    np.testing.assert_allclose(h.counts, [[1.0, 2.0], [3.0, 4.0]])
    np.testing.assert_allclose(h.errors, [[1.0, 2.0], [3.0, 4.0]])
    assert h.shape == (2, 2)


class _FakeTree:
    def __init__(self, arrays):
        self._arrays = arrays

    def arrays(self, names, library="np"):
        assert library == "np"
        return {name: self._arrays[name] for name in names}


class _FakeRootFile:
    def __init__(self, objects):
        self._objects = objects

    def __getitem__(self, item):
        return self._objects[item]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_hist1d_from_tree_with_weights(monkeypatch):
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "w": np.array([1.0, 2.0, 3.0, 4.0], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    h = hist1d_from_tree("input.root", "events", "x", bins=2, range=(0.0, 2.0), weight_branch="w")
    np.testing.assert_allclose(h.counts, [3.0, 7.0])
    np.testing.assert_allclose(h.errors, [np.sqrt(5.0), 5.0])


def test_hist2d_from_tree(monkeypatch):
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "y": np.array([0.5, 1.5, 0.5, 1.5], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    h = hist2d_from_tree(
        "input.root",
        "events",
        "x",
        "y",
        bins=(2, 2),
        range=((0.0, 2.0), (0.0, 2.0)),
    )
    np.testing.assert_allclose(h.counts, [[1.0, 1.0], [1.0, 1.0]])


def test_read_hist1d(monkeypatch):
    fake_file = _FakeRootFile({"h1": _FakeTH1()})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)
    h = read_hist1d("input.root", "h1")
    np.testing.assert_allclose(h.counts, [2.0, 3.0])


def test_profile_from_tree(monkeypatch):
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "y": np.array([1.0, 3.0, 2.0, 6.0], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    p = profile_from_tree("input.root", "events", "x", "y", bins=2, range=(0.0, 2.0))
    np.testing.assert_allclose(p.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(p.means, [2.0, 4.0])
    np.testing.assert_allclose(p.entries, [2.0, 2.0])
    np.testing.assert_allclose(p.errors, [np.sqrt(0.5), np.sqrt(2.0)])


def test_profile_from_tree_with_weights(monkeypatch):
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "y": np.array([1.0, 3.0, 2.0, 6.0], dtype=float),
        "w": np.array([1.0, 2.0, 3.0, 4.0], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    p = profile_from_tree("input.root", "events", "x", "y", bins=2, range=(0.0, 2.0), weight_branch="w")
    np.testing.assert_allclose(p.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(p.means, [7.0 / 3.0, 30.0 / 7.0])
    np.testing.assert_allclose(p.entries, [3.0, 7.0])


def test_real_root_file_conversions():
    uproot = pytest.importorskip("uproot")
    assert TESTS_INPUT_ROOT.exists()

    with uproot.open(TESTS_INPUT_ROOT) as root_file:
        hx = hist1d_from_uproot(root_file["hx"], name="hx")
        hy = hist1d_from_uproot(root_file["hy"], name="hy")
        hxy = hist2d_from_uproot(root_file["hxy"], name="hxy")
        h_pass = hist1d_from_uproot(root_file["h_pass"], name="h_pass")

        prof_x_obj = root_file["profX"]
        prof_x = profile(
            edges=np.asarray(prof_x_obj.axis().edges(flow=False), dtype=float),
            means=np.asarray(prof_x_obj.values(flow=False), dtype=float),
            errors=np.asarray(prof_x_obj.errors(flow=False), dtype=float),
            entries=np.asarray(prof_x_obj.counts(flow=False), dtype=float),
            name="profX",
        )

        prof_y_obj = root_file["profY"]
        prof_y = profile(
            edges=np.asarray(prof_y_obj.axis().edges(flow=False), dtype=float),
            means=np.asarray(prof_y_obj.values(flow=False), dtype=float),
            errors=np.asarray(prof_y_obj.errors(flow=False), dtype=float),
            entries=np.asarray(prof_y_obj.counts(flow=False), dtype=float),
            name="profY",
        )

        eff_x = efficiency(edges=hx.edges, passed=h_pass.counts, total=hx.counts, name="eff_x")

        # Try reading TEfficiency directly when supported by the uproot version.
        # Some versions cannot deserialize the object payload in this test file.
        try:
            teff_obj = root_file["eff_x"]
            assert teff_obj.classname == "TEfficiency"
        except NotImplementedError:
            teff_obj = None

    assert hx.n_bins > 0
    assert hy.n_bins > 0
    assert hxy.shape[0] > 0 and hxy.shape[1] > 0
    assert prof_x.n_bins > 0
    assert prof_y.n_bins > 0
    assert eff_x.n_bins == hx.n_bins
    np.testing.assert_array_less(eff_x.passed - eff_x.total, np.zeros_like(eff_x.passed) + 1e-12)


def test_profile_from_tree_real_root_file():
    pytest.importorskip("uproot")
    assert TESTS_INPUT_ROOT.exists()

    p = profile_from_tree(
        str(TESTS_INPUT_ROOT),
        "tree",
        "x",
        "y",
        bins=50,
        range=(-5.0, 5.0),
        name="profX_from_tree",
    )
    assert p.n_bins == 50
    assert p.name == "profX_from_tree"

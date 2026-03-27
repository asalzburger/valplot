import numpy as np
from pathlib import Path

import pytest

from valplot.io.root.histograms import (
    band_from_tree,
    efficiency_from_tefficiency_root,
    efficiency_from_tefficiency_uproot,
    hist1d_from_tefficiency_root,
    hist1d_from_tefficiency_uproot,
    restricted_band_from_tree,
    hist1d_from_tree,
    hist1d_from_uproot,
    hist2d_from_tree,
    hist2d_from_uproot,
    profile_from_tree,
    read_hist1d,
    read_tefficiency,
    restricted_profile_from_tree,
    scatter_from_tree,
)
from valplot.histograms import efficiency, profile, restricted_profile


TESTS_INPUT_ROOT = Path(__file__).parent / "data" / "tests_input.root"
TESTS_RESTRICTED_ROOT = Path(__file__).parent / "data" / "tests_restricted.root"
TESTS_EFF_ROOT = Path(__file__).parent / "data" / "tests_efficiency.root"


class _FakeTH1Axis:
    def __init__(self, edges: np.ndarray):
        self._edges = edges

    def edges(self, flow=False):
        return self._edges


class _FakeTH1:
    def __init__(self):
        self._counts = np.array([2.0, 3.0], dtype=float)
        self._edges = np.array([0.0, 1.0, 2.0], dtype=float)
        self._flow_counts = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
        self._variances = np.array([4.0, 9.0], dtype=float)

    def axis(self):
        return _FakeTH1Axis(self._edges)

    def values(self, flow=False):
        if flow:
            return self._flow_counts
        return self._counts

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


class _FakeTEff:
    classname = "TEfficiency"

    def __init__(self):
        self._passed = _FakeTH1()
        self._total = _FakeTH1()
        self._total._counts = np.array([4.0, 6.0], dtype=float)
        self._total._variances = np.array([4.0, 6.0], dtype=float)

    def member(self, key):
        if key == "fPassedHistogram":
            return self._passed
        if key == "fTotalHistogram":
            return self._total
        raise KeyError(key)


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


def test_hist1d_from_tefficiency_uproot():
    h = hist1d_from_tefficiency_uproot(_FakeTEff(), name="eff")
    np.testing.assert_allclose(h.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(h.counts, [0.5, 0.5])
    assert np.all(h.errors > 0.0)


def test_efficiency_from_tefficiency_uproot():
    eff = efficiency_from_tefficiency_uproot(_FakeTEff(), name="eff")
    np.testing.assert_allclose(eff.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(eff.passed, [2.0, 3.0])
    np.testing.assert_allclose(eff.total, [4.0, 6.0])
    np.testing.assert_allclose(eff.values, [0.5, 0.5])
    assert np.all(eff.errors > 0.0)


def test_read_tefficiency(monkeypatch):
    fake_file = _FakeRootFile({"e1": _FakeTEff()})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)
    eff = read_tefficiency("input.root", "e1")
    np.testing.assert_allclose(eff.passed, [2.0, 3.0])
    np.testing.assert_allclose(eff.total, [4.0, 6.0])


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


def test_scatter_from_tree(monkeypatch):
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

    s = scatter_from_tree("input.root", "events", "x", "y")
    np.testing.assert_allclose(s.x, arrays["x"])
    np.testing.assert_allclose(s.y, arrays["y"])


def test_band_from_tree(monkeypatch):
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

    b = band_from_tree("input.root", "events", "x", "y", bins=2, range=(0.0, 2.0))
    np.testing.assert_allclose(b.edges, [0.0, 1.0, 2.0])
    np.testing.assert_allclose(b.values, [2.0, 4.0])
    np.testing.assert_allclose(b.lower, [1.0, 2.0])
    np.testing.assert_allclose(b.upper, [3.0, 6.0])


def test_restricted_band_from_tree(monkeypatch):
    # x, y, z. Restrict z in [0.5, 1.5] -> keep indices 0, 2, 3
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "y": np.array([1.0, 3.0, 2.0, 6.0], dtype=float),
        "z": np.array([0.5, 2.0, 1.0, 1.2], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    b = restricted_band_from_tree(
        "input.root",
        "events",
        x_branch="x",
        y_branch="y",
        restriction_branch="z",
        restriction_range=(0.5, 1.5),
        bins=2,
        range=(0.0, 2.0),
        name="b",
    )

    np.testing.assert_allclose(b.edges, [0.0, 1.0, 2.0])
    # After filter: x=[0.1, 1.2, 1.9], y=[1.0, 2.0, 6.0]
    # bin 0: y=[1.0] -> mean=1, min/max=1, error=0
    # bin 1: y=[2.0, 6.0] -> mean=4, min/max=2..6, error=sqrt(4)=2
    np.testing.assert_allclose(b.values, [1.0, 4.0])
    np.testing.assert_allclose(b.lower, [1.0, 2.0])
    np.testing.assert_allclose(b.upper, [1.0, 6.0])
    np.testing.assert_allclose(b.errors, [0.0, 2.0])


def test_restricted_profile_class():
    rp = restricted_profile(
        edges=[0.0, 1.0, 2.0],
        means=[2.0, 4.0],
        errors=[0.2, 0.3],
        entries=[10.0, 20.0],
        name="rp",
        metadata={"restriction_branch": "z", "restriction_range": (-4.0, 4.0)},
    )
    assert rp.n_bins == 2
    np.testing.assert_allclose(rp.means, [2.0, 4.0])
    assert rp.metadata["restriction_range"] == (-4.0, 4.0)


def test_restricted_profile_from_tree(monkeypatch):
    # x, y, z. Restrict z in [0.5, 1.5] -> keep indices 0, 2, 3
    arrays = {
        "x": np.array([0.1, 0.2, 1.2, 1.9], dtype=float),
        "y": np.array([1.0, 3.0, 2.0, 6.0], dtype=float),
        "z": np.array([0.5, 2.0, 1.0, 1.2], dtype=float),
    }
    fake_tree = _FakeTree(arrays)
    fake_file = _FakeRootFile({"events": fake_tree})

    class _FakeUproot:
        @staticmethod
        def open(_):
            return fake_file

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _FakeUproot)

    rp = restricted_profile_from_tree(
        "input.root",
        "events",
        x_branch="x",
        y_branch="y",
        restriction_branch="z",
        restriction_range=(0.5, 1.5),
        bins=2,
        range=(0.0, 2.0),
        name="rp",
    )
    np.testing.assert_allclose(rp.edges, [0.0, 1.0, 2.0])
    # After filter: x=[0.1, 1.2, 1.9], y=[1.0, 2.0, 6.0]
    # bin 0 [0,1]: x=0.1, y=1.0 -> mean=1, entries=1
    # bin 1 [1,2]: x=1.2, 1.9, y=2, 6 -> mean=4, entries=2
    np.testing.assert_allclose(rp.means, [1.0, 4.0])
    np.testing.assert_allclose(rp.entries, [1.0, 2.0])
    assert rp.metadata["restriction_branch"] == "z"
    assert rp.metadata["restriction_range"] == (0.5, 1.5)


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

        try:
            teff_obj = root_file["eff_x"]
            assert teff_obj.classname == "TEfficiency"
            eff_from_teff = efficiency_from_tefficiency_uproot(teff_obj, name="eff_x")
            assert eff_from_teff.n_bins == eff_x.n_bins
            np.testing.assert_allclose(eff_from_teff.passed, eff_x.passed, rtol=1e-5, atol=1e-8)
            np.testing.assert_allclose(eff_from_teff.total, eff_x.total, rtol=1e-5, atol=1e-8)
            np.testing.assert_allclose(eff_from_teff.edges, eff_x.edges, rtol=1e-5, atol=1e-8)
        except NotImplementedError:
            pass

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


def test_scatter_and_band_from_tree_real_root_file():
    pytest.importorskip("uproot")
    assert TESTS_INPUT_ROOT.exists()

    s = scatter_from_tree(str(TESTS_INPUT_ROOT), "tree", "x", "y", name="scatter_xy")
    b = band_from_tree(str(TESTS_INPUT_ROOT), "tree", "x", "y", bins=50, range=(-5.0, 5.0), name="band_xy")

    assert s.x.shape == s.y.shape
    assert s.name == "scatter_xy"
    assert b.values.shape[0] == 50
    assert b.name == "band_xy"


def test_restricted_profile_from_tree_real_root_file():
    pytest.importorskip("uproot")
    assert TESTS_RESTRICTED_ROOT.exists()

    rp = restricted_profile_from_tree(
        str(TESTS_RESTRICTED_ROOT),
        "restricted_profile",
        x_branch="x",
        y_branch="v0",
        restriction_branch="y",
        restriction_range=(-4.0, 4.0),
        bins=40,
        range=(-5.0, 5.0),
        name="v0_ycut",
    )
    assert rp.n_bins == 40
    assert rp.metadata["restriction_branch"] == "y"
    assert rp.metadata["restriction_range"] == (-4.0, 4.0)


def test_read_hist1d_tefficiency_real_root_file():
    pytest.importorskip("uproot")
    assert TESTS_EFF_ROOT.exists()
    try:
        h = read_hist1d(str(TESTS_EFF_ROOT), "efficiency")
    except NotImplementedError:
        pytest.skip("Current uproot cannot deserialize this TEfficiency streamer payload.")
    assert h.n_bins > 0
    assert np.all(h.counts >= 0.0)
    assert np.all(h.counts <= 1.0 + 1e-12)


def test_tefficiency_root_fallback_real_root_file():
    pytest.importorskip("ROOT")
    assert TESTS_EFF_ROOT.exists()

    eff = efficiency_from_tefficiency_root(str(TESTS_EFF_ROOT), "efficiency", name="eff_root")
    h = hist1d_from_tefficiency_root(str(TESTS_EFF_ROOT), "efficiency", name="eff_hist")

    assert eff.n_bins > 0
    assert h.n_bins == eff.n_bins
    np.testing.assert_allclose(h.edges, eff.edges)
    np.testing.assert_allclose(h.counts, eff.values)
    np.testing.assert_allclose(h.errors, eff.errors)


def test_read_tefficiency_fallback_when_uproot_streamer_unavailable(monkeypatch):
    pytest.importorskip("ROOT")
    assert TESTS_EFF_ROOT.exists()

    class _BrokenUproot:
        @staticmethod
        def open(_):
            raise NotImplementedError("Simulated unsupported TEfficiency streamer payload")

    monkeypatch.setattr("valplot.io.root.histograms._import_uproot", lambda: _BrokenUproot)

    eff = read_tefficiency(str(TESTS_EFF_ROOT), "efficiency")
    h = read_hist1d(str(TESTS_EFF_ROOT), "efficiency")

    assert eff.n_bins > 0
    assert h.n_bins == eff.n_bins
    np.testing.assert_allclose(h.edges, eff.edges)

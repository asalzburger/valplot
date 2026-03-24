import sys
import types

import pytest

from valplot.draw import Decoration, plot, plot_band, plot_ratio, plot_scatter
from valplot.histograms import band, hist1d, profile, restricted_profile, scatter


class _FakeAxis:
    def __init__(self):
        self.calls = []
        self.figure = None
        self._labels = []

    def stairs(self, counts, edges, **kwargs):
        self.calls.append(("stairs", counts, edges, kwargs))
        if kwargs.get("label"):
            self._labels.append(kwargs["label"])

    def pcolormesh(self, *args, **kwargs):
        self.calls.append(("pcolormesh", args, kwargs))
        return object()

    def errorbar(self, *args, **kwargs):
        self.calls.append(("errorbar", args, kwargs))
        if kwargs.get("label"):
            self._labels.append(kwargs["label"])

    def set_title(self, *args, **kwargs):
        self.calls.append(("set_title", args, kwargs))

    def set_xlabel(self, *args, **kwargs):
        self.calls.append(("set_xlabel", args, kwargs))

    def set_ylabel(self, *args, **kwargs):
        self.calls.append(("set_ylabel", args, kwargs))

    def tick_params(self, *args, **kwargs):
        self.calls.append(("tick_params", args, kwargs))

    def grid(self, *args, **kwargs):
        self.calls.append(("grid", args, kwargs))

    def get_legend_handles_labels(self):
        return [], self._labels

    def legend(self):
        self.calls.append(("legend", (), {}))

    def set_ylim(self, *args, **kwargs):
        self.calls.append(("set_ylim", args, kwargs))

    def axhline(self, *args, **kwargs):
        self.calls.append(("axhline", args, kwargs))

    def scatter(self, *args, **kwargs):
        self.calls.append(("scatter", args, kwargs))

    def fill_between(self, *args, **kwargs):
        self.calls.append(("fill_between", args, kwargs))

    def plot(self, *args, **kwargs):
        self.calls.append(("plot", args, kwargs))


class _FakeFigure:
    def __init__(self, axes):
        self._axes = axes
        for axis in axes:
            axis.figure = self
        self.colorbar_calls = []
        self.subplots_adjust_calls = []

    def gca(self):
        return self._axes[0]

    def colorbar(self, mesh, ax=None):
        self.colorbar_calls.append((mesh, ax))

    def subplots_adjust(self, **kwargs):
        self.subplots_adjust_calls.append(kwargs)


def _install_fake_matplotlib(monkeypatch):
    fake_pyplot = types.SimpleNamespace()
    ax = _FakeAxis()
    fig = _FakeFigure([ax])

    def _subplots(nrows=1, ncols=1, **_kwargs):
        if nrows == 2 and ncols == 1:
            top = _FakeAxis()
            bottom = _FakeAxis()
            ratio_fig = _FakeFigure([top, bottom])
            return ratio_fig, (top, bottom)
        return fig, ax

    fake_pyplot.subplots = _subplots
    monkeypatch.setitem(sys.modules, "matplotlib", types.ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_pyplot)


class _FakePlotlyFigure:
    def __init__(self):
        self.traces = []
        self.layout_updates = []

    def add_trace(self, trace, row=None, col=None):
        self.traces.append((trace, row, col))

    def update_layout(self, **kwargs):
        self.layout_updates.append(kwargs)


def _trace_factory(trace_type):
    def _ctor(**kwargs):
        return {"type": trace_type, **kwargs}

    return _ctor


def _install_fake_plotly(monkeypatch):
    fake_go = types.SimpleNamespace(
        Figure=_FakePlotlyFigure,
        Bar=_trace_factory("bar"),
        Heatmap=_trace_factory("heatmap"),
        Scatter=_trace_factory("scatter"),
    )
    monkeypatch.setitem(sys.modules, "plotly", types.ModuleType("plotly"))
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_go)


def test_plot_matplotlib_with_decoration(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")
    deco = Decoration(title="Title", x_label="X", y_label="Y", label="sample", show_grid=True)

    fig, ax = plot(h, decoration=deco, backend="matplotlib")
    assert fig is not None
    assert ax is not None
    assert any(call[0] == "stairs" for call in ax.calls)
    assert any(call[0] == "set_title" for call in ax.calls)
    assert any(call[0] == "set_xlabel" for call in ax.calls)
    assert any(call[0] == "set_ylabel" for call in ax.calls)
    assert any(call[0] == "grid" for call in ax.calls)
    assert any(call[0] == "legend" for call in ax.calls)


def test_plot_matplotlib_overlay_uses_existing_axis(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")

    _, ax = plot(h, backend="matplotlib")
    fig2, ax2 = plot(h, backend="matplotlib", axis=ax)
    assert ax2 is ax
    assert fig2 is ax.figure


def test_plot_plotly_subplot_support(monkeypatch):
    _install_fake_plotly(monkeypatch)
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")
    deco = Decoration(x_label="X", y_label="Y")

    fig = plot(h, decoration=deco, backend="plotly", row=1, col=2)
    assert len(fig.traces) == 1
    trace, row, col = fig.traces[0]
    assert trace["type"] == "bar"
    assert (row, col) == (1, 2)
    assert any("xaxis_title" in update for update in fig.layout_updates)


def test_plot_plotly_requires_row_and_col(monkeypatch):
    _install_fake_plotly(monkeypatch)
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")
    with pytest.raises(ValueError):
        plot(h, backend="plotly", row=1)


def test_plot_rejects_unknown_backend():
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")
    with pytest.raises(ValueError):
        plot(h, backend="unknown")


def test_plot_ratio_hist1d(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    h1 = hist1d(edges=[0.0, 1.0, 2.0], counts=[2.0, 4.0], name="h1")
    h2 = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 6.0], name="h2")
    deco1 = Decoration(title="Overlay+Ratio", x_label="x", y_label="Entries", label="num", show_grid=True)
    deco2 = Decoration(label="other", line_style="--")

    fig, (top_ax, ratio_ax) = plot_ratio([h1, h2], [deco1, deco2], backend="matplotlib")
    assert fig is not None
    assert fig.subplots_adjust_calls
    assert any(call[0] == "stairs" for call in top_ax.calls)
    assert not any(call[0] == "set_xlabel" for call in top_ax.calls)
    ratio_errorbars = [call for call in ratio_ax.calls if call[0] == "errorbar"]
    assert len(ratio_errorbars) == 1
    assert any(call[0] == "axhline" for call in ratio_ax.calls)
    assert any(call[0] == "set_ylabel" and call[1][0] == "Ratio" for call in ratio_ax.calls)
    assert any(call[0] == "set_xlabel" and call[1][0] == "x" for call in ratio_ax.calls)


def test_plot_ratio_profile(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    p1 = profile(edges=[0.0, 1.0, 2.0], means=[2.0, 4.0], errors=[0.2, 0.3], entries=[10.0, 20.0], name="p1")
    p2 = profile(edges=[0.0, 1.0, 2.0], means=[1.0, 8.0], errors=[0.1, 0.4], entries=[8.0, 22.0], name="p2")

    _, (top_ax, ratio_ax) = plot_ratio([p1, p2], [Decoration(label="p1"), Decoration(label="p2")], backend="matplotlib")
    assert any(call[0] == "errorbar" for call in top_ax.calls)
    ratio_errorbars = [call for call in ratio_ax.calls if call[0] == "errorbar"]
    assert len(ratio_errorbars) == 1


def test_plot_ratio_restricted_profile(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    rp1 = restricted_profile(
        edges=[0.0, 1.0, 2.0],
        means=[2.0, 4.0],
        errors=[0.2, 0.3],
        entries=[10.0, 20.0],
        name="rp1",
    )
    rp2 = restricted_profile(
        edges=[0.0, 1.0, 2.0],
        means=[1.0, 8.0],
        errors=[0.1, 0.4],
        entries=[8.0, 22.0],
        name="rp2",
    )

    _, (top_ax, ratio_ax) = plot_ratio(
        [rp1, rp2],
        [Decoration(label="rp1"), Decoration(label="rp2")],
        backend="matplotlib",
    )
    assert any(call[0] == "errorbar" for call in top_ax.calls)
    ratio_errorbars = [call for call in ratio_ax.calls if call[0] == "errorbar"]
    assert len(ratio_errorbars) == 1


def test_plot_ratio_mixed_profile_restricted_profile(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    p = profile(edges=[0.0, 1.0, 2.0], means=[2.0, 4.0], errors=[0.2, 0.3], entries=[10.0, 20.0], name="p")
    rp = restricted_profile(
        edges=[0.0, 1.0, 2.0],
        means=[1.0, 8.0],
        errors=[0.1, 0.4],
        entries=[8.0, 22.0],
        name="rp",
    )

    _, (top_ax, _) = plot_ratio(
        [p, rp],
        [Decoration(label="p"), Decoration(label="rp")],
        backend="matplotlib",
    )
    assert any(call[0] == "errorbar" for call in top_ax.calls)


def test_plot_ratio_rejects_mixed_types(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    h = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h")
    p = profile(edges=[0.0, 1.0, 2.0], means=[1.0, 2.0], errors=[0.1, 0.1], entries=[5.0, 5.0], name="p")

    with pytest.raises(TypeError):
        plot_ratio([h, p], [Decoration(), Decoration()], backend="matplotlib")


def test_plot_ratio_rejects_incompatible_edges(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    h1 = hist1d(edges=[0.0, 1.0, 2.0], counts=[1.0, 2.0], name="h1")
    h2 = hist1d(edges=[0.0, 2.0, 4.0], counts=[1.0, 2.0], name="h2")

    with pytest.raises(ValueError):
        plot_ratio([h1, h2], [Decoration(), Decoration()], backend="matplotlib")


def test_plot_scatter_matplotlib(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    pts = scatter(x=[0.0, 1.0, 2.0], y=[1.0, 1.5, 2.0], name="pts")

    _, ax = plot_scatter(pts, decoration=Decoration(label="points", marker="x"), backend="matplotlib")
    assert any(call[0] == "scatter" for call in ax.calls)


def test_plot_band_from_profile(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    p = profile(edges=[0.0, 1.0, 2.0], means=[2.0, 4.0], errors=[0.2, 0.3], entries=[10.0, 20.0], name="p")

    _, ax = plot_band([p], [Decoration(label="p", color="tab:blue")], backend="matplotlib")
    assert any(call[0] == "fill_between" for call in ax.calls)
    assert any(call[0] == "plot" for call in ax.calls)


def test_plot_band_from_band_spread(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    b = band(
        edges=[0.0, 1.0, 2.0],
        values=[2.0, 4.0],
        lower=[1.5, 3.0],
        upper=[2.5, 5.5],
        errors=[0.1, 0.2],
        name="b",
    )

    _, ax = plot_band([b], [Decoration(label="band", fill_color="tab:green")], spread="spread", backend="matplotlib")
    fill_calls = [call for call in ax.calls if call[0] == "fill_between"]
    assert fill_calls


def test_plot_band_from_restricted_profile(monkeypatch):
    _install_fake_matplotlib(monkeypatch)
    rp = restricted_profile(
        edges=[0.0, 1.0, 2.0],
        means=[2.0, 4.0],
        errors=[0.2, 0.3],
        entries=[10.0, 20.0],
        name="rp",
    )

    _, ax = plot_band(
        [rp],
        [Decoration(label="rp", color="tab:cyan", fill_color="tab:cyan")],
        spread="1sigma",
        backend="matplotlib",
    )
    assert any(call[0] == "fill_between" for call in ax.calls)
    assert any(call[0] == "plot" for call in ax.calls)

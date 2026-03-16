import sys
import types

import pytest

from valplot.draw import Decoration, plot
from valplot.histograms import hist1d


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


class _FakeFigure:
    def __init__(self, axis):
        self._axis = axis
        axis.figure = self
        self.colorbar_calls = []

    def gca(self):
        return self._axis

    def colorbar(self, mesh, ax=None):
        self.colorbar_calls.append((mesh, ax))


def _install_fake_matplotlib(monkeypatch):
    fake_pyplot = types.SimpleNamespace()
    ax = _FakeAxis()
    fig = _FakeFigure(ax)
    fake_pyplot.subplots = lambda: (fig, ax)
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

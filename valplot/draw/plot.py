"""Backend-agnostic plotting entry point for valplot histogram containers."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..histograms import efficiency, hist1d, hist2d, profile
from .decorations import Decoration


def plot(
    histogram: hist1d | hist2d | profile | efficiency,
    decoration: Decoration | None = None,
    *,
    backend: str = "matplotlib",
    figure: Any | None = None,
    axis: Any | None = None,
    row: int | None = None,
    col: int | None = None,
):
    """Plot a valplot histogram helper object into a selected backend."""
    deco = decoration or Decoration()
    if backend == "matplotlib":
        return _plot_matplotlib(histogram, deco, figure=figure, axis=axis)
    if backend == "plotly":
        return _plot_plotly(histogram, deco, figure=figure, row=row, col=col)
    raise ValueError(f"Unsupported backend={backend!r}. Expected 'matplotlib' or 'plotly'.")


def _plot_matplotlib(
    histogram: hist1d | hist2d | profile | efficiency,
    decoration: Decoration,
    *,
    figure: Any | None,
    axis: Any | None,
):
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise ImportError("matplotlib is required for backend='matplotlib'.") from exc

    if axis is not None:
        ax = axis
        fig = figure if figure is not None else getattr(axis, "figure", None)
    elif figure is not None:
        fig = figure
        ax = figure.gca()
    else:
        fig, ax = plt.subplots()

    if isinstance(histogram, hist1d):
        ax.stairs(
            histogram.counts,
            histogram.edges,
            label=decoration.label or histogram.name,
            color=decoration.color,
            alpha=decoration.alpha,
            linestyle=decoration.line_style,
            linewidth=decoration.line_width,
            fill=decoration.fill,
        )
    elif isinstance(histogram, hist2d):
        mesh = ax.pcolormesh(
            histogram.x_edges,
            histogram.y_edges,
            histogram.counts.T,
            cmap=decoration.cmap,
            shading="auto",
            alpha=decoration.alpha,
        )
        if figure is not None and hasattr(figure, "colorbar"):
            figure.colorbar(mesh, ax=ax)
    elif isinstance(histogram, profile):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        ax.errorbar(
            centers,
            histogram.means,
            yerr=histogram.errors,
            label=decoration.label or histogram.name,
            color=decoration.color,
            linestyle=decoration.line_style,
            linewidth=decoration.line_width,
            marker=decoration.marker,
            markersize=decoration.marker_size,
            alpha=decoration.alpha,
        )
    elif isinstance(histogram, efficiency):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        ax.errorbar(
            centers,
            histogram.values,
            yerr=histogram.errors,
            label=decoration.label or histogram.name,
            color=decoration.color,
            linestyle=decoration.line_style,
            linewidth=decoration.line_width,
            marker=decoration.marker,
            markersize=decoration.marker_size,
            alpha=decoration.alpha,
        )
        ax.set_ylim(0.0, 1.05)
    else:  # pragma: no cover
        raise TypeError(f"Unsupported histogram type: {type(histogram)!r}")

    _apply_matplotlib_decoration(ax, decoration)
    return fig, ax


def _apply_matplotlib_decoration(axis: Any, decoration: Decoration) -> None:
    if decoration.title is not None:
        axis.set_title(decoration.title, fontsize=decoration.font_size, fontfamily=decoration.font_family)
    if decoration.x_label is not None:
        axis.set_xlabel(decoration.x_label, fontsize=decoration.label_size)
    if decoration.y_label is not None:
        axis.set_ylabel(decoration.y_label, fontsize=decoration.label_size)
    if decoration.tick_size is not None:
        axis.tick_params(axis="both", labelsize=decoration.tick_size)
    if decoration.show_grid:
        axis.grid(True, alpha=0.3)
    if decoration.show_legend:
        handles, labels = axis.get_legend_handles_labels()
        if labels:
            axis.legend()


def _plot_plotly(
    histogram: hist1d | hist2d | profile | efficiency,
    decoration: Decoration,
    *,
    figure: Any | None,
    row: int | None,
    col: int | None,
):
    try:
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover
        raise ImportError("plotly is required for backend='plotly'.") from exc

    fig = go.Figure() if figure is None else figure

    if isinstance(histogram, hist1d):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        widths = np.diff(histogram.edges)
        trace = go.Bar(
            x=centers,
            y=histogram.counts,
            width=widths,
            name=decoration.label or histogram.name,
            marker_color=decoration.fill_color or decoration.color,
            opacity=decoration.alpha,
        )
        _add_plotly_trace(fig, trace, row=row, col=col)
    elif isinstance(histogram, hist2d):
        trace = go.Heatmap(
            x=histogram.x_edges,
            y=histogram.y_edges,
            z=histogram.counts.T,
            colorscale=decoration.cmap,
            opacity=decoration.alpha,
            name=decoration.label or histogram.name,
        )
        _add_plotly_trace(fig, trace, row=row, col=col)
    elif isinstance(histogram, profile):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        trace = go.Scatter(
            x=centers,
            y=histogram.means,
            mode=_plotly_mode(decoration),
            name=decoration.label or histogram.name,
            marker={"size": decoration.marker_size, "color": decoration.color},
            line={"color": decoration.color, "dash": decoration.line_style, "width": decoration.line_width},
            error_y={"type": "data", "array": histogram.errors, "visible": True},
            opacity=decoration.alpha,
        )
        _add_plotly_trace(fig, trace, row=row, col=col)
    elif isinstance(histogram, efficiency):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        trace = go.Scatter(
            x=centers,
            y=histogram.values,
            mode=_plotly_mode(decoration),
            name=decoration.label or histogram.name,
            marker={"size": decoration.marker_size, "color": decoration.color},
            line={"color": decoration.color, "dash": decoration.line_style, "width": decoration.line_width},
            error_y={"type": "data", "array": histogram.errors, "visible": True},
            opacity=decoration.alpha,
        )
        _add_plotly_trace(fig, trace, row=row, col=col)
        _update_plotly_layout(fig, yaxis_range=[0.0, 1.05])
    else:  # pragma: no cover
        raise TypeError(f"Unsupported histogram type: {type(histogram)!r}")

    _apply_plotly_decoration(fig, decoration)
    return fig


def _plotly_mode(decoration: Decoration) -> str:
    if decoration.marker:
        return "markers+lines"
    return "lines"


def _add_plotly_trace(fig: Any, trace: Any, *, row: int | None, col: int | None) -> None:
    if row is not None or col is not None:
        if row is None or col is None:
            raise ValueError("Both row and col must be provided when targeting a plotly subplot.")
        fig.add_trace(trace, row=row, col=col)
    else:
        fig.add_trace(trace)


def _apply_plotly_decoration(fig: Any, decoration: Decoration) -> None:
    title_font = {}
    if decoration.font_family is not None:
        title_font["family"] = decoration.font_family
    if decoration.font_size is not None:
        title_font["size"] = decoration.font_size

    axis_title_font = {}
    if decoration.label_size is not None:
        axis_title_font["size"] = decoration.label_size

    layout_updates = {
        "showlegend": decoration.show_legend,
        "title": decoration.title,
        "xaxis_title": decoration.x_label,
        "yaxis_title": decoration.y_label,
    }
    if title_font:
        layout_updates["title_font"] = title_font
    if axis_title_font:
        layout_updates["xaxis_title_font"] = axis_title_font
        layout_updates["yaxis_title_font"] = axis_title_font
    if decoration.tick_size is not None:
        layout_updates["xaxis_tickfont"] = {"size": decoration.tick_size}
        layout_updates["yaxis_tickfont"] = {"size": decoration.tick_size}
    if decoration.show_grid:
        layout_updates["xaxis_showgrid"] = True
        layout_updates["yaxis_showgrid"] = True

    _update_plotly_layout(fig, **layout_updates)


def _update_plotly_layout(fig: Any, **kwargs: Any) -> None:
    kwargs = {key: value for key, value in kwargs.items() if value is not None}
    if kwargs:
        fig.update_layout(**kwargs)

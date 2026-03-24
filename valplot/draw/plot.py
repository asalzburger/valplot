"""Backend-agnostic plotting entry point for valplot histogram containers."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Sequence

import numpy as np

from ..histograms import band, efficiency, hist1d, hist2d, profile, restricted_profile, scatter
from .decorations import Decoration


def plot(
    histogram: hist1d | hist2d | profile | restricted_profile | efficiency | scatter | band,
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


def plot_scatter(
    points: scatter,
    decoration: Decoration | None = None,
    *,
    backend: str = "matplotlib",
    figure: Any | None = None,
    axis: Any | None = None,
):
    """Plot scatter points."""
    return plot(points, decoration=decoration, backend=backend, figure=figure, axis=axis)


def plot_band(
    histograms: Sequence[hist1d | profile | restricted_profile | band],
    decorations: Sequence[Decoration] | None = None,
    *,
    spread: str | None = None,
    backend: str = "matplotlib",
    figure: Any | None = None,
    axis: Any | None = None,
):
    """Overlay band plots from hist1d/profile/band objects."""
    if len(histograms) == 0:
        raise ValueError("histograms must contain at least one item")
    for histogram in histograms:
        if not isinstance(histogram, (hist1d, profile, restricted_profile, band)):
            raise TypeError("plot_band supports only hist1d, profile, or band objects")

    if decorations is None:
        decos = [Decoration() for _ in histograms]
    else:
        if len(decorations) != len(histograms):
            raise ValueError("decorations length must match histograms length")
        decos = list(decorations)

    if backend != "matplotlib":
        raise ValueError("plot_band currently supports backend='matplotlib' only.")

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

    for histogram, deco in zip(histograms, decos):
        edges, centers, lower, upper, values = _band_arrays_from_histogram(histogram, spread=spread)
        _ = edges
        band_color = deco.fill_color or deco.color
        ax.fill_between(
            centers,
            lower,
            upper,
            alpha=deco.band_alpha if deco.band_alpha is not None else 0.5,
            color=band_color,
        )
        ax.plot(
            centers,
            values,
            label=deco.label or histogram.name,
            color=deco.color,
            alpha=deco.alpha,
            linestyle=deco.line_style,
            linewidth=deco.line_width,
            marker=deco.marker,
            markersize=deco.marker_size,
        )

    _apply_matplotlib_decoration(ax, decos[0])
    return fig, ax


def plot_ratio(
    histograms: Sequence[hist1d | profile | restricted_profile],
    decorations: Sequence[Decoration] | None = None,
    *,
    backend: str = "matplotlib",
):
    """Overlay 1D distributions and draw ratios to the first item."""
    if len(histograms) == 0:
        raise ValueError("histograms must contain at least one item")

    for histogram in histograms:
        if not isinstance(histogram, (hist1d, profile, restricted_profile)):
            raise TypeError("plot_ratio supports only hist1d and profile objects")

    first = histograms[0]
    profile_like = (profile, restricted_profile)
    if isinstance(first, profile_like):
        if any(not isinstance(hist, profile_like) for hist in histograms):
            raise TypeError("All histograms passed to plot_ratio must be hist1d or profile-like")
    elif isinstance(first, hist1d):
        if any(not isinstance(hist, hist1d) for hist in histograms):
            raise TypeError("All histograms passed to plot_ratio must be hist1d or profile-like")

    if decorations is None:
        decos = [Decoration() for _ in histograms]
    else:
        if len(decorations) != len(histograms):
            raise ValueError("decorations length must match histograms length")
        decos = list(decorations)

    if backend != "matplotlib":
        raise ValueError("plot_ratio currently supports backend='matplotlib' only.")

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover
        raise ImportError("matplotlib is required for backend='matplotlib'.") from exc

    fig, axes = plt.subplots(
        2,
        1,
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    if hasattr(fig, "subplots_adjust"):
        fig.subplots_adjust(hspace=0.05)
    top_ax, ratio_ax = axes

    for histogram, deco in zip(histograms, decos):
        _draw_matplotlib_histogram(top_ax, histogram, deco, figure=fig)
    _apply_matplotlib_decoration(top_ax, replace(decos[0], x_label=None))

    denominator = histograms[0]
    for histogram, deco in zip(histograms[1:], decos[1:]):
        ratio_values, ratio_errors, edges = _ratio_to_denominator(histogram, denominator)
        centers = 0.5 * (edges[:-1] + edges[1:])
        ratio_ax.errorbar(
            centers,
            ratio_values,
            yerr=ratio_errors,
            label=deco.label or histogram.name,
            color=deco.color,
            linestyle=deco.line_style,
            linewidth=deco.line_width,
            marker=deco.marker or "o",
            markersize=deco.marker_size,
            alpha=deco.alpha,
        )

    ratio_ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0, alpha=0.8)
    ratio_ax.set_ylabel("Ratio")
    if decos[0].x_label is not None:
        ratio_ax.set_xlabel(decos[0].x_label, fontsize=decos[0].label_size)
    if decos[0].tick_size is not None:
        ratio_ax.tick_params(axis="both", labelsize=decos[0].tick_size)
    if decos[0].show_grid:
        ratio_ax.grid(True, alpha=0.3)
    if decos[0].show_legend:
        handles, labels = ratio_ax.get_legend_handles_labels()
        if labels:
            ratio_ax.legend()

    return fig, (top_ax, ratio_ax)


def _parse_sigma(spread: str) -> float:
    if not spread.endswith("sigma"):
        raise ValueError(f"Unsupported spread mode '{spread}'. Use 'spread' or '<N>sigma'.")
    factor = spread[: -len("sigma")].strip()
    if factor == "":
        raise ValueError(f"Unsupported spread mode '{spread}'.")
    sigma = float(factor)
    if sigma <= 0.0:
        raise ValueError("Sigma factor must be positive.")
    return sigma


def _band_arrays_from_histogram(
    histogram: hist1d | profile | band,
    *,
    spread: str | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if isinstance(histogram, hist1d):
        edges = histogram.edges
        values = histogram.counts
        errors = histogram.errors
        mode = "1sigma" if spread is None else spread
        if mode == "spread":
            raise ValueError("spread mode is only available for band objects.")
        sigma = _parse_sigma(mode)
        lower = values - sigma * errors
        upper = values + sigma * errors
    elif isinstance(histogram, (profile, restricted_profile)):
        edges = histogram.edges
        values = histogram.means
        errors = histogram.errors
        mode = "1sigma" if spread is None else spread
        if mode == "spread":
            raise ValueError("spread mode is only available for band objects.")
        sigma = _parse_sigma(mode)
        lower = values - sigma * errors
        upper = values + sigma * errors
    else:
        edges = histogram.edges
        values = histogram.values
        errors = histogram.errors
        mode = "spread" if spread is None else spread
        if mode == "spread":
            lower = histogram.lower
            upper = histogram.upper
        else:
            sigma = _parse_sigma(mode)
            lower = values - sigma * errors
            upper = values + sigma * errors

    centers = 0.5 * (edges[:-1] + edges[1:])
    return edges, centers, lower, upper, values


def _draw_matplotlib_histogram(
    axis: Any,
    histogram: hist1d | hist2d | profile | restricted_profile | efficiency | scatter | band,
    decoration: Decoration,
    *,
    figure: Any,
):
    if isinstance(histogram, hist1d):
        axis.stairs(
            histogram.counts,
            histogram.edges,
            label=decoration.label or histogram.name,
            color=decoration.color,
            alpha=decoration.alpha,
            linestyle=decoration.line_style,
            linewidth=decoration.line_width,
            fill=decoration.fill,
        )
        return

    if isinstance(histogram, hist2d):
        mesh = axis.pcolormesh(
            histogram.x_edges,
            histogram.y_edges,
            histogram.counts.T,
            cmap=decoration.cmap,
            shading="auto",
            alpha=decoration.alpha,
        )
        if figure is not None and hasattr(figure, "colorbar"):
            figure.colorbar(mesh, ax=axis)
        return

    if isinstance(histogram, (profile, restricted_profile)):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        axis.errorbar(
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
        return

    if isinstance(histogram, efficiency):
        centers = 0.5 * (histogram.edges[:-1] + histogram.edges[1:])
        axis.errorbar(
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
        axis.set_ylim(0.0, 1.05)
        return

    if isinstance(histogram, scatter):
        axis.scatter(
            histogram.x,
            histogram.y,
            label=decoration.label or histogram.name,
            color=decoration.color,
            alpha=decoration.alpha,
            marker=decoration.marker or "o",
        )
        return

    if isinstance(histogram, band):
        _, centers, lower, upper, values = _band_arrays_from_histogram(histogram, spread=None)
        axis.fill_between(
            centers,
            lower,
            upper,
            alpha=decoration.band_alpha if decoration.band_alpha is not None else 0.5,
            color=decoration.fill_color or decoration.color,
        )
        axis.plot(
            centers,
            values,
            label=decoration.label or histogram.name,
            color=decoration.color,
            alpha=decoration.alpha,
            linestyle=decoration.line_style,
            linewidth=decoration.line_width,
            marker=decoration.marker,
            markersize=decoration.marker_size,
        )
        return

    raise TypeError(f"Unsupported histogram type: {type(histogram)!r}")


def _ratio_to_denominator(
    numerator: hist1d | profile | restricted_profile,
    denominator: hist1d | profile | restricted_profile,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if isinstance(numerator, hist1d):
        num_values = numerator.counts
        num_errors = numerator.errors
        edges = numerator.edges
    else:
        num_values = numerator.means
        num_errors = numerator.errors
        edges = numerator.edges

    if isinstance(denominator, hist1d):
        den_values = denominator.counts
        den_errors = denominator.errors
        den_edges = denominator.edges
    else:
        den_values = denominator.means
        den_errors = denominator.errors
        den_edges = denominator.edges

    if edges.shape != den_edges.shape or not np.allclose(edges, den_edges):
        raise ValueError("All histograms in plot_ratio must use compatible bin edges.")

    ratio_values = np.divide(num_values, den_values, out=np.full_like(num_values, np.nan, dtype=float), where=den_values != 0.0)
    relative_num = np.divide(num_errors, num_values, out=np.zeros_like(num_values, dtype=float), where=num_values != 0.0)
    relative_den = np.divide(den_errors, den_values, out=np.zeros_like(den_values, dtype=float), where=den_values != 0.0)
    ratio_errors = np.abs(ratio_values) * np.sqrt(np.square(relative_num) + np.square(relative_den))
    ratio_errors = np.asarray(ratio_errors, dtype=float)
    ratio_errors[~np.isfinite(ratio_values)] = 0.0

    return ratio_values, ratio_errors, edges


def _plot_matplotlib(
    histogram: hist1d | hist2d | profile | restricted_profile | efficiency | scatter | band,
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

    _draw_matplotlib_histogram(ax, histogram, decoration, figure=figure)
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
    histogram: hist1d | hist2d | profile | restricted_profile | efficiency | scatter | band,
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
    elif isinstance(histogram, (profile, restricted_profile)):
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
    elif isinstance(histogram, scatter):
        trace = go.Scatter(
            x=histogram.x,
            y=histogram.y,
            mode="markers",
            name=decoration.label or histogram.name,
            marker={"size": decoration.marker_size, "color": decoration.color},
            opacity=decoration.alpha,
        )
        _add_plotly_trace(fig, trace, row=row, col=col)
    elif isinstance(histogram, band):
        raise ValueError("plotly backend does not yet support band objects; use backend='matplotlib'.")
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

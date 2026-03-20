"""Plot decoration containers shared by all drawing backends."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decoration:
    """Generic drawing options applied by backend-specific plotters."""

    title: str | None = None
    x_label: str | None = None
    y_label: str | None = None

    label: str | None = None
    color: str | None = None
    alpha: float | None = None

    line_style: str | None = "-"
    line_width: float | None = 1.5

    marker: str | None = None
    marker_size: float | None = None
    marker_face_color: str | None = None
    marker_edge_color: str | None = None

    fill: bool = False
    fill_color: str | None = None
    fill_alpha: float | None = 0.25
    band_alpha: float | None = 0.5

    font_family: str | None = None
    font_size: float | None = None
    label_size: float | None = None
    tick_size: float | None = None

    show_grid: bool = False
    show_legend: bool = True

    cmap: str | None = None

"""Style showcase demo for valplot plotting helpers."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import numpy as np
import uproot

# Allow running this file directly from the repository checkout.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

try:
    import plotval
except ImportError:  # Local package name in this repository.
    import valplot as plotval

from valplot.io.root.histograms import hist1d_from_uproot, hist2d_from_uproot


SCHEMAS = [
    {
        "name": "classic",
        "primary": "tab:blue",
        "secondary": "tab:orange",
        "accent": "tab:green",
        "cmap": "viridis",
        "line_main": "-",
        "line_alt": "--",
    },
    {
        "name": "sunset",
        "primary": "#8c2d04",
        "secondary": "#d95f0e",
        "accent": "#f16913",
        "cmap": "magma",
        "line_main": "-",
        "line_alt": ":",
    },
    {
        "name": "forest",
        "primary": "#1b4332",
        "secondary": "#2d6a4f",
        "accent": "#40916c",
        "cmap": "cividis",
        "line_main": "-",
        "line_alt": "-.",
    },
]


def _profile_from_uproot(obj, name: str) -> plotval.profile:
    return plotval.profile(
        edges=np.asarray(obj.axis().edges(flow=False), dtype=float),
        means=np.asarray(obj.values(flow=False), dtype=float),
        errors=np.asarray(obj.errors(flow=False), dtype=float),
        entries=np.asarray(obj.counts(flow=False), dtype=float),
        name=name,
    )


def _save_profile_ratio_with_errorbars(
    prof_x: plotval.profile,
    prof_y: plotval.profile,
    schema: dict[str, str],
    out_dir: Path,
) -> None:
    fig, _ = plotval.plot_ratio(
        [prof_x, prof_y],
        [
            plotval.Decoration(
                title=f"Profile Errorbars + Ratio ({schema['name']})",
                x_label="x",
                y_label="Profile mean",
                label="ProfileX",
                color=schema["primary"],
                line_style=schema["line_main"],
                marker="o",
                marker_size=3.0,
                show_grid=True,
            ),
            plotval.Decoration(
                label="ProfileY",
                color=schema["secondary"],
                line_style=schema["line_alt"],
                marker="s",
                marker_size=3.0,
            ),
        ],
        backend="matplotlib",
    )
    fig.savefig(out_dir / f"style_{schema['name']}_profile_ratio_errorbars.png", dpi=140, bbox_inches="tight")


def _save_profile_ratio_with_bands(
    prof_x: plotval.profile,
    prof_y: plotval.profile,
    schema: dict[str, str],
    out_dir: Path,
) -> None:
    fig, (top_ax, _) = plotval.plot_ratio(
        [prof_x, prof_y],
        [
            plotval.Decoration(
                title=f"Profile Bands + Ratio ({schema['name']})",
                x_label="x",
                y_label="Profile mean",
                label="ProfileX",
                color=schema["primary"],
                line_style=schema["line_main"],
                marker="o",
                marker_size=3.0,
                show_grid=True,
            ),
            plotval.Decoration(
                label="ProfileY",
                color=schema["secondary"],
                line_style=schema["line_alt"],
                marker="s",
                marker_size=3.0,
            ),
        ],
        backend="matplotlib",
    )

    # Overlay 1-sigma bands on top panel while keeping ratio panel untouched.
    plotval.plot_band(
        [prof_x, prof_y],
        [
            plotval.Decoration(
                color=schema["primary"],
                fill_color=schema["primary"],
                band_alpha=0.22,
                show_legend=False,
            ),
            plotval.Decoration(
                color=schema["secondary"],
                fill_color=schema["secondary"],
                band_alpha=0.22,
                show_legend=False,
            ),
        ],
        spread="1sigma",
        backend="matplotlib",
        figure=fig,
        axis=top_ax,
    )
    fig.savefig(out_dir / f"style_{schema['name']}_profile_ratio_band.png", dpi=140, bbox_inches="tight")


def _save_hist1_styles(hx: plotval.hist1d, hy: plotval.hist1d, schema: dict[str, str], out_dir: Path) -> None:
    fig, _ = plotval.plot(
        hx,
        decoration=plotval.Decoration(
            title=f"hist1 styles ({schema['name']})",
            x_label="x",
            y_label="Entries",
            label="hx",
            color=schema["primary"],
            fill=True,
            alpha=0.5,
            line_style=schema["line_main"],
            line_width=1.8,
            show_grid=True,
        ),
        backend="matplotlib",
    )
    plotval.plot(
        hy,
        decoration=plotval.Decoration(
            label="hy",
            color=schema["secondary"],
            fill=False,
            line_style=schema["line_alt"],
            line_width=2.1,
        ),
        backend="matplotlib",
        axis=fig.gca(),
    )
    fig.savefig(out_dir / f"style_{schema['name']}_hist1_overlay.png", dpi=140, bbox_inches="tight")


def _save_hist2_styles(hxy: plotval.hist2d, schema: dict[str, str], out_dir: Path) -> None:
    fig, _ = plotval.plot(
        hxy,
        decoration=plotval.Decoration(
            title=f"hist2 styles ({schema['name']})",
            x_label="x",
            y_label="y",
            cmap=schema["cmap"],
            alpha=0.95,
        ),
        backend="matplotlib",
    )
    fig.savefig(out_dir / f"style_{schema['name']}_hist2_heatmap.png", dpi=140, bbox_inches="tight")


def main() -> None:
    root_path = REPO_ROOT / "tests" / "data" / "tests_input.root"
    out_dir = REPO_ROOT / "examples" / "output"
    out_dir.mkdir(exist_ok=True)

    with uproot.open(root_path) as root_file:
        hx = hist1d_from_uproot(root_file["hx"], name="hx")
        hy = hist1d_from_uproot(root_file["hy"], name="hy")
        hxy = hist2d_from_uproot(root_file["hxy"], name="hxy")
        prof_x = _profile_from_uproot(root_file["profX"], name="profX")
        prof_y = _profile_from_uproot(root_file["profY"], name="profY")

    for schema in SCHEMAS:
        _save_profile_ratio_with_errorbars(prof_x, prof_y, schema, out_dir)
        _save_profile_ratio_with_bands(prof_x, prof_y, schema, out_dir)
        _save_hist1_styles(hx, hy, schema, out_dir)
        _save_hist2_styles(hxy, schema, out_dir)

    print(f"Saved style showcase plots to: {out_dir}")


if __name__ == "__main__":
    main()

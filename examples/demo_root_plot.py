"""Simple demo: read ROOT content with uproot and plot with valplot."""

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

from valplot.io.root.histograms import efficiency_from_tefficiency_uproot, hist1d_from_uproot, hist2d_from_uproot


def _profile_from_uproot(obj, name: str) -> plotval.profile:
    return plotval.profile(
        edges=np.asarray(obj.axis().edges(flow=False), dtype=float),
        means=np.asarray(obj.values(flow=False), dtype=float),
        errors=np.asarray(obj.errors(flow=False), dtype=float),
        entries=np.asarray(obj.counts(flow=False), dtype=float),
        name=name,
    )


def main() -> None:
    root_path = Path(__file__).resolve().parents[1] / "tests" / "data" / "tests_input.root"
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)

    with uproot.open(root_path) as root_file:
        hx = hist1d_from_uproot(root_file["hx"], name="hx")
        hy = hist1d_from_uproot(root_file["hy"], name="hy")
        hxy = hist2d_from_uproot(root_file["hxy"], name="hxy")
        h_pass = hist1d_from_uproot(root_file["h_pass"], name="h_pass")
        prof_x = _profile_from_uproot(root_file["profX"], name="profX")
        prof_y = _profile_from_uproot(root_file["profY"], name="profY")

        try:
            eff_x = efficiency_from_tefficiency_uproot(root_file["eff_x"], name="eff_x")
        except Exception:
            eff_x = plotval.efficiency(edges=hx.edges, passed=h_pass.counts, total=hx.counts, name="eff_x")

    fig, _ = plotval.plot(
        hx,
        decoration=plotval.Decoration(
            title="X/Y distributions",
            x_label="x or y",
            y_label="Entries",
            label="hx",
            color="tab:blue",
            show_grid=True,
        ),
        backend="matplotlib",
    )
    plotval.plot(
        hy,
        decoration=plotval.Decoration(
            label="hy",
            color="tab:orange",
            line_style="--",
        ),
        backend="matplotlib",
        axis=fig.gca(),
    )
    fig.savefig(out_dir / "overlay_hx_hy.png", dpi=140, bbox_inches="tight")

    fig2, _ = plotval.plot(
        hxy,
        decoration=plotval.Decoration(
            title="2D Gaussian",
            x_label="x",
            y_label="y",
            cmap="viridis",
        ),
        backend="matplotlib",
    )
    fig2.savefig(out_dir / "hxy_heatmap.png", dpi=140, bbox_inches="tight")

    fig3, _ = plotval.plot(
        prof_x,
        decoration=plotval.Decoration(
            title="Profiles",
            x_label="x",
            y_label="mean",
            label="ProfileX",
            marker="o",
            marker_size=3.0,
            color="tab:green",
            show_grid=True,
        ),
        backend="matplotlib",
    )
    plotval.plot(
        prof_y,
        decoration=plotval.Decoration(
            label="ProfileY",
            marker="s",
            marker_size=3.0,
            color="tab:red",
            line_style=":",
        ),
        backend="matplotlib",
        axis=fig3.gca(),
    )
    fig3.savefig(out_dir / "profiles.png", dpi=140, bbox_inches="tight")

    fig4, _ = plotval.plot(
        eff_x,
        decoration=plotval.Decoration(
            title="Efficiency vs x",
            x_label="x",
            y_label="Efficiency",
            label="eff_x",
            marker="o",
            marker_size=3.0,
            color="tab:purple",
            show_grid=True,
        ),
        backend="matplotlib",
    )
    fig4.savefig(out_dir / "efficiency.png", dpi=140, bbox_inches="tight")

    fig5, _ = plotval.plot_ratio(
        [hx, hy],
        [
            plotval.Decoration(
                title="X vs Y with ratio",
                x_label="x or y",
                y_label="Entries",
                label="hx",
                color="tab:blue",
                show_grid=True,
            ),
            plotval.Decoration(
                label="hy",
                color="tab:orange",
                line_style="--",
            ),
        ],
        backend="matplotlib",
    )
    fig5.savefig(out_dir / "ratio_hx_hy.png", dpi=140, bbox_inches="tight")

    print(f"Saved demo plots to: {out_dir}")


if __name__ == "__main__":
    main()

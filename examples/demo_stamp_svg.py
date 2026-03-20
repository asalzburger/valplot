"""Demo: generate an SVG plot and stamp it with a logo."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import uproot

# Allow running this file directly from the repository checkout.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(REPO_ROOT / ".cache"))

try:
    import plotval
except ImportError:  # Local package name in this repository.
    import valplot as plotval

from utilities.stamp_svg import stamp_svg
from valplot.io.root.histograms import hist1d_from_uproot


def main() -> None:
    root_path = REPO_ROOT / "tests" / "data" / "tests_input.root"
    stamp_path = REPO_ROOT / "resources" / "sd" / "super_duper.svg"
    out_dir = REPO_ROOT / "examples" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_svg = out_dir / "overlay_hx_hy.svg"
    stamped_svg = out_dir / "overlay_hx_hy_sd.svg"

    with uproot.open(root_path) as root_file:
        hx = hist1d_from_uproot(root_file["hx"], name="hx")
        hy = hist1d_from_uproot(root_file["hy"], name="hy")

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
    fig.savefig(plot_svg, bbox_inches="tight")

    stamp_svg(
        input_svg=plot_svg,
        stamp_svg_path=stamp_path,
        output_svg=stamped_svg,
        location=(0.15, 0.3),
        size_fraction=0.2,
    )

    print(f"Wrote plot SVG: {plot_svg}")
    print(f"Wrote stamped SVG: {stamped_svg}")


if __name__ == "__main__":
    main()

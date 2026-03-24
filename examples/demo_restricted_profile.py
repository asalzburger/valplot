"""Demo: unrestricted and restricted profile ratio comparisons using restricted_profile."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import uproot

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

try:
    import plotval
except ImportError:
    import valplot as plotval

from valplot.io.root import profile_from_tree, restricted_profile_from_tree

RESTRICTED_ROOT = REPO_ROOT / "tests" / "data" / "tests_restricted.root"
TREE = "restricted_profile"
BINS = 40
X_RANGE = (-5.0, 5.0)
Z_RANGE = (-5.0, 5.0)


def main() -> None:
    out_dir = REPO_ROOT / "examples" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Unrestricted: profile v1/v0 vs x
    p_v0_x = profile_from_tree(
        str(RESTRICTED_ROOT), TREE, x_branch="x", y_branch="v0", bins=BINS, range=X_RANGE, name="v0"
    )
    p_v1_x = profile_from_tree(
        str(RESTRICTED_ROOT), TREE, x_branch="x", y_branch="v1", bins=BINS, range=X_RANGE, name="v1"
    )

    fig1, _ = plotval.plot_ratio(
        [p_v0_x, p_v1_x],
        [
            plotval.Decoration(
                title="v1/v0 vs x (unrestricted)",
                x_label="x",
                y_label="value",
                label="v0",
                color="tab:blue",
                marker="o",
                marker_size=2.5,
                show_grid=True,
            ),
            plotval.Decoration(label="v1", color="tab:orange", line_style="--", marker="s", marker_size=2.5),
        ],
        backend="matplotlib",
    )
    fig1.savefig(out_dir / "restricted_profile_ratio_v1_v0_vs_x.png", dpi=140, bbox_inches="tight")

    # Unrestricted: profile v1/v0 vs y
    p_v0_y = profile_from_tree(
        str(RESTRICTED_ROOT), TREE, x_branch="y", y_branch="v0", bins=BINS, range=Z_RANGE, name="v0"
    )
    p_v1_y = profile_from_tree(
        str(RESTRICTED_ROOT), TREE, x_branch="y", y_branch="v1", bins=BINS, range=Z_RANGE, name="v1"
    )

    fig2, _ = plotval.plot_ratio(
        [p_v0_y, p_v1_y],
        [
            plotval.Decoration(
                title="v1/v0 vs y (unrestricted)",
                x_label="y",
                y_label="value",
                label="v0",
                color="tab:green",
                marker="o",
                marker_size=2.5,
                show_grid=True,
            ),
            plotval.Decoration(label="v1", color="tab:red", line_style="--", marker="s", marker_size=2.5),
        ],
        backend="matplotlib",
    )
    fig2.savefig(out_dir / "restricted_profile_ratio_v1_v0_vs_y.png", dpi=140, bbox_inches="tight")

    # Restricted: v1/v0 vs x with y in [-4, 4]
    rp_v0_x = restricted_profile_from_tree(
        str(RESTRICTED_ROOT),
        TREE,
        x_branch="x",
        y_branch="v0",
        restriction_branch="y",
        restriction_range=(-4.0, 4.0),
        bins=BINS,
        range=X_RANGE,
        name="v0 (y∈[-4,4])",
    )
    rp_v1_x = restricted_profile_from_tree(
        str(RESTRICTED_ROOT),
        TREE,
        x_branch="x",
        y_branch="v1",
        restriction_branch="y",
        restriction_range=(-4.0, 4.0),
        bins=BINS,
        range=X_RANGE,
        name="v1 (y∈[-4,4])",
    )

    fig3, _ = plotval.plot_ratio(
        [rp_v0_x, rp_v1_x],
        [
            plotval.Decoration(
                title="v1/v0 vs x (y ∈ [-4, 4])",
                x_label="x",
                y_label="value",
                label="v0",
                color="tab:purple",
                marker="o",
                marker_size=2.5,
                show_grid=True,
            ),
            plotval.Decoration(label="v1", color="tab:brown", line_style="--", marker="s", marker_size=2.5),
        ],
        backend="matplotlib",
    )
    fig3.savefig(out_dir / "restricted_profile_ratio_v1_v0_vs_x_zcut.png", dpi=140, bbox_inches="tight")

    print(f"Saved restricted profile demo plots to: {out_dir}")


if __name__ == "__main__":
    main()

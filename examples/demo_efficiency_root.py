"""Demo: read ``tests/data/tests_efficiency.root`` (TEfficiency) and plot efficiency vs bin."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

try:
    import plotval
except ImportError:
    import valplot as plotval

from valplot.io.root import read_tefficiency


def main() -> int:
    root_path = REPO_ROOT / "tests" / "data" / "tests_efficiency.root"
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)
    object_path = "efficiency"

    if len(sys.argv) > 1:
        object_path = sys.argv[1]

    if not root_path.exists():
        print(f"Missing input file: {root_path}", file=sys.stderr)
        return 1

    try:
        eff = read_tefficiency(str(root_path), object_path)
    except NotImplementedError as e:
        print(
            "Could not read TEfficiency from this ROOT file with the current uproot version.\n"
            "Try upgrading uproot, or use tests_input.root + eff_x via examples/demo_root_plot.py.",
            file=sys.stderr,
        )
        print(str(e), file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Failed to read '{object_path}' from {root_path}: {e}", file=sys.stderr)
        return 2

    fig, _ = plotval.plot(
        eff,
        decoration=plotval.Decoration(
            title=f"Efficiency ({object_path})",
            x_label="bin",
            y_label="Efficiency",
            label=object_path,
            marker="o",
            marker_size=3.0,
            color="tab:purple",
            show_grid=True,
        ),
        backend="matplotlib",
    )
    out_png = out_dir / "efficiency_tests_efficiency_root.png"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    print(f"Wrote: {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

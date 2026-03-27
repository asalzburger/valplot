"""CLI utility: read a TEfficiency object with uproot+PyROOT fallback and plot it."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Allow running directly via absolute path.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from valplot import Decoration, plot
from valplot.io.root import read_tefficiency


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Read TEfficiency with PyROOT fallback and render a plot.")
    p.add_argument("--file", required=True, help="Input ROOT file.")
    p.add_argument("--object", required=True, help="TEfficiency object path in ROOT file.")
    p.add_argument("--output-dir", default="examples/output", help="Directory for output PNG.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        eff = read_tefficiency(args.file, args.object)
    except Exception as exc:
        print(f"Failed to read TEfficiency '{args.object}' from '{args.file}': {exc}", file=sys.stderr)
        return 2

    fig, _ = plot(
        eff,
        decoration=Decoration(
            title=f"TEfficiency: {args.object}",
            x_label="bin",
            y_label="Efficiency",
            label=args.object,
            marker="o",
            marker_size=3.0,
            color="tab:purple",
            show_grid=True,
        ),
        backend="matplotlib",
    )
    out_png = out_dir / "tefficiency_fallback.png"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    print(f"Wrote: {out_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


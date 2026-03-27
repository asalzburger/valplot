"""Overlay 1D distributions from tree branches (scalar or one-level jagged)."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np

# Allow running this file directly via absolute path.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from valplot import Decoration, hist1d, plot, plot_band, plot_ratio
from valplot.io.root import hist1d_from_tree
from valplot.io.root.histograms import _import_uproot, flatten_branch_values


_SIGMA_RE = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)sigma$")


def parse_ratio_mode(raw: str | None) -> tuple[bool, tuple[float, float] | None]:
    if raw is None:
        return False, None
    raw = raw.strip()
    if raw == "full":
        return True, None
    if raw.startswith("range:"):
        parts = [p.strip() for p in raw.split(":")]
        if len(parts) != 3:
            raise ValueError(f"Invalid --ratio value '{raw}'. Expected 'range:min_val:max_val'.")
        lo = float(parts[1])
        hi = float(parts[2])
        if not (np.isfinite(lo) and np.isfinite(hi)):
            raise ValueError("--ratio range values must be finite floats.")
        if lo == hi:
            eps = 0.5 if lo == 0.0 else abs(lo) * 0.01
            lo -= eps
            hi += eps
        if lo > hi:
            lo, hi = hi, lo
        return True, (lo, hi)
    raise ValueError(f"Invalid --ratio value '{raw}'. Expected 'full' or 'range:min_val:max_val'.")


def parse_band_spread(raw: str | None) -> str | None:
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "spread":
        return "spread"
    if _SIGMA_RE.match(raw):
        return raw
    raise ValueError(f"Invalid band spread token '{raw}'. Expected 'spread' or '<N>sigma'.")


def parse_labels(raw: list[str] | None, n_files: int) -> list[str] | None:
    if raw is None:
        return None
    if len(raw) == 1 and raw[0].lower() == "none":
        return None
    if len(raw) != n_files:
        raise ValueError(f"--labels length must be {n_files} (or 'None'); got {len(raw)}.")
    return raw


def parse_x_range(raw: list[float] | None) -> tuple[float, float] | None:
    if raw is None:
        return None
    if len(raw) != 2:
        raise ValueError("--range expects two floats: LO HI.")
    lo = float(raw[0])
    hi = float(raw[1])
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("--range values must be finite floats.")
    if lo == hi:
        eps = 0.5 if lo == 0.0 else abs(lo) * 0.01
        lo -= eps
        hi += eps
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _validate_root_files(files: list[str]) -> None:
    non_root = [f for f in files if not f.endswith(".root")]
    if non_root:
        bad = ", ".join(non_root[:5])
        raise ValueError(f"All --files must end with '.root'. Got: {bad}")


def _global_branch_range(file_tree_pairs: list[tuple[str, str]], branch: str) -> tuple[float, float]:
    uproot = _import_uproot()
    chunks: list[np.ndarray] = []
    for file_path, tree_path in file_tree_pairs:
        with uproot.open(file_path) as root_file:
            tree = root_file[tree_path]
            arrays = tree.arrays([branch], library="np")
            values = flatten_branch_values(arrays[branch], branch_name=branch)
            chunks.append(values)

    if not chunks:
        raise ValueError("No input data found.")
    values_all = np.concatenate(chunks)
    if values_all.size == 0:
        raise ValueError(f"Branch '{branch}' has no entries.")
    lo = float(np.min(values_all))
    hi = float(np.max(values_all))
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError(f"Branch '{branch}' contains non-finite values.")
    if lo == hi:
        eps = 0.5 if lo == 0.0 else abs(lo) * 0.01
        lo -= eps
        hi += eps
    return lo, hi


def _sanitize_piece(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in s)


def build_parser(description: str | None = None) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description or "Overlay distribution plots from tree branches.")
    p.add_argument("--files", nargs="+", required=True, help="Input ROOT files.")
    p.add_argument(
        "--input",
        nargs="+",
        default=["tree"],
        help="Tree path(s). If provided once, applies to all files.",
    )
    p.add_argument("--branch", required=True, help="Tree branch to histogram (scalar or std::vector<double>).")
    p.add_argument("--bins", type=int, default=50, help="Number of bins (default: 50).")
    p.add_argument(
        "--range",
        nargs=2,
        type=float,
        metavar=("LO", "HI"),
        default=None,
        help="Optional explicit x-axis range (LO HI). If omitted, inferred from global data.",
    )
    p.add_argument("--x-label", type=str, default=None, help="Optional x-axis label.")
    p.add_argument("--y-label", type=str, default=None, help="Optional y-axis label.")
    p.add_argument("--no-title", action="store_true", help="Disable plot title.")
    p.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional labels for inputs; one per file. Use 'None' or omit to use file stems.",
    )
    p.add_argument(
        "--band",
        nargs="?",
        const="__DEFAULT__",
        default=None,
        help="Enable band underneath curves. Optional value: 'spread' or '<N>sigma'.",
    )
    p.add_argument(
        "--ratio",
        "--ration",
        dest="ratio",
        nargs="?",
        const="full",
        default=None,
        help="Ratio mode: omit for none, use 'full', or 'range:min:max'.",
    )
    p.add_argument("--output-dir", default="examples/output", help="Output directory.")
    p.add_argument("--backend", default="matplotlib", choices=["matplotlib"], help="Plotting backend.")
    p.add_argument("--show", action="store_true", help="Show canvas and block until it is closed.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        _validate_root_files(args.files)
        ratio_enabled, ratio_y_range = parse_ratio_mode(args.ratio)
        input_labels = parse_labels(args.labels, n_files=len(args.files))
        explicit_range = parse_x_range(args.range)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if len(args.input) == 1:
        trees = [args.input[0]] * len(args.files)
    elif len(args.input) != len(args.files):
        print("Error: --input must be provided once or with the same length as --files.", file=sys.stderr)
        return 2
    else:
        trees = args.input

    file_tree_pairs = list(zip(args.files, trees))
    if explicit_range is None:
        x_lo, x_hi = _global_branch_range(file_tree_pairs, args.branch)
    else:
        x_lo, x_hi = explicit_range
    x_range = (x_lo, x_hi)

    band_enabled = args.band is not None
    band_spread: str | None = None
    if band_enabled:
        if args.band == "__DEFAULT__":
            band_spread = None
        else:
            try:
                band_spread = parse_band_spread(args.band)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 2

    colors = [
        "tab:blue",
        "tab:orange",
        "tab:green",
        "tab:red",
        "tab:purple",
        "tab:brown",
        "tab:pink",
        "tab:gray",
        "tab:olive",
        "tab:cyan",
    ]

    objects: list[hist1d] = []
    decorations: list[Decoration] = []
    band_decorations: list[Decoration] = []

    for i, (file_path, tree_path) in enumerate(file_tree_pairs):
        label = input_labels[i] if input_labels is not None else Path(file_path).stem
        color = colors[i % len(colors)]
        h = hist1d_from_tree(
            file_path=file_path,
            tree_path=tree_path,
            branch=args.branch,
            bins=args.bins,
            range=x_range,
            name=label,
        )
        objects.append(h)
        decorations.append(
            Decoration(
                title=None,
                x_label=args.x_label if args.x_label is not None else args.branch,
                y_label=args.y_label if args.y_label is not None else "Entries",
                label=label,
                color=color,
                line_style="-" if i == 0 else "--",
                show_grid=(i == 0),
            )
        )
        band_decorations.append(
            Decoration(
                title=None,
                x_label=None,
                y_label=None,
                label=None,
                color=color,
                fill_color=color,
                band_alpha=0.35,
                show_grid=False,
                show_legend=False,
            )
        )

    if decorations:
        decorations[0] = replace(
            decorations[0],
            title=None if args.no_title else f"{args.branch} distribution",
            show_legend=True,
        )

    fig: Any
    if ratio_enabled:
        fig, (top_ax, ratio_ax) = plot_ratio(
            objects,
            [replace(d, label=None, show_legend=False) for d in decorations],
            backend=args.backend,
        )
        top_ax.cla()
        if band_enabled:
            plot_band(
                objects,
                band_decorations,
                spread=band_spread,
                backend=args.backend,
                figure=fig,
                axis=top_ax,
                show_values=False,
            )
        top_decos = [replace(d, x_label=None) for d in decorations]
        for obj, deco in zip(objects, top_decos):
            plot(obj, decoration=deco, backend=args.backend, figure=fig, axis=top_ax)
        if ratio_y_range is not None:
            ratio_ax.set_ylim(ratio_y_range[0], ratio_y_range[1])
    else:
        if band_enabled:
            fig, top_ax = plot_band(
                objects,
                band_decorations,
                spread=band_spread,
                backend=args.backend,
                show_values=False,
            )
            for obj, deco in zip(objects, decorations):
                plot(obj, decoration=deco, backend=args.backend, figure=fig, axis=top_ax)
        else:
            fig, _ = plot(objects[0], decoration=decorations[0], backend=args.backend)
            for obj, deco in zip(objects[1:], decorations[1:]):
                plot(obj, decoration=deco, backend=args.backend, figure=fig, axis=fig.gca())

    ratio_part = ""
    if ratio_enabled:
        ratio_part = "_ratio_full" if ratio_y_range is None else f"_ratio_range_{ratio_y_range[0]:g}_{ratio_y_range[1]:g}"
    band_part = ""
    if band_enabled:
        band_mode = "default" if band_spread is None else str(band_spread)
        band_part = f"_band_{band_mode}"
    range_part = f"_range_{x_range[0]:g}_{x_range[1]:g}" if explicit_range is not None else ""

    base = f"overlay_dist{ratio_part}{band_part}{range_part}_{_sanitize_piece(args.branch)}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"{base}.png"
    out_svg = out_dir / f"{base}.svg"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    fig.savefig(out_svg, dpi=140, bbox_inches="tight")
    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_svg}")

    if args.show:
        try:
            import matplotlib.pyplot as plt
        except ImportError as exc:
            print(f"Error: matplotlib is required for --show ({exc})", file=sys.stderr)
            return 2
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


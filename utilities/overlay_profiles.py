"""Overlay profile-like ROOT inputs into profile plots (optionally with bands, ratio, and restrictions).

This script is intended to be runnable via absolute paths. It prepends the repo root
to PYTHONPATH by adding it to sys.path at import time.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np

# Allow running this file directly from an absolute path.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from valplot import Decoration, plot, plot_band, plot_ratio
from valplot.io.root import (
    band_from_tree,
    profile_from_tree,
    restricted_band_from_tree,
    restricted_profile_from_tree,
)


_SIGMA_RE = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)sigma$")


def parse_xy_spec(raw: str) -> tuple[str, str]:
    """Parse 'x:y' plot spec into (x_branch, y_branch)."""
    parts = [p.strip() for p in raw.split(":")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid --plot entry '{raw}'. Expected format 'x:y'.")
    return parts[0], parts[1]


def parse_restrict(raw: str) -> tuple[str, float, float]:
    """Parse 'branch:lo:hi' into (branch, lo, hi)."""
    parts = [p.strip() for p in raw.split(":")]
    if len(parts) != 3 or not parts[0]:
        raise ValueError(f"Invalid --restrict entry '{raw}'. Expected 'branch:lo:hi'.")
    branch = parts[0]
    lo = float(parts[1])
    hi = float(parts[2])
    if not (np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("--restrict lo/hi must be finite numbers.")
    if lo == hi:
        eps = 0.5 if lo == 0.0 else abs(lo) * 0.01
        lo -= eps
        hi += eps
    if lo > hi:
        lo, hi = hi, lo
    return branch, lo, hi


def parse_band_spread(raw: str | None) -> str | None:
    """Parse band spread token into valplot plot_band spread value.

    - None => default (use min/max envelope mode)
    - 'spread' => explicit min/max envelope mode
    - '<N>sigma' => sigma mode supported by plot_band
    """
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "spread":
        return "spread"
    if _SIGMA_RE.match(raw):
        return raw
    raise ValueError(f"Invalid band spread token '{raw}'. Expected 'spread' or '<N>sigma'.")


def parse_ratio_mode(raw: str | None) -> tuple[bool, tuple[float, float] | None]:
    """Parse the --ratio argument.

    Returns:
      (enabled, y_range_for_ratio_or_None)

    Accepted values:
      - None => ratio disabled
      - "full" => ratio enabled, no y-axis restriction
      - "range:min_val:max_val" => ratio enabled, set ratio y-axis to [min_val, max_val]
    """
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


def parse_labels(raw: list[str] | None, n_files: int) -> list[str] | None:
    """Parse --labels into a list matching the number of input files."""
    if raw is None:
        return None
    if len(raw) == 1 and raw[0].lower() == "none":
        return None
    if len(raw) != n_files:
        raise ValueError(f"--labels length must be {n_files} (or 'None'); got {len(raw)}.")
    return raw


def parse_x_range(raw: list[float] | None) -> tuple[float, float] | None:
    """Parse --range LO HI into (lo, hi)."""
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


def _global_branch_range(
    file_tree_pairs: list[tuple[str, str]],
    branch: str,
) -> tuple[float, float]:
    """Compute global (min, max) for branch across inputs."""
    # We import uproot lazily (only used when we actually run ROOT IO).
    from valplot.io.root.histograms import _import_uproot

    uproot = _import_uproot()
    chunks: list[np.ndarray] = []
    for file_path, tree_path in file_tree_pairs:
        with uproot.open(file_path) as root_file:
            tree = root_file[tree_path]
            arrays = tree.arrays([branch], library="np")
            values = np.asarray(arrays[branch], dtype=float)
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
        return lo - eps, hi + eps
    return lo, hi


def build_parser(description: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description or "Overlay ROOT profile-like plots (profiles, bands, ratio, restrictions).",
    )

    parser.add_argument("--files", nargs="+", required=True, help="Input ROOT files.")
    parser.add_argument(
        "--input",
        nargs="+",
        default=["tree"],
        help="Tree name(s) or histogram object name(s) (only 'tree' is supported for now). If provided once, applies to all --files.",
    )
    parser.add_argument("--plot", type=str, required=True, help="Plot spec like 'x:y' (only one allowed).")

    parser.add_argument(
        "--band",
        nargs="?",
        const="__DEFAULT__",
        default=None,
        help="Enable band underneath profiles. Optional value: 'spread' or '<N>sigma'. If omitted, uses default mode (spread).",
    )
    parser.add_argument(
        "--ratio",
        "--ration",
        dest="ratio",
        nargs="?",
        const="full",
        default=None,
        help=(
            "Draw ratio panel underneath. Accepted values: "
            "'full' (default when provided without value) or 'range:min_val:max_val'. "
            "If omitted, ratio is not drawn."
        ),
    )
    parser.add_argument(
        "--restrict",
        type=str,
        default=None,
        help="Optional restriction for restricted profiles/bands: 'branch:lo:hi'.",
    )
    parser.add_argument(
        "--x-label",
        type=str,
        default=None,
        help="Optional x-axis label (supports LaTeX/mathtext, e.g. '$\\alpha$').",
    )
    parser.add_argument(
        "--y-label",
        type=str,
        default=None,
        help="Optional y-axis label (supports LaTeX/mathtext, e.g. '$\\mu$').",
    )
    parser.add_argument(
        "--no-title",
        action="store_true",
        help="Turn off the title on the top panel.",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help=(
            "Optional labels for the plots, one per input file. "
            "If omitted (or set to 'None'), uses the file stem. "
            "If provided, its length must equal the number of --files."
        ),
    )
    parser.add_argument(
        "--range",
        nargs=2,
        type=float,
        metavar=("LO", "HI"),
        default=None,
        help="Optional explicit x-axis range (LO HI). If omitted, range is inferred from the global data spread.",
    )
    parser.add_argument(
        "--output-dir",
        default="examples/output",
        help="Directory to store rendered plots (default: examples/output).",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=50,
        help="Number of bins for x (default: 50).",
    )
    parser.add_argument("--backend", default="matplotlib", choices=["matplotlib"], help="Plotting backend.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_root_files(args.files)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if len(args.input) == 1:
        inputs = [args.input[0]] * len(args.files)
    elif len(args.input) != len(args.files):
        print("Error: --input must be provided once or with the same length as --files.", file=sys.stderr)
        return 2
    else:
        inputs = args.input

    try:
        x_branch, y_branch = parse_xy_spec(args.plot)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    restrict_spec = None
    if args.restrict is not None:
        try:
            branch, lo, hi = parse_restrict(args.restrict)
            restrict_spec = (branch, lo, hi)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2

    try:
        ratio_enabled, ratio_y_range = parse_ratio_mode(args.ratio)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

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

    file_tree_pairs = list(zip(args.files, inputs))
    try:
        input_labels = parse_labels(args.labels, n_files=len(args.files))
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

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

    try:
        explicit_range = parse_x_range(args.range)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if explicit_range is None:
        x_lo, x_hi = _global_branch_range(file_tree_pairs, x_branch)
    else:
        x_lo, x_hi = explicit_range
    bins = args.bins
    range_x = (x_lo, x_hi)

    profiles = []
    bands = []
    profile_decos: list[Decoration] = []
    band_decos: list[Decoration] = []

    for i, (file_path, tree_path) in enumerate(file_tree_pairs):
        label = input_labels[i] if input_labels is not None else Path(file_path).stem
        color = colors[i % len(colors)]

        if restrict_spec is None:
            prof = profile_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=x_branch,
                y_branch=y_branch,
                bins=bins,
                range=range_x,
                name=label,
            )
            if band_enabled:
                band_obj = band_from_tree(
                    file_path=file_path,
                    tree_path=tree_path,
                    x_branch=x_branch,
                    y_branch=y_branch,
                    bins=bins,
                    range=range_x,
                    name=label,
                )
        else:
            r_branch, r_lo, r_hi = restrict_spec
            prof = restricted_profile_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=x_branch,
                y_branch=y_branch,
                restriction_branch=r_branch,
                restriction_range=(r_lo, r_hi),
                bins=bins,
                range=range_x,
                name=label,
            )
            if band_enabled:
                band_obj = restricted_band_from_tree(
                    file_path=file_path,
                    tree_path=tree_path,
                    x_branch=x_branch,
                    y_branch=y_branch,
                    restriction_branch=r_branch,
                    restriction_range=(r_lo, r_hi),
                    bins=bins,
                    range=range_x,
                    name=label,
                )

        profiles.append(prof)
        if band_enabled:
            bands.append(band_obj)

        show_grid = i == 0
        profile_decos.append(
            Decoration(
                title=None,
                x_label=args.x_label if args.x_label is not None else x_branch,
                y_label=args.y_label if args.y_label is not None else y_branch,
                label=label,
                color=color,
                line_style="-" if i == 0 else "--",
                marker="o",
                marker_size=2.5,
                show_grid=show_grid,
            )
        )
        if band_enabled:
            band_decos.append(
                Decoration(
                    title=None,
                    x_label=None,
                    y_label=None,
                    label=None,
                    color=color,
                    fill_color=color,
                    band_alpha=0.35,
                    line_style="-",
                    show_grid=False,
                    show_legend=False,
                )
            )

    # Ensure only the first profile deco carries the title.
    if profile_decos:
        profile_decos[0] = replace(
            profile_decos[0],
            title=None if args.no_title else f"{y_branch} vs {x_branch}",
            show_legend=True,
        )

    written: list[Path] = []

    fig: Any
    if ratio_enabled:
        fig, (top_ax, ratio_ax) = plot_ratio(
            profiles,
            # Suppress legend/labels on ratio panel; we redraw top panel below anyway.
            [replace(d, label=None, show_legend=False) for d in profile_decos],
            backend=args.backend,
        )
        top_ax.cla()

        if band_enabled:
            plot_band(
                bands,
                band_decos,
                spread=band_spread,
                backend=args.backend,
                figure=fig,
                axis=top_ax,
                show_values=False,
            )

        # Redraw profiles (without top-panel xlabel).
        top_decos = [replace(d, x_label=None) for d in profile_decos]
        for prof, deco in zip(profiles, top_decos):
            plot(prof, decoration=deco, backend=args.backend, figure=fig, axis=top_ax)

        if ratio_y_range is not None:
            ratio_ax.set_ylim(ratio_y_range[0], ratio_y_range[1])
    else:
        if band_enabled:
            fig, top_ax = plot_band(
                bands,
                band_decos,
                spread=band_spread,
                backend=args.backend,
                show_values=False,
            )
            for prof, deco in zip(profiles, profile_decos):
                plot(prof, decoration=deco, backend=args.backend, figure=fig, axis=top_ax)
        else:
            fig, _ = plot(
                profiles[0],
                decoration=profile_decos[0],
                backend=args.backend,
            )
            for prof, deco in zip(profiles[1:], profile_decos[1:]):
                plot(prof, decoration=deco, backend=args.backend, figure=fig, axis=fig.gca())

    # Output names
    ratio_part = ""
    if ratio_enabled:
        ratio_part = "_ratio_full" if ratio_y_range is None else f"_ratio_range_{ratio_y_range[0]:g}_{ratio_y_range[1]:g}"
    band_part = ""
    if band_enabled:
        band_mode = "default" if band_spread is None else str(band_spread)
        band_part = f"_band_{band_mode}"
    restrict_part = ""
    if restrict_spec is not None:
        r_branch, r_lo, r_hi = restrict_spec
        restrict_part = f"_restrict_{r_branch}_{r_lo:g}_{r_hi:g}"

    def _sanitize_piece(s: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in s)

    base = (
        f"overlay_profiles{ratio_part}{band_part}{restrict_part}"
        f"_{_sanitize_piece(x_branch)}_{_sanitize_piece(y_branch)}"
    )

    out_png = out_dir / f"{base}.png"
    out_svg = out_dir / f"{base}.svg"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    fig.savefig(out_svg, dpi=140, bbox_inches="tight")
    written.extend([out_png, out_svg])

    for p in written:
        print(f"Wrote: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


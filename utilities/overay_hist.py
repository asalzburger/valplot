"""Overlay 1D histogram-like objects from ROOT files.

Supported kinds:
- hist1d
- efficiency

For now, only `.root` inputs are supported.
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

from valplot import Decoration, efficiency as efficiency_obj, hist1d, plot, plot_band, plot_ratio
from valplot.io.root import read_hist1d


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


def parse_eff_input(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("Invalid efficiency --input entry ''. Expected TEfficiency object name.")
    if ":" in raw:
        raise ValueError(f"Invalid efficiency --input entry '{raw}'. Expected TEfficiency object name.")
    return raw


def _validate_root_files(files: list[str]) -> None:
    non_root = [f for f in files if not f.endswith(".root")]
    if non_root:
        bad = ", ".join(non_root[:5])
        raise ValueError(f"All --files must end with '.root'. Got: {bad}")


def _sanitize_piece(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in s)


def build_parser(description: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description or "Overlay 1D ROOT histogram-like plots (hist1d/efficiency, ratio, band).",
    )
    parser.add_argument("--files", nargs="+", required=True, help="Input ROOT files.")
    parser.add_argument(
        "--kind",
        choices=["hist1d", "efficiency"],
        default="hist1d",
        help="Plot kind to build from ROOT objects (default: hist1d).",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help=(
            "Object name(s). For kind=hist1d: TH1 object path(s). "
            "For kind=efficiency: TEfficiency object path(s). "
            "If provided once, applies to all files."
        ),
    )
    parser.add_argument(
        "--band",
        nargs="?",
        const="__DEFAULT__",
        default=None,
        help="Enable band underneath curves. Optional value: 'spread' or '<N>sigma'.",
    )
    parser.add_argument(
        "--ratio",
        "--ration",
        dest="ratio",
        nargs="?",
        const="full",
        default=None,
        help="Ratio mode: omit for none, use 'full', or 'range:min:max'.",
    )
    parser.add_argument("--x-label", type=str, default=None, help="Optional x-axis label.")
    parser.add_argument("--y-label", type=str, default=None, help="Optional y-axis label.")
    parser.add_argument("--no-title", action="store_true", help="Disable top title.")
    parser.add_argument(
        "--labels",
        nargs="*",
        default=None,
        help="Optional labels for inputs; one per file. Use 'None' or omit to use file stems.",
    )
    parser.add_argument("--output-dir", default="examples/output", help="Output directory.")
    parser.add_argument("--backend", default="matplotlib", choices=["matplotlib"], help="Plotting backend.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_root_files(args.files)
        ratio_enabled, ratio_y_range = parse_ratio_mode(args.ratio)
        input_labels = parse_labels(args.labels, n_files=len(args.files))
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

    objects: list[hist1d | efficiency_obj] = []
    ratio_objects: list[hist1d] = []
    decorations: list[Decoration] = []
    band_decorations: list[Decoration] = []

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

    for i, (file_path, input_item) in enumerate(zip(args.files, inputs)):
        label = input_labels[i] if input_labels is not None else Path(file_path).stem
        color = colors[i % len(colors)]

        if args.kind == "hist1d":
            h = read_hist1d(file_path, input_item)
            h = hist1d(edges=h.edges, counts=h.counts, errors=h.errors, name=label)
            objects.append(h)
            ratio_objects.append(h)
        else:
            try:
                teff_obj = parse_eff_input(input_item)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 2
            try:
                h_eff = read_hist1d(file_path, teff_obj)
            except Exception as e:
                print(f"Error: failed to read TEfficiency '{teff_obj}' from '{file_path}': {e}", file=sys.stderr)
                return 2
            if np.any(h_eff.counts < -1e-12) or np.any(h_eff.counts > 1.0 + 1e-12):
                print(
                    f"Error: object '{teff_obj}' does not look like a TEfficiency-derived histogram (values outside [0,1]).",
                    file=sys.stderr,
                )
                return 2
            eff = efficiency_obj(
                edges=h_eff.edges,
                passed=np.clip(h_eff.counts, 0.0, 1.0),
                total=np.ones_like(h_eff.counts, dtype=float),
                errors=h_eff.errors,
                name=label,
            )
            objects.append(eff)
            # Ratio/band helper path: map efficiency values/errors to a hist1d-like container.
            ratio_objects.append(hist1d(edges=eff.edges, counts=eff.values, errors=eff.errors, name=label))

        decorations.append(
            Decoration(
                title=None,
                x_label=args.x_label,
                y_label=args.y_label if args.y_label is not None else ("Efficiency" if args.kind == "efficiency" else "Entries"),
                label=label,
                color=color,
                line_style="-" if i == 0 else "--",
                marker="o",
                marker_size=2.5,
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
                line_style="-",
                show_grid=False,
                show_legend=False,
            )
        )

    if decorations:
        decorations[0] = replace(
            decorations[0],
            title=None if args.no_title else f"{args.kind} overlay",
            show_legend=True,
        )

    if ratio_enabled:
        fig, (top_ax, ratio_ax) = plot_ratio(
            ratio_objects,
            [replace(d, label=None, show_legend=False) for d in decorations],
            backend=args.backend,
        )
        top_ax.cla()
        if band_enabled:
            plot_band(
                ratio_objects,
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
                ratio_objects,
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

    base = f"overlay_hist_{args.kind}{ratio_part}{band_part}_{_sanitize_piece(inputs[0])}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"{base}.png"
    out_svg = out_dir / f"{base}.svg"
    fig.savefig(out_png, dpi=140, bbox_inches="tight")
    fig.savefig(out_svg, dpi=140, bbox_inches="tight")
    print(f"Wrote: {out_png}")
    print(f"Wrote: {out_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


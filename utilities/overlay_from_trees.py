"""Overlay tree-derived plots (hist1d, profile, restricted_profile, scatter, band) from multiple ROOT files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import uproot

from valplot.io.root import (
    band_from_tree,
    hist1d_from_tree,
    profile_from_tree,
    restricted_profile_from_tree,
    scatter_from_tree,
)


@dataclass(frozen=True)
class PlotInstruction:
    kind: str
    ratio: bool
    band: bool
    x_branch: str
    y_branch: str | None = None
    restriction_branch: str | None = None
    restriction_range: tuple[float, float] | None = None


_SUPPORTED_KINDS = {"hist1d", "profile", "restricted_profile", "scatter", "band"}


def parse_plot_instruction(raw: str) -> PlotInstruction:
    """Parse plot instruction string.

    Formats:
      hist1d[:ratio][:band]:x_branch
      profile[:ratio][:band]:x_branch:y_branch
      restricted_profile[:ratio][:band]:x_branch:y_branch:restriction_branch:lo:hi
      scatter:x_branch:y_branch
      band:x_branch:y_branch
    """
    parts = [item.strip() for item in raw.split(":")]
    if len(parts) < 2:
        raise ValueError(f"Invalid plot instruction '{raw}'.")

    kind = parts[0].lower()
    if kind not in _SUPPORTED_KINDS:
        supported = ", ".join(sorted(_SUPPORTED_KINDS))
        raise ValueError(f"Unsupported plot kind in '{raw}'. Expected one of: {supported}.")

    if kind == "hist1d":
        options = [item.lower() for item in parts[1:-1] if item]
        x_branch = parts[-1]
        y_branch = None
        restriction_branch = None
        restriction_range = None
    elif kind == "restricted_profile":
        if len(parts) < 7:
            raise ValueError(
                f"restricted_profile requires x:y:restriction_branch:lo:hi, got '{raw}'."
            )
        options = [item.lower() for item in parts[1:-5] if item]
        x_branch = parts[-5]
        y_branch = parts[-4]
        restriction_branch = parts[-3]
        try:
            lo = float(parts[-2])
            hi = float(parts[-1])
        except ValueError as e:
            raise ValueError(
                f"restricted_profile restriction range must be numeric (lo:hi), got '{raw}'."
            ) from e
        restriction_range = (lo, hi)
    elif kind == "scatter":
        if len(parts) < 3:
            raise ValueError(f"scatter requires x_branch:y_branch, got '{raw}'.")
        options = [item.lower() for item in parts[1:-2] if item]
        x_branch = parts[-2]
        y_branch = parts[-1]
        restriction_branch = None
        restriction_range = None
    else:
        if len(parts) < 3:
            raise ValueError(f"{kind} requires x_branch:y_branch, got '{raw}'.")
        options = [item.lower() for item in parts[1:-2] if item]
        x_branch = parts[-2]
        y_branch = parts[-1]
        restriction_branch = None
        restriction_range = None

    ratio = "ratio" in options
    use_band = "band" in options or kind == "band"

    if kind in {"scatter", "band"} and ratio:
        raise ValueError(f"ratio option is not supported for '{kind}' instructions.")
    if kind == "scatter" and use_band:
        raise ValueError("scatter instructions cannot use band mode.")

    return PlotInstruction(
        kind=kind,
        ratio=ratio,
        band=use_band,
        x_branch=x_branch,
        y_branch=y_branch,
        restriction_branch=restriction_branch,
        restriction_range=restriction_range,
    )


def _sanitize_filename_piece(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _global_branch_range(
    file_tree_pairs: list[tuple[str, str]], branch: str
) -> tuple[float, float]:
    chunks: list[np.ndarray] = []
    for file_path, tree_path in file_tree_pairs:
        with uproot.open(file_path) as root_file:
            arr = np.asarray(root_file[tree_path].arrays([branch], library="np")[branch], dtype=float)
            chunks.append(arr)

    if not chunks:
        raise ValueError("No input data found.")
    values = np.concatenate(chunks)
    if values.size == 0:
        raise ValueError(f"Branch '{branch}' has no entries.")

    lo = float(np.min(values))
    hi = float(np.max(values))
    if not np.isfinite(lo) or not np.isfinite(hi):
        raise ValueError(f"Branch '{branch}' contains non-finite values.")
    if lo == hi:
        eps = 0.5 if lo == 0.0 else abs(lo) * 0.01
        return lo - eps, hi + eps
    return lo, hi


def _build_objects(
    spec: PlotInstruction,
    file_tree_pairs: list[tuple[str, str]],
    bins: int,
) -> tuple[list[Any], str, str]:
    if spec.kind != "scatter":
        x_lo, x_hi = _global_branch_range(file_tree_pairs, spec.x_branch)
    else:
        x_lo, x_hi = (0.0, 1.0)

    objects: list[Any] = []
    for file_path, tree_path in file_tree_pairs:
        file_label = Path(file_path).stem
        if spec.kind == "hist1d":
            obj = hist1d_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                branch=spec.x_branch,
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        elif spec.kind == "profile":
            obj = profile_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=spec.x_branch,
                y_branch=spec.y_branch or "",
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        elif spec.kind == "restricted_profile":
            if spec.restriction_branch is None or spec.restriction_range is None:
                raise ValueError(
                    "restricted_profile requires restriction_branch and restriction_range."
                )
            obj = restricted_profile_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=spec.x_branch,
                y_branch=spec.y_branch or "",
                restriction_branch=spec.restriction_branch,
                restriction_range=spec.restriction_range,
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        elif spec.kind == "scatter":
            obj = scatter_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=spec.x_branch,
                y_branch=spec.y_branch or "",
                name=file_label,
            )
        else:
            obj = band_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=spec.x_branch,
                y_branch=spec.y_branch or "",
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        objects.append(obj)

    if spec.kind == "hist1d":
        title = f"hist1d: {spec.x_branch}"
        y_label = "Entries"
    elif spec.kind == "profile":
        title = f"profile: {spec.y_branch} vs {spec.x_branch}"
        y_label = spec.y_branch or "Mean"
    elif spec.kind == "restricted_profile":
        r = spec.restriction_range or (0, 0)
        title = f"restricted_profile: {spec.y_branch} vs {spec.x_branch} ({spec.restriction_branch} ∈ [{r[0]},{r[1]}])"
        y_label = spec.y_branch or "Mean"
    elif spec.kind == "scatter":
        title = f"scatter: {spec.y_branch} vs {spec.x_branch}"
        y_label = spec.y_branch or "y"
    else:
        title = f"band: {spec.y_branch} vs {spec.x_branch}"
        y_label = spec.y_branch or "y"
    return objects, title, y_label


def overlay_from_trees(
    file_tree_pairs: list[tuple[str, str]],
    specs: list[PlotInstruction],
    *,
    bins: int = 50,
    output_dir: Path | str,
    backend: str = "matplotlib",
) -> list[Path]:
    """Build overlay plots from tree-derived objects and save to output_dir.

    Returns list of written file paths.
    """
    try:
        import plotval
    except ImportError:
        import valplot as plotval

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

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

    for spec in specs:
        objects, title, y_label = _build_objects(spec, file_tree_pairs, bins=bins)
        decorations = []
        for i, obj in enumerate(objects):
            decorations.append(
                plotval.Decoration(
                    title=title if i == 0 else None,
                    x_label=spec.x_branch if i == 0 else None,
                    y_label=y_label if i == 0 else None,
                    label=getattr(obj, "name", None),
                    color=colors[i % len(colors)],
                    line_style="-" if i == 0 else "--",
                    marker="o" if spec.kind in {"profile", "restricted_profile", "scatter"} else None,
                    marker_size=3.0 if spec.kind in {"profile", "restricted_profile", "scatter"} else None,
                    band_alpha=0.5,
                    show_grid=True if i == 0 else False,
                )
            )

        if spec.band:
            fig, _ = plotval.plot_band(objects, decorations, backend=backend)
        elif spec.ratio:
            fig, _ = plotval.plot_ratio(objects, decorations, backend=backend)
        elif spec.kind == "scatter":
            fig, _ = plotval.plot_scatter(
                objects[0], decoration=decorations[0], backend=backend
            )
            for obj, deco in zip(objects[1:], decorations[1:]):
                plotval.plot_scatter(obj, decoration=deco, backend=backend, axis=fig.gca())
        else:
            fig, _ = plotval.plot(
                objects[0], decoration=decorations[0], backend=backend
            )
            for obj, deco in zip(objects[1:], decorations[1:]):
                plotval.plot(obj, decoration=deco, backend=backend, axis=fig.gca())

        ratio_part = "_ratio" if spec.ratio else ""
        band_part = "_band" if spec.band else ""
        if spec.kind == "hist1d":
            filename = f"overlay_hist1d{ratio_part}{band_part}_{_sanitize_filename_piece(spec.x_branch)}.png"
        elif spec.kind == "profile":
            filename = (
                f"overlay_profile{ratio_part}{band_part}_"
                f"{_sanitize_filename_piece(spec.x_branch)}_{_sanitize_filename_piece(spec.y_branch or "")}.png"
            )
        elif spec.kind == "restricted_profile":
            filename = (
                f"overlay_restricted_profile{ratio_part}{band_part}_"
                f"{_sanitize_filename_piece(spec.x_branch)}_{_sanitize_filename_piece(spec.y_branch or "")}.png"
            )
        elif spec.kind == "scatter":
            filename = (
                f"overlay_scatter_"
                f"{_sanitize_filename_piece(spec.x_branch)}_{_sanitize_filename_piece(spec.y_branch or "")}.png"
            )
        else:
            filename = (
                f"overlay_band_"
                f"{_sanitize_filename_piece(spec.x_branch)}_{_sanitize_filename_piece(spec.y_branch or "")}.png"
            )
        out_path = output_dir / filename
        fig.savefig(out_path, dpi=140, bbox_inches="tight")
        written.append(out_path)

    return written


def build_parser(description: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description or "Overlay ROOT tree-derived plots from multiple files.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="List of ROOT files.",
    )
    parser.add_argument(
        "--trees",
        nargs="+",
        required=True,
        help="List of tree names; must match --files length 1:1.",
    )
    parser.add_argument(
        "--plots",
        nargs="+",
        required=True,
        help=(
            "Plot instructions, e.g. "
            "'profile:ratio:x:y' 'profile:x:y' 'profile:band:x:y' "
            "'hist1d:x' 'hist1d:ratio:x' 'hist1d:band:x' "
            "'restricted_profile:ratio:x:y:z:-4:4' "
            "'scatter:x:y' 'band:x:y'."
        ),
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=50,
        help="Number of bins for histogram/profile/band plots (default: 50).",
    )
    parser.add_argument(
        "--output-dir",
        default="examples/output",
        help="Directory to store rendered plots (default: examples/output).",
    )
    parser.add_argument(
        "--backend",
        default="matplotlib",
        choices=["matplotlib"],
        help="Plotting backend (default: matplotlib).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if len(args.files) != len(args.trees):
        parser.error("--files and --trees must have the same length.")

    file_tree_pairs = list(zip(args.files, args.trees))
    specs = [parse_plot_instruction(raw) for raw in args.plots]

    written = overlay_from_trees(
        file_tree_pairs,
        specs,
        bins=args.bins,
        output_dir=args.output_dir,
        backend=args.backend,
    )

    print("Wrote plots:")
    for path in written:
        print(f" - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

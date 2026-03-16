"""CLI demo: overlay tree-derived plots from multiple ROOT files."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
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

from valplot.io.root import hist1d_from_tree, profile_from_tree


@dataclass(frozen=True)
class PlotInstruction:
    kind: str  # "hist1" or "profile"
    ratio: bool
    x_branch: str
    y_branch: str | None = None


def _parse_plot_instruction(raw: str) -> PlotInstruction:
    parts = raw.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid plot instruction '{raw}'.")

    kind = parts[0].strip().lower()
    if kind not in {"hist1", "profile"}:
        raise ValueError(f"Unsupported plot kind in '{raw}'. Expected 'hist1' or 'profile'.")

    ratio = False
    idx = 1
    if idx < len(parts) and parts[idx].strip().lower() == "ratio":
        ratio = True
        idx += 1

    if kind == "hist1":
        if len(parts) != idx + 1:
            raise ValueError(f"Invalid hist1 instruction '{raw}'. Expected hist1[:ratio]:<branch>.")
        return PlotInstruction(kind="hist1", ratio=ratio, x_branch=parts[idx].strip())

    if len(parts) != idx + 2:
        raise ValueError(f"Invalid profile instruction '{raw}'. Expected profile[:ratio]:<x_branch>:<y_branch>.")
    return PlotInstruction(
        kind="profile",
        ratio=ratio,
        x_branch=parts[idx].strip(),
        y_branch=parts[idx + 1].strip(),
    )


def _sanitize_filename_piece(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _global_branch_range(file_tree_pairs: list[tuple[str, str]], branch: str) -> tuple[float, float]:
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


def _build_histograms(
    spec: PlotInstruction,
    file_tree_pairs: list[tuple[str, str]],
    bins: int,
) -> tuple[list[plotval.hist1d | plotval.profile], str, str]:
    x_lo, x_hi = _global_branch_range(file_tree_pairs, spec.x_branch)

    objects: list[plotval.hist1d | plotval.profile] = []
    for file_path, tree_path in file_tree_pairs:
        file_label = Path(file_path).stem
        if spec.kind == "hist1":
            obj = hist1d_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                branch=spec.x_branch,
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        else:
            obj = profile_from_tree(
                file_path=file_path,
                tree_path=tree_path,
                x_branch=spec.x_branch,
                y_branch=spec.y_branch or "",
                bins=bins,
                range=(x_lo, x_hi),
                name=file_label,
            )
        objects.append(obj)

    if spec.kind == "hist1":
        title = f"hist1: {spec.x_branch}"
        y_label = "Entries"
    else:
        title = f"profile: {spec.y_branch} vs {spec.x_branch}"
        y_label = spec.y_branch or "Mean"
    return objects, title, y_label


def _overlay_and_save(
    spec: PlotInstruction,
    histograms: list[plotval.hist1d | plotval.profile],
    title: str,
    y_label: str,
    output_dir: Path,
) -> Path:
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
    decorations = []
    for i, histogram in enumerate(histograms):
        decorations.append(
            plotval.Decoration(
                title=title if i == 0 else None,
                x_label=spec.x_branch if i == 0 else None,
                y_label=y_label if i == 0 else None,
                label=histogram.name,
                color=colors[i % len(colors)],
                line_style="-" if i == 0 else "--",
                marker="o" if spec.kind == "profile" else None,
                marker_size=3.0 if spec.kind == "profile" else None,
                show_grid=True if i == 0 else False,
            )
        )

    if spec.ratio:
        fig, _ = plotval.plot_ratio(histograms, decorations, backend="matplotlib")
    else:
        fig, _ = plotval.plot(histograms[0], decoration=decorations[0], backend="matplotlib")
        for histogram, deco in zip(histograms[1:], decorations[1:]):
            plotval.plot(histogram, decoration=deco, backend="matplotlib", axis=fig.gca())

    ratio_part = "_ratio" if spec.ratio else ""
    if spec.kind == "hist1":
        filename = f"overlay_hist1{ratio_part}_{_sanitize_filename_piece(spec.x_branch)}.png"
    else:
        filename = (
            f"overlay_profile{ratio_part}_"
            f"{_sanitize_filename_piece(spec.x_branch)}_{_sanitize_filename_piece(spec.y_branch or '')}.png"
        )
    out_path = output_dir / filename
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    return out_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Overlay ROOT tree-derived plots from multiple files.",
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
            "'profile:ratio:x:y' 'profile:x:y' 'hist1:d0' 'hist1:ratio:d0'."
        ),
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=50,
        help="Number of bins used for tree-derived plots (default: 50).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "examples" / "output"),
        help="Directory to store rendered plots.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if len(args.files) != len(args.trees):
        parser.error("--files and --trees must have the same length.")

    file_tree_pairs = list(zip(args.files, args.trees))
    specs = [_parse_plot_instruction(raw) for raw in args.plots]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in specs:
        histograms, title, y_label = _build_histograms(spec, file_tree_pairs, bins=args.bins)
        out_path = _overlay_and_save(spec, histograms, title, y_label, output_dir)
        written.append(out_path)

    print("Wrote plots:")
    for path in written:
        print(f" - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

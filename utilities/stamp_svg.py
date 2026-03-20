"""Stamp one SVG onto another at a fractional location/size."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def _parse_length(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"^\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)", value)
    if not match:
        return None
    return float(match.group(1))


def _svg_dimensions(svg_root: ET.Element) -> tuple[float, float]:
    width = _parse_length(svg_root.get("width"))
    height = _parse_length(svg_root.get("height"))
    if width is not None and height is not None:
        return width, height

    view_box = svg_root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])

    raise ValueError("Could not determine SVG dimensions (width/height or viewBox required).")


def _build_stamped_element(
    stamp_root: ET.Element,
    x: float,
    y: float,
    target_width: float,
) -> ET.Element:
    stamp_width, stamp_height = _svg_dimensions(stamp_root)
    target_height = target_width * (stamp_height / stamp_width)

    stamped = ET.Element(stamp_root.tag)
    stamped.attrib.update(stamp_root.attrib)
    stamped.set("x", str(x))
    stamped.set("y", str(y))
    stamped.set("width", str(target_width))
    stamped.set("height", str(target_height))

    for child in list(stamp_root):
        stamped.append(deepcopy(child))
    return stamped


def stamp_svg(
    input_svg: Path,
    stamp_svg_path: Path,
    output_svg: Path,
    location: tuple[float, float],
    size_fraction: float,
) -> None:
    if not (0.0 <= location[0] <= 1.0 and 0.0 <= location[1] <= 1.0):
        raise ValueError("location fractions must be in [0, 1]")
    if size_fraction <= 0.0:
        raise ValueError("size fraction must be > 0")

    base_tree = ET.parse(input_svg)
    base_root = base_tree.getroot()
    base_width, base_height = _svg_dimensions(base_root)

    stamp_tree = ET.parse(stamp_svg_path)
    stamp_root = stamp_tree.getroot()

    x = float(location[0] * base_width)
    y = float(location[1] * base_height)
    target_width = float(size_fraction * base_width)

    stamped = _build_stamped_element(stamp_root, x=x, y=y, target_width=target_width)
    base_root.append(stamped)

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    base_tree.write(output_svg, encoding="utf-8", xml_declaration=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stamp an SVG file onto another SVG.")
    parser.add_argument("--input", required=True, help="Input plot SVG file.")
    parser.add_argument("--stamp", required=True, help="Stamp SVG file.")
    # Keep compatibility with user-provided typo while supporting the correct spelling.
    parser.add_argument("--output", "--outout", dest="output", required=True, help="Output stamped SVG file.")
    parser.add_argument(
        "--location",
        nargs=2,
        type=float,
        required=True,
        metavar=("X", "Y"),
        help="Top-left stamp location as fractions of input width/height.",
    )
    parser.add_argument(
        "--size",
        type=float,
        required=True,
        help="Stamp width as a fraction of input SVG width.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stamp_svg(
        input_svg=Path(args.input),
        stamp_svg_path=Path(args.stamp),
        output_svg=Path(args.output),
        location=(args.location[0], args.location[1]),
        size_fraction=args.size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

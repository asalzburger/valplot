from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from utilities.stamp_svg import main, stamp_svg


def _write_svg(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_stamp_svg_function(tmp_path: Path):
    input_svg = tmp_path / "plot.svg"
    stamp = tmp_path / "stamp.svg"
    out = tmp_path / "out.svg"

    _write_svg(
        input_svg,
        """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100"/></svg>""",
    )
    _write_svg(
        stamp,
        """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><circle cx="10" cy="5" r="4"/></svg>""",
    )

    stamp_svg(input_svg, stamp, out, location=(0.15, 0.3), size_fraction=0.2)

    tree = ET.parse(out)
    root = tree.getroot()
    children = list(root)
    stamped = children[-1]
    assert stamped.attrib["x"] == "30.0"
    assert stamped.attrib["y"] == "30.0"
    assert stamped.attrib["width"] == "40.0"
    assert stamped.attrib["height"] == "20.0"


def test_stamp_svg_cli_outout_alias(tmp_path: Path):
    input_svg = tmp_path / "plot.svg"
    stamp = tmp_path / "stamp.svg"
    out = tmp_path / "stamped.svg"

    _write_svg(
        input_svg,
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200"/></svg>""",
    )
    _write_svg(
        stamp,
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><path d="M0,0 L20,10"/></svg>""",
    )

    exit_code = main(
        [
            "--input",
            str(input_svg),
            "--stamp",
            str(stamp),
            "--outout",
            str(out),
            "--location",
            "0.25",
            "0.5",
            "--size",
            "0.1",
        ]
    )
    assert exit_code == 0
    assert out.exists()


def test_stamp_svg_rejects_invalid_fraction(tmp_path: Path):
    input_svg = tmp_path / "plot.svg"
    stamp = tmp_path / "stamp.svg"
    out = tmp_path / "out.svg"

    _write_svg(
        input_svg,
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>""",
    )
    _write_svg(
        stamp,
        """<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>""",
    )

    with pytest.raises(ValueError):
        stamp_svg(input_svg, stamp, out, location=(1.2, 0.5), size_fraction=0.2)

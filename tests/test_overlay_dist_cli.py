import subprocess
import sys
from pathlib import Path

import pytest

from utilities.overlay_dist import parse_band_spread, parse_labels, parse_ratio_mode, parse_x_range


@pytest.mark.parametrize("token,expected", [(None, None), ("spread", "spread"), ("2sigma", "2sigma"), ("1.5sigma", "1.5sigma")])
def test_parse_band_spread(token, expected):
    assert parse_band_spread(token) == expected


@pytest.mark.parametrize(
    "token,expected_enabled,expected_range",
    [
        (None, False, None),
        ("full", True, None),
        ("range:-4:4", True, (-4.0, 4.0)),
        ("range:4:-4", True, (-4.0, 4.0)),
    ],
)
def test_parse_ratio_mode(token, expected_enabled, expected_range):
    enabled, y_range = parse_ratio_mode(token)
    assert enabled is expected_enabled
    assert y_range == expected_range


def test_parse_x_range():
    assert parse_x_range(None) is None
    assert parse_x_range([-5.0, 5.0]) == (-5.0, 5.0)
    assert parse_x_range([5.0, -5.0]) == (-5.0, 5.0)


@pytest.mark.parametrize(
    "labels,n_files,expected",
    [
        (None, 2, None),
        (["None"], 2, None),
        (["a"], 1, ["a"]),
        (["a", "b"], 2, ["a", "b"]),
    ],
)
def test_parse_labels_ok(labels, n_files, expected):
    assert parse_labels(labels, n_files=n_files) == expected


def test_parse_labels_length_mismatch_raises():
    with pytest.raises(ValueError):
        parse_labels(["a"], n_files=2)


def test_overlay_dist_runnable_from_anywhere_non_root_file(tmp_path: Path):
    dummy = tmp_path / "dummy.txt"
    dummy.write_text("not a root file")

    script = Path(__file__).resolve().parents[1] / "utilities" / "overlay_dist.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--files", str(dummy), "--input", "tree", "--branch", "x"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "All --files must end with '.root'" in (proc.stderr + proc.stdout)


def test_overlay_dist_handles_jagged_branch(tmp_path: Path):
    pytest.importorskip("uproot")
    pytest.importorskip("matplotlib")

    jagged_root = Path(__file__).resolve().parents[1] / "tests" / "data" / "tests_trees_jagged.root"
    assert jagged_root.exists()

    script = Path(__file__).resolve().parents[1] / "utilities" / "overlay_dist.py"
    out_dir = tmp_path / "out"

    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--files",
            str(jagged_root),
            str(jagged_root),
            "--input",
            "jagged_tree",
            "--branch",
            "xj",
            "--output-dir",
            str(out_dir),
        ],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert list(out_dir.glob("*.png"))
    assert list(out_dir.glob("*.svg"))


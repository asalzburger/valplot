import subprocess
import sys
from pathlib import Path

import pytest

from utilities.overay_hist import parse_band_spread, parse_eff_input, parse_labels, parse_ratio_mode


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


def test_parse_eff_input():
    assert parse_eff_input("h_pass:h_total") == ("h_pass", "h_total")
    with pytest.raises(ValueError):
        parse_eff_input("h_pass")


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


def test_overay_hist_runnable_from_anywhere_non_root_file(tmp_path: Path):
    dummy = tmp_path / "dummy.txt"
    dummy.write_text("not a root file")

    script = Path(__file__).resolve().parents[1] / "utilities" / "overay_hist.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--files", str(dummy), "--kind", "hist1d", "--input", "hx"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "All --files must end with '.root'" in (proc.stderr + proc.stdout)


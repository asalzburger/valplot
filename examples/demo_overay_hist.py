"""Demo: overlay hist1d and efficiency using utilities.overay_hist."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".mplconfig"))

from utilities.overay_hist import main


if __name__ == "__main__":
    if "--output-dir" not in sys.argv:
        sys.argv.extend(["--output-dir", str(REPO_ROOT / "examples" / "output")])

    # Default demo mode if user did not provide explicit args.
    if "--kind" not in sys.argv and "--input" not in sys.argv:
        sys.argv.extend(
            [
                "--files",
                str(REPO_ROOT / "tests" / "data" / "tests_input.root"),
                str(REPO_ROOT / "tests" / "data" / "tests_input.root"),
                "--kind",
                "hist1d",
                "--input",
                "hx",
                "hy",
                "--labels",
                "hx",
                "hy",
                "--band",
                "1sigma",
                "--ratio",
                "full",
            ]
        )

    raise SystemExit(main())


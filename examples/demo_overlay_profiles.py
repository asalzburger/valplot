"""Demo: overlay profiles with optional bands/ratio/restrictions using utilities.overlay_profiles."""

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

from utilities.overlay_profiles import main


if __name__ == "__main__":
    # Default to repo example output when run without --output-dir
    if "--output-dir" not in sys.argv:
        sys.argv.extend(["--output-dir", str(REPO_ROOT / "examples" / "output")])

    # Provide a sensible default CLI example if the user didn't pass any plots.
    if "--plot" not in sys.argv:
        sys.argv.extend(
            [
                "--files",
                str(REPO_ROOT / "tests" / "data" / "tests_input.root"),
                "--input",
                "tree",
                "--plot",
                "x:y",
                "--band",
                "spread",
                "--ratio",
            ]
        )

    raise SystemExit(main())


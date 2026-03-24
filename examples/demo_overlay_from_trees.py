"""Demo: overlay tree-derived plots from multiple ROOT files. Uses utilities.overlay_from_trees."""

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

from utilities.overlay_from_trees import main

if __name__ == "__main__":
    # Default to repo example output when run without --output-dir
    if "--output-dir" not in sys.argv:
        sys.argv.extend(["--output-dir", str(REPO_ROOT / "examples" / "output")])
    raise SystemExit(main())

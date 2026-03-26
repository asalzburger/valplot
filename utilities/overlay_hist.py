"""Canonical entry point for overlaying hist1d/efficiency ROOT objects.

This module re-exports functionality from the legacy `overay_hist` module.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Support execution as both module import and direct script path.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from utilities.overay_hist import *  # type: ignore # noqa: F401,F403
except ModuleNotFoundError:
    from overay_hist import *  # type: ignore # noqa: F401,F403


if __name__ == "__main__":
    raise SystemExit(main())


"""PyInstaller entry point for the Edit Videos FastAPI sidecar."""
from __future__ import annotations

import sys

# Ensure the project src is importable when run as a frozen binary
import os
if getattr(sys, "frozen", False):
    _base = os.path.dirname(sys.executable)
    sys.path.insert(0, _base)

from edit_videos_poc.web.app import main  # noqa: E402

if __name__ == "__main__":
    main()

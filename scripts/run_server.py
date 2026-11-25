#!/usr/bin/env python3
"""Compatibility shim: same as `edit-videos serve ...`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edit_videos_poc.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["serve", *sys.argv[1:]]))

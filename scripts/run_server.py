#!/usr/bin/env python3
"""Start the Edit Videos web server.

Usage:
    python scripts/run_server.py [--host 0.0.0.0] [--port 8000]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is in path when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        "edit_videos_poc.web.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

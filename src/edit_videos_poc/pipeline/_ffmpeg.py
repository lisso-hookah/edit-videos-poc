"""Shared subprocess wrapper for ffmpeg invocations."""
from __future__ import annotations

import subprocess


def run_ffmpeg(cmd: list[str]) -> str:
    """Run ffmpeg-style command; raise with stderr on failure. Returns stderr (ffmpeg writes progress there)."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n---stderr---\n{proc.stderr}")
    return proc.stderr

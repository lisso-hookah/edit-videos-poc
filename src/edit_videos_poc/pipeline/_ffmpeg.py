"""Shared subprocess wrapper for ffmpeg invocations."""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import cache
from pathlib import Path


@cache
def ffmpeg_exe() -> str:
    """Locate ffmpeg: FFMPEG_BINARY env, then PATH, then the binary bundled with imageio-ffmpeg."""
    explicit = os.getenv("FFMPEG_BINARY", "").strip()
    if explicit:
        return explicit
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "ffmpeg が見つかりません。ffmpeg を PATH に追加するか、FFMPEG_BINARY に実行ファイルのパスを設定してください。"
        ) from exc


def run_ffmpeg(cmd: list[str]) -> str:
    """Run ffmpeg-style command; raise with stderr on failure. Returns stderr (ffmpeg writes progress there)."""
    if cmd and cmd[0] == "ffmpeg":
        cmd = [ffmpeg_exe(), *cmd[1:]]
    # ffmpeg logs UTF-8 regardless of the console code page (cp932 on Japanese Windows).
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n---stderr---\n{proc.stderr}")
    return proc.stderr


def filter_path(path: Path | str) -> str:
    """Escape a file path for use as a filter option value (e.g. subtitles=...)."""
    # Two rounds: the filter's option parser, then the filtergraph parser. Without this a
    # Windows drive colon ("C:") is read as an option separator and the filter fails.
    value = str(path).replace("\\", "/")
    for special in ("\\':", "\\'[],;"):
        value = "".join(f"\\{ch}" if ch in special else ch for ch in value)
    return value

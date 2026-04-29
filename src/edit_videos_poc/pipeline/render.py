"""Final rendering: silent-region cut + subtitle burn-in."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import run_ffmpeg
from .silence import SilentRange


def cut_silence(video_path: Path, cuts: list[SilentRange], out_name: str | None = None) -> Path:
    """Remove silent ranges from video using ffmpeg select/aselect filters."""
    out_path = config.step_dir("rendered") / (out_name or f"{video_path.stem}_cut.mp4")
    if not cuts:
        run_ffmpeg(["ffmpeg", "-y", "-i", str(video_path), "-c", "copy", str(out_path)])
        return out_path

    drop_expr = "+".join(f"between(t,{c.start},{c.end})" for c in cuts)
    select = f"not({drop_expr})"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"select='{select}',setpts=N/FRAME_RATE/TB",
        "-af", f"aselect='{select}',asetpts=N/SR/TB",
        str(out_path),
    ]
    run_ffmpeg(cmd)
    return out_path


def burn_subtitles(
    video_path: Path,
    sub_path: Path,
    font: str = "Noto Sans CJK JP",
    font_size: int = 36,
    font_color: str = "&H00FFFFFF&",
    out_name: str | None = None,
) -> Path:
    """Burn subtitles (SRT or ASS) into video as hardsub."""
    out_path = config.step_dir("rendered") / (out_name or f"{video_path.stem}_subbed.mp4")
    if sub_path.suffix.lower() == ".ass":
        # ASS carries its own styling; force_style not needed
        vf = f"subtitles={sub_path}"
    else:
        style = f"FontName={font},FontSize={font_size},PrimaryColour={font_color},Outline=1,Shadow=0"
        vf = f"subtitles={sub_path}:force_style='{style}'"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", vf,
        "-c:a", "copy",
        str(out_path),
    ]
    run_ffmpeg(cmd)
    return out_path

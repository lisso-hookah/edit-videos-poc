"""Final rendering: silent-region cut + subtitle burn-in."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import filter_path, run_ffmpeg
from .silence import SilentRange


def _select_expr(cuts: list[SilentRange]) -> str:
    drop_expr = "+".join(f"between(t,{c.start},{c.end})" for c in cuts)
    return f"not({drop_expr})"


def _subtitles_filter(sub_path: Path, font: str | None, font_size: int, font_color: str) -> str:
    if sub_path.suffix.lower() == ".ass":
        # ASS carries its own styling; force_style not needed
        return f"subtitles={filter_path(sub_path)}"
    style = (
        f"FontName={font or config.default_font()},FontSize={font_size},"
        f"PrimaryColour={font_color},Outline=1,Shadow=0"
    )
    return f"subtitles={filter_path(sub_path)}:force_style='{style}'"


def cut_silence(video_path: Path, cuts: list[SilentRange], out_name: str | None = None) -> Path:
    """Remove silent ranges from video using ffmpeg select/aselect filters."""
    out_path = config.step_dir("rendered") / (out_name or f"{video_path.stem}_cut.mp4")
    if not cuts:
        run_ffmpeg(["ffmpeg", "-y", "-i", str(video_path), "-c", "copy", str(out_path)])
        return out_path

    select = _select_expr(cuts)
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
    font: str | None = None,
    font_size: int = 48,
    font_color: str = "&H00FFFFFF&",
    out_name: str | None = None,
) -> Path:
    """Burn subtitles (SRT or ASS) into video as hardsub."""
    out_path = config.step_dir("rendered") / (out_name or f"{video_path.stem}_subbed.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", _subtitles_filter(sub_path, font, font_size, font_color),
        "-c:a", "copy",
        str(out_path),
    ]
    run_ffmpeg(cmd)
    return out_path


def cut_and_burn(
    video_path: Path,
    cuts: list[SilentRange],
    sub_path: Path,
    font: str | None = None,
    font_size: int = 48,
    font_color: str = "&H00FFFFFF&",
    out_name: str | None = None,
) -> Path:
    """Cut silent ranges and burn subtitles in a single encode (subtitles must be on the post-cut timeline)."""
    out_path = config.step_dir("rendered") / (out_name or f"{video_path.stem}_cut_subbed.mp4")
    subtitles = _subtitles_filter(sub_path, font, font_size, font_color)
    cmd = ["ffmpeg", "-y", "-i", str(video_path)]
    if cuts:
        select = _select_expr(cuts)
        # setpts must precede subtitles so the burn-in sees the post-cut clock.
        cmd += [
            "-vf", f"select='{select}',setpts=N/FRAME_RATE/TB,{subtitles}",
            "-af", f"aselect='{select}',asetpts=N/SR/TB",
        ]
    else:
        cmd += ["-vf", subtitles, "-c:a", "copy"]
    cmd.append(str(out_path))
    run_ffmpeg(cmd)
    return out_path

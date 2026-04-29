"""Video clipping and optional text overlay via ffmpeg drawtext."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import run_ffmpeg


def clip_video(
    video_path: Path,
    start: str | float,
    end: str | float | None = None,
    duration: float | None = None,
    top_text: str | None = None,
    bottom_text: str | None = None,
    font: str = "Noto Sans CJK JP",
    font_size: int = 108,
    text_color: str = "white",
    out_name: str | None = None,
) -> Path:
    """Clip video and optionally burn top/bottom centered text."""
    out_path = config.step_dir("clip") / (out_name or f"{video_path.stem}_clip.mp4")

    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", str(video_path)]
    if end is not None:
        cmd += ["-to", str(end)]
    elif duration is not None:
        cmd += ["-t", str(duration)]

    filters: list[str] = []
    if top_text:
        filters.append(_drawtext(top_text, font, font_size, text_color, "y=(h-text_h)/2-500"))
    if bottom_text:
        filters.append(_drawtext(bottom_text, font, font_size, text_color, "y=(h+text_h)/2+500"))

    if filters:
        cmd += ["-vf", ",".join(filters), "-c:a", "copy"]
    else:
        cmd += ["-c", "copy"]

    cmd.append(str(out_path))
    run_ffmpeg(cmd)
    return out_path


def _drawtext(text: str, font: str, size: int, color: str, y_expr: str) -> str:
    escaped = text.replace("'", "’").replace(":", r"\:")
    return (
        f"drawtext=font='{font}':text='{escaped}':"
        f"fontsize={size}:fontcolor={color}:"
        f"borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:{y_expr}"
    )

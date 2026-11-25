"""Video clipping and optional text overlay via ffmpeg drawtext."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import filter_path, run_ffmpeg


def clip_video(
    video_path: Path,
    start: str | float,
    end: str | float | None = None,
    duration: float | None = None,
    top_text: str | None = None,
    bottom_text: str | None = None,
    font: str | None = None,
    font_size: int = 108,
    text_color: str = "white",
    out_name: str | None = None,
) -> Path:
    """Clip video and optionally burn top/bottom centered text."""
    out_dir = config.step_dir("clip")
    out_path = out_dir / (out_name or f"{video_path.stem}_clip.mp4")
    font = font or config.default_font()

    # -to/-t go before -i: after it, -to counts from the seek point and overshoots by `start`.
    cmd = ["ffmpeg", "-y", "-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]
    elif duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-i", str(video_path)]

    filters: list[str] = []
    if top_text:
        text_file = _write_text(out_dir / f"{out_path.stem}_top.txt", top_text)
        filters.append(_drawtext(text_file, font, font_size, text_color, "y=(h-text_h)/2-400"))
    if bottom_text:
        text_file = _write_text(out_dir / f"{out_path.stem}_bottom.txt", bottom_text)
        filters.append(_drawtext(text_file, font, font_size, text_color, "y=(h+text_h)/2+400"))

    if filters:
        cmd += ["-vf", ",".join(filters), "-c:a", "copy"]
    else:
        cmd += ["-c", "copy"]

    cmd.append(str(out_path))
    run_ffmpeg(cmd)
    return out_path


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _drawtext(text_file: Path, font: str, size: int, color: str, y_expr: str) -> str:
    # textfile + expansion=none: the overlay text never passes through filter escaping,
    # so quotes, colons, percent signs and backslashes are drawn as typed.
    return (
        f"drawtext=font={filter_path(font)}:textfile={filter_path(text_file)}:expansion=none:"
        f"fontsize={size}:fontcolor={color}:"
        f"borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:{y_expr}"
    )

"""Convert horizontal video to 9:16 vertical format with blurred background."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import run_ffmpeg


def make_vertical(
    video_path: Path,
    width: int = 1080,
    height: int = 1920,
    blur_sigma: int = 40,
    out_name: str | None = None,
) -> Path:
    """Composite original video centered on a blurred/stretched background (9:16).

    Background: original video scaled to cover width×height, then gaussian-blurred.
    Foreground: original video scaled to fit width, overlaid at center.
    """
    out_path = config.step_dir("vertical") / (out_name or f"{video_path.stem}_vertical.mp4")
    # fg: fit to target width (landscape → pillarbox-free); ensure even dimensions
    fg_scale = f"scale={width}:trunc(({width}/iw*ih)/2)*2"
    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},gblur=sigma={blur_sigma}[bg];"
        f"[0:v]{fg_scale}[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-filter_complex", filter_complex,
        "-c:a", "copy",
        str(out_path),
    ]
    run_ffmpeg(cmd)
    return out_path

"""Convert horizontal video to 9:16 vertical format with configurable background."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import run_ffmpeg


def make_vertical(
    video_path: Path,
    width: int = 1080,
    height: int = 1920,
    blur_sigma: int = 40,
    bg_color: str | None = None,
    bg_image: Path | None = None,
    out_name: str | None = None,
) -> Path:
    """Composite original video centered on a background (9:16).

    Background priority: bg_image > bg_color > blurred video (default).
    """
    out_path = config.step_dir("vertical") / (out_name or f"{video_path.stem}_vertical.mp4")
    fg_scale = f"scale={width}:trunc(({width}/iw*ih)/2)*2"

    if bg_image is not None:
        filter_complex = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},gblur=sigma={blur_sigma}[bg];"
            f"[1:v]{fg_scale}[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg_image),
            "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-c:a", "copy",
            "-shortest",
            str(out_path),
        ]
    elif bg_color is not None:
        filter_complex = (
            f"color=c={bg_color}:s={width}x{height}:r=30[bg];"
            f"[0:v]{fg_scale}[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-filter_complex", filter_complex,
            "-c:a", "copy",
            str(out_path),
        ]
    else:
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

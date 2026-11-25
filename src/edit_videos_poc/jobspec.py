"""Translate a web/worker job (pipeline name + params dict) into CLI arguments and locate its result."""
from __future__ import annotations

from pathlib import Path
from typing import Any

# Step directory (under WORK_DIR) holding each pipeline's final file.
_OUTPUT_STEP = {"pipeline": "rendered", "short": "vertical", "clip": "clip"}


def _opt(name: str, value: Any) -> str:
    # "--name=value": free text such as "-5 points" must not be parsed as another option.
    return f"{name}={value}"


def build_args(
    pipeline: str,
    params: dict[str, Any],
    video_path: Path | str,
    bg_image: Path | str | None = None,
) -> list[str]:
    """Return `edit-videos` CLI arguments (subcommand first) for a job."""
    p = params
    if pipeline in ("pipeline", "short"):
        args = [
            pipeline, str(video_path),
            _opt("--language", p.get("language", "ja")),
            _opt("--noise-db", p.get("noise_db", -30)),
            _opt("--min-silence", p.get("min_silence", 0.5)),
            _opt("--font-color", p.get("font_color", "yellow")),
            _opt("--font-size", p.get("font_size", 48)),
            _opt("--subtitle-position", p.get("subtitle_position", 2)),
            _opt("--outline-size", p.get("outline_size", 2)),
        ]
        if p.get("font"):
            args.append(_opt("--font", p["font"]))
        for flag in ("bold", "italic", "box_background", "skip_refine"):
            if p.get(flag):
                args.append("--" + flag.replace("_", "-"))
        if pipeline == "pipeline":
            if p.get("thumbnail"):
                args.append("--thumbnail")
        else:
            args.append(_opt("--blur-sigma", p.get("blur_sigma", 40)))
            if p.get("bg_color"):
                args.append(_opt("--bg-color", p["bg_color"]))
            if bg_image:
                args.append(_opt("--bg-image", bg_image))
        return args

    if pipeline == "clip":
        args = [
            "clip", str(video_path),
            _opt("--start", p.get("start_time", "0")),
            _opt("--font-size", p.get("font_size", 108)),
            _opt("--text-color", p.get("text_color", "white")),
        ]
        if p.get("end_time"):
            args.append(_opt("--end", p["end_time"]))
        if p.get("top_text"):
            args.append(_opt("--top-text", p["top_text"]))
        if p.get("bottom_text"):
            args.append(_opt("--bottom-text", p["bottom_text"]))
        if p.get("font"):
            args.append(_opt("--font", p["font"]))
        return args

    raise ValueError(f"Unknown pipeline: {pipeline!r}")


def find_output(work_dir: Path, pipeline: str) -> Path | None:
    """Return the final video a finished job wrote under work_dir, if any."""
    out_dir = work_dir / _OUTPUT_STEP.get(pipeline, "rendered")
    if not out_dir.is_dir():
        return None
    videos = sorted(out_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    return videos[0] if videos else None

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .queue_manager import Job

from . import PROJECT_ROOT

_SCRIPTS = PROJECT_ROOT / "scripts"
_STEP_RE = re.compile(r"\[(\d+)/(\d+)\]\s*(.*)")


def execute(job: Job) -> None:
    work_dir = (PROJECT_ROOT / "output" / "jobs" / job.id).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    script, args, extra_env = _build_command(job)
    cmd = ["python", str(_SCRIPTS / script)] + args

    env = os.environ.copy()
    env["WORK_DIR"] = str(work_dir)
    env.update(extra_env)

    tail: list[str] = []
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    )
    with proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            tail = (tail + [line])[-30:]
            m = _STEP_RE.search(line)
            if m:
                cur, total = int(m.group(1)), int(m.group(2))
                snapped = min(int(cur / total * 100 / 20) * 20, 80)
                job.progress = max(snapped, 20)
                job.progress_label = m.group(3).strip()

    if proc.returncode != 0:
        raise RuntimeError(
            f"Process failed (exit {proc.returncode}):\n" + "\n".join(tail[-10:])
        )

    job.output_filename = _find_output(work_dir, job.pipeline)


def _find_output(work_dir: Path, pipeline: str) -> str | None:
    step = {"pipeline": "rendered", "short": "vertical", "clip": "clip"}.get(pipeline, "rendered")
    out_dir = work_dir / step
    if out_dir.exists():
        for f in sorted(out_dir.glob("*.mp4")):
            return f"{step}/{f.name}"
    return None


def _build_command(job: Job) -> tuple[str, list[str], dict[str, str]]:
    p = job.params
    video = p["video_path"]
    extra_env: dict[str, str] = {}

    whisper = str(p.get("whisper_model", "medium"))
    extra_env["WHISPER_MODEL"] = whisper

    if job.pipeline == "pipeline":
        args: list[str] = [
            video,
            "--language", str(p.get("language", "ja")),
            "--noise-db", str(p.get("noise_db", "-30")),
            "--min-silence", str(p.get("min_silence", "0.5")),
            "--font-color", str(p.get("font_color", "yellow")),
            "--font-size", str(p.get("font_size", 48)),
            "--subtitle-position", str(p.get("subtitle_position", 2)),
            "--outline-size", str(p.get("outline_size", 2)),
        ]
        if p.get("font"):
            args += ["--font", str(p["font"])]
        if p.get("bold"):
            args.append("--bold")
        if p.get("italic"):
            args.append("--italic")
        if p.get("box_background"):
            args.append("--box-background")
        if p.get("skip_refine"):
            args.append("--skip-refine")
        if p.get("thumbnail"):
            args.append("--thumbnail")
        return "run_pipeline.py", args, extra_env

    if job.pipeline == "short":
        args = [
            video,
            "--language", str(p.get("language", "ja")),
            "--font-color", str(p.get("font_color", "yellow")),
            "--font-size", str(p.get("font_size", 48)),
            "--subtitle-position", str(p.get("subtitle_position", 2)),
            "--outline-size", str(p.get("outline_size", 2)),
            "--blur-sigma", str(p.get("blur_sigma", "40")),
        ]
        if p.get("font"):
            args += ["--font", str(p["font"])]
        if p.get("bold"):
            args.append("--bold")
        if p.get("italic"):
            args.append("--italic")
        if p.get("box_background"):
            args.append("--box-background")
        if p.get("skip_refine"):
            args.append("--skip-refine")
        if p.get("bg_color"):
            args += ["--bg-color", str(p["bg_color"])]
        if p.get("bg_image"):
            args += ["--bg-image", str(p["bg_image"])]
        return "run_short.py", args, extra_env

    if job.pipeline == "clip":
        args = [
            video,
            "--start", str(p.get("start_time", "0")),
            "--font-size", str(p.get("font_size", "108")),
            "--text-color", str(p.get("text_color", "white")),
        ]
        if p.get("end_time"):
            args += ["--end", str(p["end_time"])]
        if p.get("top_text"):
            args += ["--top-text", str(p["top_text"])]
        if p.get("bottom_text"):
            args += ["--bottom-text", str(p["bottom_text"])]
        return "run_clip.py", args, extra_env

    raise ValueError(f"Unknown pipeline: {job.pipeline!r}")

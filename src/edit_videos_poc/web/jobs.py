"""Run one job as a child process and mirror its progress onto the Job record."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING

from .. import config
from ..jobspec import build_args, find_output

if TYPE_CHECKING:
    from .queue_manager import Job

_STEP_RE = re.compile(r"\[(\d+)/(\d+)\]\s*(.*)")
_WARN_PREFIX = "[warn]"


def execute(job: Job) -> None:
    """Run the job's pipeline to completion; raise RuntimeError with the log tail on failure."""
    work_dir = (config.jobs_dir() / job.id).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    params = job.params
    # sys.executable, not "python": the child must run in this environment, whatever PATH says.
    cmd = [sys.executable, "-m", "edit_videos_poc", *build_args(job.pipeline, params, params["video_path"], params.get("bg_image"))]

    env = os.environ.copy()
    env["WORK_DIR"] = str(work_dir)
    env["WHISPER_MODEL"] = str(params.get("whisper_model", "medium"))
    env["PYTHONUNBUFFERED"] = "1"  # progress lines must arrive as they are printed, not at exit
    env["PYTHONUTF8"] = "1"

    tail: list[str] = []
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    with proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            tail = (tail + [line])[-30:]
            if line.startswith(_WARN_PREFIX):
                job.warnings.append(line[len(_WARN_PREFIX):].strip())
                continue
            m = _STEP_RE.search(line)
            if m:
                cur, total = int(m.group(1)), int(m.group(2))
                # A step is announced when it starts, so cur-1 steps are complete.
                job.progress = max(5, int((cur - 1) / total * 100))
                job.progress_label = m.group(3).strip()

    if proc.returncode != 0:
        raise RuntimeError(f"Process failed (exit {proc.returncode}):\n" + "\n".join(tail[-10:]))

    output = find_output(work_dir, job.pipeline)
    if output is None:
        raise RuntimeError("出力ファイルが生成されませんでした:\n" + "\n".join(tail[-10:]))
    job.output_filename = output.relative_to(work_dir).as_posix()

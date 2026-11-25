"""In-process job queue for the local web UI, persisted as one JSON file per job."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .. import config

# Whisper saturates the CPU/GPU on its own; running jobs side by side on one PC only slows all of them.
MAX_WORKERS = max(1, int(os.getenv("EDIT_VIDEOS_MAX_JOBS", "1") or 1))
MAX_QUEUE = 20
_STATE_FILE = "job.json"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    pipeline: str
    params: dict[str, Any]
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    progress_label: str = "待機中"
    output_filename: str | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def save(self) -> None:
        """Write this job's state to its output directory."""
        job_dir = config.jobs_dir() / self.id
        job_dir.mkdir(parents=True, exist_ok=True)
        data = asdict(self) | {"status": self.status.value, "created_at": self.created_at.isoformat()}
        tmp = job_dir / (_STATE_FILE + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(job_dir / _STATE_FILE)


def _load_job(path: Path) -> Job | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        job = Job(
            id=data["id"],
            pipeline=data["pipeline"],
            params=data.get("params", {}),
            status=JobStatus(data["status"]),
            progress=int(data.get("progress", 0)),
            progress_label=data.get("progress_label", ""),
            output_filename=data.get("output_filename"),
            error=data.get("error"),
            warnings=list(data.get("warnings", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        # The server that owned this job is gone; its child process went with it.
        job.status = JobStatus.FAILED
        job.error = "サーバーが再起動されたため中断されました"
        job.progress_label = "失敗"
        job.save()
    return job


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._pending: list[str] = []
        self._queue: asyncio.Queue[Job] | None = None
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._semaphore: asyncio.Semaphore | None = None

    def restore(self) -> None:
        """Reload jobs left on disk by a previous run."""
        for state in config.jobs_dir().glob(f"*/{_STATE_FILE}"):
            job = _load_job(state)
            if job:
                self._jobs[job.id] = job

    def submit(self, pipeline: str, params: dict[str, Any]) -> Job:
        """Queue a job; raises RuntimeError when the server is not ready or the queue is full."""
        if self._queue is None:
            raise RuntimeError("サーバーの起動が完了していません")
        if len(self._pending) >= MAX_QUEUE:
            raise RuntimeError(f"キューが満杯です（最大{MAX_QUEUE}件）")
        job = Job(id=str(uuid.uuid4()), pipeline=pipeline, params=params)
        self._jobs[job.id] = job
        self._pending.append(job.id)
        job.save()
        self._queue.put_nowait(job)
        return job

    def get(self, job_id: str) -> Job | None:
        """Return a job by id."""
        return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        """Return every known job, newest first."""
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def queue_position(self, job_id: str) -> int:
        """Return the 1-based position among waiting jobs (0 if not waiting)."""
        try:
            return self._pending.index(job_id) + 1
        except ValueError:
            return 0

    async def start(self) -> None:
        """Dispatch queued jobs forever, at most MAX_WORKERS at a time."""
        self._queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(MAX_WORKERS)
        tasks: set[asyncio.Task[None]] = set()
        while True:
            job = await self._queue.get()
            task = asyncio.create_task(self._dispatch(job))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    async def _dispatch(self, job: Job) -> None:
        assert self._semaphore is not None
        async with self._semaphore:
            if job.id in self._pending:
                self._pending.remove(job.id)
            await asyncio.get_running_loop().run_in_executor(self._executor, _run_job, job)


def _run_job(job: Job) -> None:
    from .jobs import execute

    try:
        job.status = JobStatus.RUNNING
        job.progress = 5
        job.progress_label = "処理中"
        job.save()
        execute(job)
        job.status = JobStatus.DONE
        job.progress = 100
        job.progress_label = "完了"
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.progress_label = "失敗"
    job.save()

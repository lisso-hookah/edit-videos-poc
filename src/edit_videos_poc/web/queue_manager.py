from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid

MAX_WORKERS = 5
MAX_QUEUE = 20


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
    created_at: datetime = field(default_factory=datetime.now)


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._pending: list[str] = []
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=MAX_QUEUE)
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._semaphore: asyncio.Semaphore | None = None

    def submit(self, pipeline: str, params: dict[str, Any]) -> Job:
        if self._queue.full():
            raise RuntimeError("キューが満杯です（最大20件）")
        job = Job(id=str(uuid.uuid4()), pipeline=pipeline, params=params)
        self._jobs[job.id] = job
        self._pending.append(job.id)
        self._queue.put_nowait(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def queue_position(self, job_id: str) -> int:
        try:
            return self._pending.index(job_id) + 1
        except ValueError:
            return 0

    async def start(self) -> None:
        self._semaphore = asyncio.Semaphore(MAX_WORKERS)
        while True:
            job = await self._queue.get()
            if job.id in self._pending:
                self._pending.remove(job.id)
            asyncio.create_task(self._dispatch(job))

    async def _dispatch(self, job: Job) -> None:
        loop = asyncio.get_event_loop()
        assert self._semaphore is not None
        async with self._semaphore:
            await loop.run_in_executor(self._executor, _run_job, job)


def _run_job(job: Job) -> None:
    from .jobs import execute
    try:
        job.status = JobStatus.RUNNING
        execute(job)
        job.status = JobStatus.DONE
        job.progress = 100
        job.progress_label = "完了"
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = str(exc)
        job.progress_label = "失敗"

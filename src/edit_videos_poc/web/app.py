"""FastAPI app for the local web UI: upload → queue a job → poll → download."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import config
from .queue_manager import JobQueue

_UPLOAD_CHUNK = 1024 * 1024
queue = JobQueue()


def _purge_old_files() -> None:
    """Delete uploads and job outputs older than EDIT_VIDEOS_RETENTION_DAYS (default 7; 0 keeps everything)."""
    days = float(os.getenv("EDIT_VIDEOS_RETENTION_DAYS", "7") or 0)
    if days <= 0:
        return
    cutoff = time.time() - days * 86400
    for entry in [*config.uploads_dir().iterdir(), *config.jobs_dir().iterdir()]:
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
        except OSError:
            pass


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _purge_old_files()
    queue.restore()
    dispatcher = asyncio.create_task(queue.start())
    yield
    dispatcher.cancel()


app = FastAPI(title="Edit Videos", lifespan=_lifespan)


def _safe_name(filename: str | None) -> str:
    # Keep the user's file name (it becomes the download name) minus anything a filesystem rejects.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", Path(filename or "").name).strip(" .")
    return name if Path(name).suffix else f"{name or 'file'}.bin"


def _find_upload(file_id: str) -> Path | None:
    try:
        uuid.UUID(file_id)  # ids are server-generated; anything else is not a path we wrote
    except ValueError:
        return None
    folder = config.uploads_dir() / file_id
    files = [f for f in folder.iterdir() if f.is_file()] if folder.is_dir() else []
    return files[0].resolve() if files else None


@app.get("/api/health")
async def health() -> dict[str, Any]:
    """Report what this install can do, so the UI can explain skipped steps up front."""
    return {
        "gemini": bool(config.GEMINI_API_KEY),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "data_dir": str(config.DATA_DIR),
    }


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    """Store an uploaded file and return its id."""
    file_id = str(uuid.uuid4())
    dest = config.uploads_dir() / file_id / _safe_name(file.filename)
    dest.parent.mkdir(parents=True)
    # Stream to disk: videos are routinely larger than free RAM.
    with dest.open("wb") as out:
        while chunk := await file.read(_UPLOAD_CHUNK):
            out.write(chunk)
    return {"file_id": file_id, "filename": file.filename, "size": dest.stat().st_size}


class JobRequest(BaseModel):
    pipeline: str
    file_id: str
    params: dict[str, Any] = {}
    bg_file_id: str | None = None


@app.post("/api/jobs")
async def submit_job(req: JobRequest) -> dict[str, Any]:
    """Queue a pipeline run for an uploaded file."""
    if req.pipeline not in ("pipeline", "short", "clip"):
        raise HTTPException(400, f"不明なパイプラインです: {req.pipeline}")
    video = _find_upload(req.file_id)
    if not video:
        raise HTTPException(404, "アップロードファイルが見つかりません")

    params = dict(req.params)
    params["video_path"] = str(video)
    params.pop("bg_image", None)
    if req.bg_file_id:
        bg = _find_upload(req.bg_file_id)
        if bg:
            params["bg_image"] = str(bg)

    try:
        job = queue.submit(req.pipeline, params)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    """List all jobs, newest first."""
    return [_serialize(j) for j in queue.all()]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Return one job's status."""
    job = queue.get(job_id)
    if not job:
        raise HTTPException(404, "ジョブが見つかりません")
    return _serialize(job)


@app.get("/api/jobs/{job_id}/download/{file_path:path}")
async def download(job_id: str, file_path: str) -> FileResponse:
    """Download a file produced by a job."""
    job = queue.get(job_id)
    if not job:
        raise HTTPException(404)
    base = (config.jobs_dir() / job_id).resolve()
    target = (base / file_path).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(403)
    if not target.is_file():
        raise HTTPException(404)
    return FileResponse(target, filename=target.name)


def _serialize(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "pipeline": job.pipeline,
        "status": job.status,
        "progress": job.progress,
        "progress_label": job.progress_label,
        "queue_position": queue.queue_position(job.id),
        "error": job.error,
        "warnings": job.warnings,
        "output_filename": job.output_filename,
        "created_at": job.created_at.isoformat(),
    }


# Serve frontend — must be last
_static = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")

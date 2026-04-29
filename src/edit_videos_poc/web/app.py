from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import PROJECT_ROOT
from .queue_manager import JobQueue, JobStatus

_UPLOADS = PROJECT_ROOT / "uploads"
_UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Edit Videos")
queue = JobQueue()


@app.on_event("startup")
async def _startup() -> None:
    import asyncio
    asyncio.create_task(queue.start())


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    file_id = str(uuid.uuid4())
    suffix = Path(file.filename or "file").suffix or ".bin"
    dest = _UPLOADS / f"{file_id}{suffix}"
    dest.write_bytes(await file.read())
    return {"file_id": file_id, "filename": file.filename, "size": dest.stat().st_size}


class JobRequest(BaseModel):
    pipeline: str
    file_id: str
    params: dict[str, Any] = {}
    bg_file_id: str | None = None


@app.post("/api/jobs")
async def submit_job(req: JobRequest) -> dict[str, Any]:
    matches = list(_UPLOADS.glob(f"{req.file_id}.*"))
    if not matches:
        raise HTTPException(404, "アップロードファイルが見つかりません")

    params = dict(req.params)
    params["video_path"] = str(matches[0].resolve())

    if req.bg_file_id:
        bg = list(_UPLOADS.glob(f"{req.bg_file_id}.*"))
        if bg:
            params["bg_image"] = str(bg[0].resolve())

    try:
        job = queue.submit(req.pipeline, params)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    return {"job_id": job.id, "status": job.status}


@app.get("/api/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    return [_serialize(j) for j in queue.all()]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    job = queue.get(job_id)
    if not job:
        raise HTTPException(404, "ジョブが見つかりません")
    return _serialize(job)


@app.get("/api/jobs/{job_id}/download/{file_path:path}")
async def download(job_id: str, file_path: str) -> FileResponse:
    job = queue.get(job_id)
    if not job:
        raise HTTPException(404)
    base = (PROJECT_ROOT / "output" / "jobs" / job_id).resolve()
    target = (base / file_path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(403)
    if not target.exists():
        raise HTTPException(404)
    return FileResponse(target, filename=target.name, media_type="video/mp4")


def _serialize(job: Any) -> dict[str, Any]:
    return {
        "id": job.id,
        "pipeline": job.pipeline,
        "status": job.status,
        "progress": job.progress,
        "progress_label": job.progress_label,
        "queue_position": queue.queue_position(job.id),
        "error": job.error,
        "output_filename": job.output_filename,
        "created_at": job.created_at.isoformat(),
    }


# Serve frontend — must be last
_static = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from edit_videos_poc import cli, config
from edit_videos_poc.jobspec import build_args, find_output
from edit_videos_poc.web import jobs as web_jobs
from edit_videos_poc.web.app import app


def test_build_args_round_trips_through_the_cli_parser() -> None:
    parser = cli._build_parser()
    short = parser.parse_args(build_args("short", {"font_color": "white", "bold": True, "bg_color": "black", "skip_refine": True}, "in.mp4", "bg.jpg"))
    assert (short.command, short.font_color, short.bold, short.bg_color, short.skip_refine) == ("short", "white", True, "black", True)
    assert short.bg_image == Path("bg.jpg")

    clip = parser.parse_args(build_args("clip", {"start_time": "0:10", "end_time": "0:20", "top_text": "-hi"}, "in.mp4"))
    assert (clip.start, clip.end, clip.top_text, clip.font_size) == ("0:10", "0:20", "-hi", 108)

    with pytest.raises(ValueError):
        build_args("nope", {}, "in.mp4")


def test_find_output_returns_the_final_file(tmp_path: Path) -> None:
    assert find_output(tmp_path, "pipeline") is None
    (tmp_path / "rendered").mkdir()
    (tmp_path / "rendered" / "a_cut_subbed.mp4").write_bytes(b"x")
    assert find_output(tmp_path, "pipeline") == tmp_path / "rendered" / "a_cut_subbed.mp4"


def _wait_done(client: TestClient, job_id: str) -> dict:
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_upload_run_download_and_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_execute(job) -> None:
        out = config.jobs_dir() / job.id / "clip" / f"{Path(job.params['video_path']).stem}_clip.mp4"
        out.parent.mkdir(parents=True)
        out.write_bytes(b"video")
        job.warnings.append("注意")
        job.output_filename = f"clip/{out.name}"

    monkeypatch.setattr(web_jobs, "execute", fake_execute)

    with TestClient(app) as client:
        assert client.post("/api/jobs", json={"pipeline": "clip", "file_id": "../../etc", "params": {}}).status_code == 404
        file_id = client.post("/api/upload", files={"file": ("旅行 vlog: 1.mp4", b"data")}).json()["file_id"]
        assert client.post("/api/jobs", json={"pipeline": "rm -rf", "file_id": file_id}).status_code == 400

        job_id = client.post("/api/jobs", json={"pipeline": "clip", "file_id": file_id, "params": {"start_time": "0"}}).json()["job_id"]
        job = _wait_done(client, job_id)
        assert (job["status"], job["warnings"], job["output_filename"]) == ("done", ["注意"], "clip/旅行 vlog_ 1_clip.mp4")

        assert client.get(f"/api/jobs/{job_id}/download/{job['output_filename']}").content == b"video"
        assert client.get(f"/api/jobs/{job_id}/download/..%2Fjob.json").status_code in (403, 404)
        assert client.get(f"/api/jobs/{job_id}/download/%2e%2e/%2e%2e/%2e%2e/uploads/{file_id}/x").status_code in (403, 404)

    # A new server process must still list the finished job.
    from edit_videos_poc.web.queue_manager import JobQueue

    restored = JobQueue()
    restored.restore()
    assert restored.get(job_id).output_filename == job["output_filename"]


def test_failed_child_process_reports_log_tail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from edit_videos_poc.web.queue_manager import Job

    job = Job(id="j1", pipeline="clip", params={"video_path": str(tmp_path / "missing.mp4"), "start_time": "0"})
    with pytest.raises(RuntimeError, match="Video not found"):
        web_jobs.execute(job)

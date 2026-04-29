#!/usr/bin/env python3
"""
Edit Videos – Local Worker (Windows 11)

ロリポップ上の API をポーリングしてジョブを取得し、
ローカルでパイプラインを実行して結果をアップロードする。

使い方:
    python scripts/run_worker.py

必要な環境変数 (.env に記載):
    LOLLIPOP_API_URL  = https://your-domain.com     # ロリポップのドメイン
    WORKER_KEY        = CHANGE_ME_worker_secret_key  # api.php の WORKER_KEY と同じ値
    GEMINI_API_KEY    = your_gemini_key              # Video/Short パイプラインで必要
    OPENAI_API_KEY    = your_openai_key              # サムネイル生成で必要（任意）
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ─── 設定 ───────────────────────────────────────────────────────
API_URL    = os.environ["LOLLIPOP_API_URL"].rstrip("/")
WORKER_KEY = os.environ["WORKER_KEY"]
POLL_SEC   = 5       # ポーリング間隔（秒）
PROG_SEC   = 4       # 進捗送信間隔（秒）

# プロジェクトルート（このファイルの一階層上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"

_HEADERS = {"X-Worker-Key": WORKER_KEY}
_STEP_RE  = re.compile(r"\[(\d+)/(\d+)\]\s*(.*)")


# ════════════════════════════════════════════════════════════════
# メインループ
# ════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"[worker] 起動 → {API_URL}")
    print(f"[worker] Ctrl+C で停止")
    while True:
        try:
            job = fetch_next_job()
            if job:
                process_job(job)
            else:
                time.sleep(POLL_SEC)
        except KeyboardInterrupt:
            print("\n[worker] 停止")
            sys.exit(0)
        except Exception as exc:
            print(f"[worker] エラー: {exc}")
            time.sleep(POLL_SEC)


# ════════════════════════════════════════════════════════════════
# ジョブ取得・処理
# ════════════════════════════════════════════════════════════════

def fetch_next_job() -> dict | None:
    r = requests.get(f"{API_URL}/api/worker/jobs/next", headers=_HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()  # None または job dict


def process_job(job: dict) -> None:
    job_id   = job["job_id"]
    pipeline = job["pipeline"]
    params   = job["params"]

    print(f"\n[worker] ジョブ開始: {job_id[:8]}… ({pipeline})")

    work_dir = PROJECT_ROOT / "output" / "worker_jobs" / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # ─── 動画ダウンロード ─────────────────────────────────────
    video_path = download_video(job_id, job["download_url"], work_dir)
    print(f"[worker] 動画ダウンロード完了: {video_path.name}")

    # ─── 背景画像ダウンロード (Short + image モード) ──────────
    bg_image_path: Path | None = None
    bg_file_id = params.get("bg_file_id")
    if pipeline == "short" and bg_file_id:
        bg_url  = f"{API_URL}/api/worker/uploads/{bg_file_id}"
        bg_path = work_dir / "bg_image.jpg"
        stream_download(bg_url, bg_path)
        bg_image_path = bg_path
        print(f"[worker] 背景画像ダウンロード完了")

    # ─── パイプライン実行 ─────────────────────────────────────
    try:
        result_path = run_pipeline(job_id, pipeline, params, video_path, bg_image_path, work_dir)
    except Exception as exc:
        send_fail(job_id, str(exc))
        return

    # ─── 結果アップロード ─────────────────────────────────────
    if result_path and result_path.exists():
        upload_result(job_id, result_path)
        print(f"[worker] 完了: {job_id[:8]}…")
    else:
        send_fail(job_id, "結果ファイルが見つかりませんでした")


# ════════════════════════════════════════════════════════════════
# パイプライン実行
# ════════════════════════════════════════════════════════════════

def run_pipeline(
    job_id: str,
    pipeline: str,
    params: dict,
    video_path: Path,
    bg_image_path: Path | None,
    work_dir: Path,
) -> Path | None:

    script, args = build_command(pipeline, params, video_path, bg_image_path)
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + args

    env = os.environ.copy()
    env["WORK_DIR"]      = str(work_dir)
    env["WHISPER_MODEL"] = str(params.get("whisper_model", "medium"))

    print(f"[worker] 実行: {script}")

    last_progress_send = time.time()
    tail: list[str] = []

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )

    progress       = 0
    progress_label = "処理中"

    with proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            tail = (tail + [line])[-30:]
            print(f"  {line}")

            m = _STEP_RE.search(line)
            if m:
                cur, total = int(m.group(1)), int(m.group(2))
                progress       = min(int(cur / total * 100 / 20) * 20, 80)
                progress_label = m.group(3).strip()

            # 進捗を定期送信
            if time.time() - last_progress_send >= PROG_SEC:
                send_progress(job_id, progress, progress_label)
                last_progress_send = time.time()

    if proc.returncode != 0:
        raise RuntimeError(
            f"スクリプト終了コード {proc.returncode}:\n" + "\n".join(tail[-10:])
        )

    return find_output(work_dir, pipeline)


def build_command(
    pipeline: str,
    params: dict,
    video_path: Path,
    bg_image_path: Path | None,
) -> tuple[str, list[str]]:

    vp = str(video_path)

    if pipeline == "pipeline":
        args = [
            vp,
            "--language",    str(params.get("language",    "ja")),
            "--noise-db",    str(params.get("noise_db",    -30)),
            "--min-silence", str(params.get("min_silence", 0.5)),
            "--font-color",  str(params.get("font_color",  "yellow")),
        ]
        if params.get("skip_refine"):
            args.append("--skip-refine")
        if params.get("thumbnail"):
            args.append("--thumbnail")
        return "run_pipeline.py", args

    if pipeline == "short":
        args = [
            vp,
            "--language",   str(params.get("language",   "ja")),
            "--font-color", str(params.get("font_color", "yellow")),
            "--blur-sigma", str(params.get("blur_sigma", 40)),
        ]
        if params.get("skip_refine"):
            args.append("--skip-refine")
        if params.get("bg_color"):
            args += ["--bg-color", str(params["bg_color"])]
        if bg_image_path:
            args += ["--bg-image", str(bg_image_path)]
        return "run_short.py", args

    if pipeline == "clip":
        args = [
            vp,
            "--start",     str(params.get("start_time", "0")),
            "--font-size", str(params.get("font_size",  108)),
            "--text-color", str(params.get("text_color", "white")),
        ]
        if params.get("end_time"):
            args += ["--end", str(params["end_time"])]
        if params.get("top_text"):
            args += ["--top-text", str(params["top_text"])]
        if params.get("bottom_text"):
            args += ["--bottom-text", str(params["bottom_text"])]
        return "run_clip.py", args

    raise ValueError(f"不明なパイプライン: {pipeline!r}")


def find_output(work_dir: Path, pipeline: str) -> Path | None:
    step = {"pipeline": "render", "short": "vertical", "clip": "clip"}.get(pipeline, "render")
    out_dir = work_dir / step
    if out_dir.exists():
        for f in sorted(out_dir.glob("*.mp4")):
            return f
    return None


# ════════════════════════════════════════════════════════════════
# API 通信
# ════════════════════════════════════════════════════════════════

def download_video(job_id: str, download_url: str, work_dir: Path) -> Path:
    url = API_URL + download_url
    dest = work_dir / "input.mp4"
    stream_download(url, dest)
    return dest


def stream_download(url: str, dest: Path) -> None:
    r = requests.get(url, headers=_HEADERS, stream=True, timeout=300)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)


def send_progress(job_id: str, progress: int, label: str) -> None:
    try:
        requests.post(
            f"{API_URL}/api/worker/jobs/{job_id}/progress",
            headers=_HEADERS,
            json={"progress": progress, "progress_label": label},
            timeout=5,
        )
    except Exception:
        pass  # 進捗送信失敗は無視


def upload_result(job_id: str, result_path: Path) -> None:
    with open(result_path, "rb") as f:
        r = requests.post(
            f"{API_URL}/api/worker/jobs/{job_id}/complete",
            headers=_HEADERS,
            files={"file": ("result.mp4", f, "video/mp4")},
            timeout=600,
        )
    r.raise_for_status()


def send_fail(job_id: str, error: str) -> None:
    print(f"[worker] ジョブ失敗: {error[:200]}")
    try:
        requests.post(
            f"{API_URL}/api/worker/jobs/{job_id}/fail",
            headers=_HEADERS,
            json={"error": error},
            timeout=5,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()

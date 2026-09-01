"""
Edit Videos – Windows ランチャー

動作:
  1. {インストール先}\python\pythonw.exe で FastAPI サーバーを起動
  2. ポートが開くのを待ってブラウザを開く
  3. システムトレイアイコンを表示（右クリック → ブラウザで開く / 終了）

PyInstaller でコンパイルして EditVideos.exe にする。
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


# ── パス解決 ─────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    # PyInstaller バンドル → EXE と同じディレクトリがアプリルート
    APP_DIR = Path(sys.executable).parent
else:
    # 開発実行 → リポジトリルート
    APP_DIR = Path(__file__).resolve().parents[1]

PYTHON_EXE   = APP_DIR / "python" / "pythonw.exe"   # コンソールなし
PYTHON_CONS  = APP_DIR / "python" / "python.exe"     # フォールバック
SERVER_SCRIPT = APP_DIR / "scripts" / "run_server.py"
ENV_FILE     = APP_DIR / ".env"
PORT         = 8000
SERVER_URL   = f"http://127.0.0.1:{PORT}"


# ── ユーティリティ ────────────────────────────────────────────────

def find_python() -> str:
    for p in (PYTHON_EXE, PYTHON_CONS):
        if p.exists():
            return str(p)
    return sys.executable  # システム Python にフォールバック


def build_env() -> dict[str, str]:
    env = os.environ.copy()

    # バンドルした ffmpeg を PATH に追加
    ffmpeg_dir = str(APP_DIR / "bin")
    env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")

    # src を PYTHONPATH に追加（embeddable Python が sys.path に持たない場合）
    src_dir = str(APP_DIR / "src")
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else src_dir

    # .env ファイルを読み込む
    if ENV_FILE.exists():
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip())

    # 出力先
    env.setdefault("WORK_DIR", str(APP_DIR / "output"))
    return env


def start_server() -> subprocess.Popen:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    return subprocess.Popen(
        [find_python(), str(SERVER_SCRIPT)],
        env=build_env(),
        cwd=str(APP_DIR),
        creationflags=flags,
    )


def wait_for_server(timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urlopen(SERVER_URL + "/", timeout=1)
            return True
        except (URLError, OSError):
            time.sleep(0.5)
    return False


# ── アイコン生成（Pillow 必須） ────────────────────────────────────

def make_icon():
    from PIL import Image, ImageDraw
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 背景
    d.ellipse([0, 0, size - 1, size - 1], fill="#0d1117")
    # フィルム風フレーム
    d.rectangle([36, 76, 220, 180], fill="#58a6ff")
    d.rectangle([36, 76, 72, 180], fill="#1c2128")
    d.rectangle([184, 76, 220, 180], fill="#1c2128")
    for y in range(86, 172, 20):
        d.rectangle([40, y, 68, y + 10], fill="#58a6ff")
        d.rectangle([188, y, 216, y + 10], fill="#58a6ff")
    # 再生ボタン
    d.polygon([(100, 102), (100, 154), (168, 128)], fill="#0d1117")
    return img


# ── メイン ────────────────────────────────────────────────────────

def main() -> None:
    proc = start_server()

    def open_browser_when_ready():
        if wait_for_server():
            webbrowser.open(SERVER_URL)

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    try:
        import pystray
        from PIL import Image  # noqa: F401 (pystray 依存)

        icon_img = make_icon()

        def on_open(icon, item):
            webbrowser.open(SERVER_URL)

        def on_quit(icon, item):
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem("ブラウザで開く", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", on_quit),
        )
        tray = pystray.Icon("EditVideos", icon_img, "Edit Videos", menu)
        tray.run()

    except Exception:
        # pystray が使えない場合はプロセスが終わるまで待つ
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()

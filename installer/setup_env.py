"""
インストール時セットアップスクリプト
Inno Setup の [Run] セクションから呼び出される。

  {app}\python\python.exe  setup_env.py  "{app}"

行うこと:
  1. python3xx._pth を修正して site-packages を有効化
  2. get-pip.py で pip を導入
  3. プロジェクトに必要なすべてのパッケージをインストール
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.request import urlretrieve

# ── 引数 ──────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: setup_env.py <app_dir>", file=sys.stderr)
    sys.exit(1)

APP_DIR    = Path(sys.argv[1]).resolve()
PYTHON_DIR = APP_DIR / "python"
PYTHON_EXE = PYTHON_DIR / "python.exe"


# ── Step 1: _pth を修正して import site を有効化 ─────────────────
def configure_pth() -> None:
    pth_files = list(PYTHON_DIR.glob("python3*._pth"))
    if not pth_files:
        print("[setup] 警告: _pth ファイルが見つかりません")
        return

    pth = pth_files[0]
    lines = pth.read_text(encoding="utf-8").splitlines()

    new_lines: list[str] = []
    site_added   = False
    import_added = False

    for line in lines:
        stripped = line.strip()

        # "#import site" → "import site"
        if stripped == "#import site":
            new_lines.append("import site")
            import_added = True
            continue

        # Lib\site-packages が未記載なら追加
        if stripped == "." and not site_added:
            new_lines.append(line)
            new_lines.append("Lib\\site-packages")
            site_added = True
            continue

        new_lines.append(line)

    # 行が存在しなかった場合の保険
    if not site_added:
        new_lines.append("Lib\\site-packages")
    if not import_added:
        new_lines.append("import site")

    pth.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"[setup] {pth.name} を更新しました")


# ── Step 2: pip インストール ──────────────────────────────────────
def install_pip() -> None:
    get_pip = PYTHON_DIR / "get-pip.py"

    # インストーラーに同梱されていない場合はダウンロード
    if not get_pip.exists():
        print("[setup] get-pip.py をダウンロード中...")
        urlretrieve("https://bootstrap.pypa.io/get-pip.py", str(get_pip))

    print("[setup] pip をインストール中...")
    subprocess.run(
        [str(PYTHON_EXE), str(get_pip),
         "--no-warn-script-location",
         "--target", str(PYTHON_DIR / "Lib" / "site-packages")],
        check=True,
    )
    print("[setup] pip インストール完了")


# ── Step 3: 依存パッケージ ────────────────────────────────────────
PACKAGES = [
    "faster-whisper>=1.0.0",
    "google-genai>=0.8.0",
    "srt>=3.5.0",
    "python-dotenv>=1.0.0",
    "openai>=2.33.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",
    "aiofiles>=23.0.0",
    "requests>=2.31.0",
    "ffmpeg-python>=0.2.0",
]


def install_packages() -> None:
    print("[setup] パッケージをインストール中... (数分かかります)")
    subprocess.run(
        [
            str(PYTHON_EXE), "-m", "pip", "install",
            "--no-warn-script-location",
            "--target", str(PYTHON_DIR / "Lib" / "site-packages"),
        ] + PACKAGES,
        check=True,
    )
    print("[setup] パッケージインストール完了")


# ── Step 4: 出力ディレクトリ作成 ─────────────────────────────────
def create_dirs() -> None:
    for d in ("output", "uploads"):
        (APP_DIR / d).mkdir(parents=True, exist_ok=True)


# ── メイン ────────────────────────────────────────────────────────
def main() -> None:
    print(f"[setup] セットアップ開始: {APP_DIR}")

    configure_pth()

    if not (PYTHON_DIR / "Lib" / "site-packages" / "pip").exists():
        install_pip()
    else:
        print("[setup] pip は既にインストール済みです")

    install_packages()
    create_dirs()

    print("[setup] セットアップ完了！")


if __name__ == "__main__":
    main()

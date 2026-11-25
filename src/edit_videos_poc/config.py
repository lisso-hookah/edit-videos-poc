"""Centralized config + Colab/local path resolution."""
from __future__ import annotations

import os
import subprocess
import sys
from functools import cache
from pathlib import Path

from dotenv import load_dotenv

_PACKAGE_DIR = Path(__file__).resolve().parent
_CHECKOUT_ROOT = _PACKAGE_DIR.parents[1]


def _user_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "edit-videos"


def _detect_data_dir() -> Path:
    explicit = os.environ.get("EDIT_VIDEOS_HOME", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    # Source checkout (git clone / installer layout): keep data next to the code, as before.
    if (_CHECKOUT_ROOT / "pyproject.toml").is_file():
        return _CHECKOUT_ROOT
    return _user_data_dir()


# Real environment variables win; then ./.env; then the data dir's .env.
load_dotenv(Path.cwd() / ".env")
DATA_DIR: Path = _detect_data_dir()
load_dotenv(DATA_DIR / ".env")


def _detect_work_dir() -> Path:
    if "COLAB_RELEASE_TAG" in os.environ:
        return Path("/content/output")
    return Path(os.getenv("WORK_DIR", "./output")).resolve()


WORK_DIR: Path = _detect_work_dir()
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

_PLATFORM_FONTS = {"win32": "Yu Gothic", "darwin": "Hiragino Sans"}


def step_dir(step: str) -> Path:
    """Return WORK_DIR/{step}/, creating it if needed."""
    p = WORK_DIR / step
    p.mkdir(parents=True, exist_ok=True)
    return p


@cache
def _fontconfig_japanese_font() -> str:
    preferred = "Noto Sans CJK JP"
    try:
        listing = subprocess.run(
            ["fc-list", ":lang=ja", "family"], capture_output=True, text=True, encoding="utf-8", errors="replace"
        ).stdout
    except OSError:
        return preferred
    families = [line.split(",")[0].replace("\\", "").strip() for line in listing.splitlines() if line.strip()]
    if not families or preferred in families:
        return preferred
    # drawtext has no glyph fallback, so a missing font would render Japanese as boxes.
    for candidate in ("Noto Sans JP", "IPAGothic", "IPAexGothic", "TakaoGothic", "VL Gothic"):
        if candidate in families:
            return candidate
    return sorted(families)[0]


def default_font() -> str:
    """Return the subtitle font: SUBTITLE_FONT env, else a Japanese font installed on this OS."""
    explicit = os.getenv("SUBTITLE_FONT", "").strip()
    if explicit:
        return explicit
    return _PLATFORM_FONTS.get(sys.platform) or _fontconfig_japanese_font()


def uploads_dir() -> Path:
    """Return the local web server's upload directory, creating it if needed."""
    p = DATA_DIR / "uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def jobs_dir() -> Path:
    """Return the local web server's per-job output root, creating it if needed."""
    p = DATA_DIR / "output" / "jobs"
    p.mkdir(parents=True, exist_ok=True)
    return p

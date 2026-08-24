"""Centralized config + Colab/local path resolution."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _detect_work_dir() -> Path:
    if "COLAB_RELEASE_TAG" in os.environ:
        return Path("/content/output")
    return Path(os.getenv("WORK_DIR", "./output")).resolve()


WORK_DIR: Path = _detect_work_dir()
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# Local LLM (llama.cpp HTTP server, OpenAI-compatible)
LOCAL_LLM_URL: str = os.getenv("LOCAL_LLM_URL", "http://localhost:8080")
LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "local-model")  # llama.cpp ignores model name
LOCAL_LLM_TIMEOUT: int = int(os.getenv("LOCAL_LLM_TIMEOUT", "120"))


def step_dir(step: str) -> Path:
    """Return WORK_DIR/{step}/, creating it if needed."""
    p = WORK_DIR / step
    p.mkdir(parents=True, exist_ok=True)
    return p

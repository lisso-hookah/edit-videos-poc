"""Whisper transcription via faster-whisper."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .. import config


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word]


def transcribe(audio_path: Path, language: str = "ja") -> list[Segment]:
    """Run Whisper on an audio file and return segments with word-level timestamps."""
    device, compute_type = _select_runtime()
    try:
        return _run(audio_path, language, device, compute_type)
    except Exception as exc:
        if device != "cuda" or os.getenv("WHISPER_DEVICE", "").strip().lower() == "cuda":
            raise
        # A visible GPU does not guarantee usable cuBLAS/cuDNN; finish on CPU rather than fail the job.
        print(f"[warn] GPU での文字起こしに失敗したため CPU で再実行します: {str(exc).splitlines()[0]}", flush=True)
        return _run(audio_path, language, "cpu", "int8")


def _run(audio_path: Path, language: str, device: str, compute_type: str) -> list[Segment]:
    from faster_whisper import WhisperModel  # heavy: lazy import

    model = WhisperModel(config.WHISPER_MODEL, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )
    out: list[Segment] = []
    for seg in segments:
        words = [Word(w.start, w.end, w.word) for w in (seg.words or [])]
        out.append(Segment(seg.start, seg.end, seg.text, words))
    return out


def _select_runtime() -> tuple[str, str]:
    forced = os.getenv("WHISPER_DEVICE", "").strip().lower()
    compute = os.getenv("WHISPER_COMPUTE_TYPE", "").strip()
    if forced == "cpu":
        return "cpu", compute or "int8"
    if forced == "cuda":
        _register_cuda_wheels()
        return "cuda", compute or "float16"
    if _torch_has_cuda() or (_register_cuda_wheels() and _ctranslate2_sees_gpu()):
        return "cuda", compute or "float16"
    return "cpu", compute or "int8"


def _torch_has_cuda() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def _ctranslate2_sees_gpu() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def _register_cuda_wheels() -> bool:
    """Make cuBLAS/cuDNN from the `gpu` extra (nvidia-*-cu12 wheels) loadable; False if not installed."""
    import importlib.util

    try:
        spec = importlib.util.find_spec("nvidia")
    except ImportError:
        return False
    roots = [Path(p) for p in (spec.submodule_search_locations or [])] if spec else []
    lib_dirs = [d for root in roots for name in ("cublas", "cudnn") for d in (root / name / "bin", root / name / "lib") if d.is_dir()]
    if not lib_dirs:
        return False
    if sys.platform.startswith("win"):
        for d in lib_dirs:
            os.add_dll_directory(str(d))
            os.environ["PATH"] = f"{d}{os.pathsep}{os.environ.get('PATH', '')}"
    else:
        # LD_LIBRARY_PATH is read at process start, so preload by absolute path instead.
        import ctypes

        for d in lib_dirs:
            for lib in sorted(d.glob("lib*.so*")):
                try:
                    ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass
    return True

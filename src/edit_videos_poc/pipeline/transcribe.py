"""Whisper transcription via faster-whisper."""
from __future__ import annotations

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
    from faster_whisper import WhisperModel  # heavy: lazy import

    device, compute_type = _select_runtime()
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
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except ImportError:
        pass
    return "cpu", "int8"

"""Detect silent ranges via ffmpeg silencedetect filter."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ._ffmpeg import run_ffmpeg


@dataclass
class SilentRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def detect_silence(
    audio_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
) -> list[SilentRange]:
    """Detect silent ranges (seconds) below noise_db lasting at least min_duration."""
    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-",
    ]
    log = run_ffmpeg(cmd)
    return _parse_silence_log(log)


_START_RE = re.compile(r"silence_start: ([\d.]+)")
_END_RE = re.compile(r"silence_end: ([\d.]+)")


def _parse_silence_log(log: str) -> list[SilentRange]:
    starts = [float(m.group(1)) for m in _START_RE.finditer(log)]
    ends = [float(m.group(1)) for m in _END_RE.finditer(log)]
    return [SilentRange(s, e) for s, e in zip(starts, ends)]

"""Extract audio track from video for Whisper input."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ._ffmpeg import run_ffmpeg


def extract_audio(video_path: Path, sample_rate: int = 16000) -> Path:
    """Extract mono PCM WAV (16kHz default) suitable for Whisper."""
    out_path = config.step_dir("audio") / f"{video_path.stem}.wav"
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "wav", str(out_path),
    ]
    run_ffmpeg(cmd)
    return out_path

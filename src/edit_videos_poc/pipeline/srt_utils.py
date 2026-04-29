"""SRT generation and time-shift utilities for silence-cut sync."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import srt

from .. import config
from .silence import SilentRange
from .transcribe import Segment, Word


def segments_to_srt(segments: list[Segment], out_name: str = "subs.srt") -> Path:
    """Compose SRT file from transcript segments."""
    items = [
        srt.Subtitle(
            index=i + 1,
            start=timedelta(seconds=seg.start),
            end=timedelta(seconds=seg.end),
            content=seg.text.strip(),
        )
        for i, seg in enumerate(segments)
    ]
    out_path = config.step_dir("srt") / out_name
    out_path.write_text(srt.compose(items), encoding="utf-8")
    return out_path


def shift_for_cuts(segments: list[Segment], cuts: list[SilentRange]) -> list[Segment]:
    """Shift segment timestamps to match a video where `cuts` ranges have been removed."""
    sorted_cuts = sorted(cuts, key=lambda c: c.start)

    def shift(t: float) -> float:
        removed = 0.0
        for c in sorted_cuts:
            if c.end <= t:
                removed += c.duration
            elif c.start < t < c.end:
                # Time falls inside a removed range: clamp to its start
                removed += t - c.start
                break
            else:
                break
        return t - removed

    out: list[Segment] = []
    for seg in segments:
        new_words = [Word(shift(w.start), shift(w.end), w.text) for w in seg.words]
        out.append(Segment(shift(seg.start), shift(seg.end), seg.text, new_words))
    return out

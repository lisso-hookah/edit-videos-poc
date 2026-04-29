"""SRT/ASS generation and time-shift utilities for silence-cut sync."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import srt

from .. import config
from .silence import SilentRange
from .transcribe import Segment, Word

_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Outer,{font},{size},{outer},{outer},{outer},&H00000000&,0,0,0,0,100,100,0,0,1,4,0,2,10,10,30,0
Style: Inner,{font},{size},{text},{text},{inner},&H00000000&,0,0,0,0,100,100,0,0,1,2,0,2,10,10,30,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _td_to_ass(td: timedelta) -> str:
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    cs = td.microseconds // 10000
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def segments_to_ass(
    segments: list[Segment],
    font: str = "Noto Sans CJK JP",
    font_size: int = 24,
    text_color: str = "&H0000FFFF&",
    inner_color: str = "&H00000000&",
    outer_color: str = "&H00FFFFFF&",
    out_name: str = "subs.ass",
) -> Path:
    """Compose ASS file with double-outline styling (outer/inner border layers)."""
    header = _ASS_HEADER.format(
        font=font, size=font_size,
        text=text_color, inner=inner_color, outer=outer_color,
    )
    events: list[str] = []
    for seg in segments:
        start = _td_to_ass(timedelta(seconds=seg.start))
        end = _td_to_ass(timedelta(seconds=seg.end))
        text = seg.text.strip().replace("\n", "\\N")
        events.append(f"Dialogue: 0,{start},{end},Outer,,0,0,0,,{text}")
        events.append(f"Dialogue: 1,{start},{end},Inner,,0,0,0,,{text}")
    out_path = config.step_dir("srt") / out_name
    out_path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return out_path


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

"""Gemini-based filler removal and summarization over transcript segments."""
from __future__ import annotations

import re
from functools import cache

from .. import config
from .transcribe import Segment

_BATCH_FILLER_PROMPT = """\
以下は動画の文字起こしです。各行の [番号] を保ったまま、フィラー語（えーと、あの、まあ、など）を除去し、
意味を変えずに自然な日本語にしてください。[番号] と本文だけを返し、それ以外は出力しないでください。

{text}
"""

_SUMMARY_PROMPT = "以下の文字起こしを 3〜5 行で要約してください。\n\n{text}"

_LINE_RE = re.compile(r"^\[(\d+)\]\s*(.*)")


def refine_segments(segments: list[Segment]) -> list[Segment]:
    """Remove filler words from all segments in a single Gemini call."""
    if not segments:
        return segments

    numbered = "\n".join(f"[{i}] {seg.text}" for i, seg in enumerate(segments))
    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_BATCH_FILLER_PROMPT.format(text=numbered),
    )

    refined_texts: dict[int, str] = {}
    for line in resp.text.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            refined_texts[int(m.group(1))] = m.group(2).strip()

    return [
        Segment(seg.start, seg.end, refined_texts.get(i, seg.text), seg.words)
        for i, seg in enumerate(segments)
    ]


def summarize(segments: list[Segment]) -> str:
    """Generate a short summary of the entire transcript."""
    full_text = "\n".join(seg.text for seg in segments)
    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_SUMMARY_PROMPT.format(text=full_text),
    )
    return resp.text.strip()


@cache
def _client():
    """Cached singleton: re-creating genai.Client per call closes its httpx transport via GC."""
    from google import genai  # heavy: lazy import

    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set; configure .env first")
    return genai.Client(api_key=config.GEMINI_API_KEY)

"""Gemini-based filler removal and summarization over transcript segments."""
from __future__ import annotations

from .. import config
from .transcribe import Segment

_FILLER_PROMPT = """\
以下は動画の文字起こしです。フィラー語（えーと、あの、まあ、など）を除去し、
意味を変えずに自然な日本語にしてください。タイムコードや改行は触らず、
セリフテキストだけを返してください。

入力:
{text}

出力:
"""

_SUMMARY_PROMPT = "以下の文字起こしを 3〜5 行で要約してください。\n\n{text}"


def refine_segments(segments: list[Segment]) -> list[Segment]:
    """Remove filler words from each segment via Gemini."""
    client = _client()
    refined: list[Segment] = []
    for seg in segments:
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=_FILLER_PROMPT.format(text=seg.text),
        )
        refined.append(Segment(seg.start, seg.end, resp.text.strip(), seg.words))
    return refined


def summarize(segments: list[Segment]) -> str:
    """Generate a short summary of the entire transcript."""
    full_text = "\n".join(seg.text for seg in segments)
    resp = _client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_SUMMARY_PROMPT.format(text=full_text),
    )
    return resp.text.strip()


def _client():
    from google import genai  # heavy: lazy import

    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set; configure .env first")
    return genai.Client(api_key=config.GEMINI_API_KEY)

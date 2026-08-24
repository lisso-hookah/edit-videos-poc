"""Local LLM refinement via llama.cpp HTTP server (OpenAI-compatible API).

llama-server を先に起動しておく:
    llama-server -m /path/to/model.gguf --port 8080 --ctx-size 4096

環境変数:
    LOCAL_LLM_URL   - サーバーURL (default: http://localhost:8080)
    LOCAL_LLM_MODEL - モデル名 (llama.cpp は無視するが一応渡す; default: local-model)
    LOCAL_LLM_TIMEOUT - リクエストタイムアウト秒 (default: 120)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .. import config
from .transcribe import Segment

# ── Prompts ────────────────────────────────────────────────────────────────

_FILLER_SYSTEM = (
    "あなたは日本語字幕の編集アシスタントです。"
    "与えられたテキストのフィラー語（えーと、あの、まあ、うーん、えー、など）を除去し、"
    "自然な日本語に整えてください。"
    "指示: [番号] を保ったまま本文だけ修正し、[番号] 本文 の形式で出力してください。"
    "余計な説明は不要です。"
)

_FILLER_USER = "{text}"

_TOPIC_SYSTEM = (
    "あなたは動画コンテンツの構成アナリストです。"
    "与えられた字幕テキスト（行番号付き）を読み、話題の区切りを検出してください。"
    "出力は必ず JSON 配列のみとし、他のテキストは含めないでください。"
    '形式: [{"topic": "トピック名（15文字以内）", "start_index": 0, "end_index": 10}, ...]'
)

_TOPIC_USER = (
    "以下の字幕テキストをトピックでグルーピングしてください。\n\n"
    "{text}\n\n"
    "JSON のみ出力してください。"
)

_LINE_RE = re.compile(r"^\[(\d+)\]\s*(.*)")


# ── Public types ───────────────────────────────────────────────────────────

@dataclass
class TopicGroup:
    """連続するセグメントをひとつのトピックにまとめた結果。"""
    topic: str
    segments: list[Segment]

    @property
    def start(self) -> float:
        return self.segments[0].start

    @property
    def end(self) -> float:
        return self.segments[-1].end


# ── Public functions ───────────────────────────────────────────────────────

def refine_segments_local(segments: list[Segment]) -> list[Segment]:
    """フィラー語を除去して字幕を整形する（llama.cpp 版）。"""
    if not segments:
        return segments

    numbered = "\n".join(f"[{i}] {seg.text}" for i, seg in enumerate(segments))
    raw = _chat(
        system=_FILLER_SYSTEM,
        user=_FILLER_USER.format(text=numbered),
        temperature=0.0,
        max_tokens=len(numbered) * 2 + 64,
    )

    refined: dict[int, str] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line.strip())
        if m:
            refined[int(m.group(1))] = m.group(2).strip()

    return [
        Segment(seg.start, seg.end, refined.get(i, seg.text), seg.words)
        for i, seg in enumerate(segments)
    ]


def classify_topics(segments: list[Segment]) -> list[TopicGroup]:
    """字幕全体をトピックでグルーピングする（llama.cpp 版）。

    小さいモデルでも扱いやすいよう、長い場合は 50 セグメントごとにチャンク分割して処理する。
    """
    if not segments:
        return []

    CHUNK = 50  # small models have limited context
    groups: list[TopicGroup] = []
    offset = 0

    for chunk_start in range(0, len(segments), CHUNK):
        chunk = segments[chunk_start: chunk_start + CHUNK]
        raw_groups = _classify_chunk(chunk, offset)
        groups.extend(raw_groups)
        offset += len(chunk)

    return groups


def is_available() -> bool:
    """llama.cpp サーバーが起動中か確認する（タイムアウト 2 秒）。"""
    try:
        import requests
        r = requests.get(f"{config.LOCAL_LLM_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ── Internal helpers ───────────────────────────────────────────────────────

def _classify_chunk(chunk: list[Segment], offset: int) -> list[TopicGroup]:
    numbered = "\n".join(f"[{offset + i}] {seg.text}" for i, seg in enumerate(chunk))
    raw = _chat(
        system=_TOPIC_SYSTEM,
        user=_TOPIC_USER.format(text=numbered),
        temperature=0.1,
        max_tokens=1024,
    )

    # Extract JSON from model output (may contain ```json ... ``` wrapper)
    json_str = _extract_json(raw)
    try:
        items: list[dict[str, Any]] = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: treat the whole chunk as one topic
        return [TopicGroup(topic="(未分類)", segments=chunk)]

    result: list[TopicGroup] = []
    for item in items:
        topic = str(item.get("topic", "(未分類)"))
        s_idx = int(item.get("start_index", offset)) - offset
        e_idx = int(item.get("end_index", offset + len(chunk) - 1)) - offset
        s_idx = max(0, min(s_idx, len(chunk) - 1))
        e_idx = max(s_idx, min(e_idx, len(chunk) - 1))
        result.append(TopicGroup(topic=topic, segments=chunk[s_idx: e_idx + 1]))

    return result if result else [TopicGroup(topic="(未分類)", segments=chunk)]


def _chat(system: str, user: str, temperature: float = 0.0, max_tokens: int = 2048) -> str:
    """OpenAI-compatible chat completion via llama.cpp server."""
    import requests  # lazy: heavy only if called

    url = f"{config.LOCAL_LLM_URL}/v1/chat/completions"
    payload = {
        "model": config.LOCAL_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=config.LOCAL_LLM_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _extract_json(text: str) -> str:
    """モデル出力から JSON 部分だけを取り出す。"""
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    # Find first [ ... ] block
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return m.group(0) if m else text.strip()

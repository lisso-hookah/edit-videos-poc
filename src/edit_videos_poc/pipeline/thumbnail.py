"""Thumbnail generation via OpenAI gpt-image-2."""
from __future__ import annotations

import base64
import os
from pathlib import Path

from .. import config

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "gpt-image-2")


def generate_thumbnail(summary: str, out_name: str = "thumbnail.png") -> Path:
    """Generate a 16:9 thumbnail image from a video summary using gpt-image-2."""
    from openai import OpenAI  # heavy: lazy import

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set; configure .env first")

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        f"YouTube動画のサムネイル画像。内容: {summary}\n"
        "鮮やかで目を引くデザイン、大きなテキストなし、16:9の構図。"
    )
    resp = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size="1536x1024",
        quality="high",
        n=1,
        output_format="png",
    )

    out_path = config.step_dir("thumbnail") / out_name
    image_data = resp.data[0].b64_json
    out_path.write_bytes(base64.b64decode(image_data))
    return out_path

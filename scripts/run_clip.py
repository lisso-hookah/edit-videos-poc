#!/usr/bin/env python3
"""Clip a video at specified times with optional top/bottom text overlays."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Clip video with optional text overlays")
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("--start", required=True, help="Start time (seconds or HH:MM:SS)")
    parser.add_argument("--end", default=None, help="End time (seconds or HH:MM:SS)")
    parser.add_argument("--duration", type=float, default=None, help="Clip duration in seconds")
    parser.add_argument("--top-text", default=None, help="Text shown at top center")
    parser.add_argument("--bottom-text", default=None, help="Text shown at bottom center")
    parser.add_argument("--text-color", default="white", help="Text color (white / yellow / red / etc.)")
    parser.add_argument("--font", default=None, help="Font name")
    parser.add_argument("--font-size", type=int, default=48)
    args = parser.parse_args()

    from edit_videos_poc.pipeline.clip import clip_video

    video = args.video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video}")

    kwargs: dict = {
        "start": args.start,
        "text_color": args.text_color,
        "font_size": args.font_size,
    }
    if args.end:
        kwargs["end"] = args.end
    if args.duration:
        kwargs["duration"] = args.duration
    if args.top_text:
        kwargs["top_text"] = args.top_text
    if args.bottom_text:
        kwargs["bottom_text"] = args.bottom_text
    if args.font:
        kwargs["font"] = args.font

    print(f"[clip] {video.name}  {args.start} → {args.end or f'+{args.duration}s'}")
    final = clip_video(video, **kwargs)
    print(f"[clip] Done: {final}")


if __name__ == "__main__":
    main()

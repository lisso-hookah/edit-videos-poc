#!/usr/bin/env python3
"""Run the full video editing pipeline end-to-end."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the video editing pipeline")
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("--language", default="ja", help="Transcription language (default: ja)")
    parser.add_argument("--noise-db", type=float, default=-30.0, help="Silence threshold in dB")
    parser.add_argument("--min-silence", type=float, default=0.5, help="Minimum silence duration (s)")
    parser.add_argument("--skip-refine", action="store_true", help="Skip Gemini refinement step")
    parser.add_argument("--font", default=None, help="Subtitle font name")
    parser.add_argument("--font-color", default="yellow", help="字幕文字色 (yellow / white / red / black など)")
    parser.add_argument("--subtitle-style", default="default", help="字幕スタイルプリセット (default/news/pop/karaoke/minimal/telop/neon)")
    parser.add_argument("--subtitle-position", default="bottom", help="字幕位置 (bottom/top/middle/lower-third/upper-third)")
    parser.add_argument("--thumbnail", action="store_true", help="Generate thumbnail image via gpt-image-2")
    args = parser.parse_args()

    from edit_videos_poc.pipeline.audio import extract_audio
    from edit_videos_poc.pipeline.silence import detect_silence
    from edit_videos_poc.pipeline.transcribe import transcribe
    from edit_videos_poc.pipeline.refine import refine_segments, summarize
    from edit_videos_poc.pipeline.srt_utils import segments_to_ass, shift_for_cuts
    from edit_videos_poc.pipeline.render import cut_silence, burn_subtitles

    video = args.video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video}")

    print(f"[pipeline] Input: {video}")

    print("[1/6] Extracting audio...")
    audio = extract_audio(video)

    print("[2/6] Transcribing...")
    segments = transcribe(audio, language=args.language)
    print(f"       {len(segments)} segments")

    print("[3/6] Detecting silence...")
    cuts = detect_silence(audio, noise_db=args.noise_db, min_duration=args.min_silence)
    print(f"       {len(cuts)} silent ranges")

    if args.skip_refine:
        refined = segments
        print("[4/6] Skipping Gemini refinement (--skip-refine)")
    else:
        print("[4/6] Refining with Gemini...")
        refined = refine_segments(segments)

    print("[5/6] Generating ASS subtitles...")
    shifted = shift_for_cuts(refined, cuts)
    ass_kwargs: dict = {"text_color": args.font_color}
    if args.font:
        ass_kwargs["font"] = args.font
    sub_path = segments_to_ass(shifted, **ass_kwargs)
    print(f"       ASS: {sub_path}")

    print("[6/6] Rendering...")
    cut_video = cut_silence(video, cuts)
    final = burn_subtitles(cut_video, sub_path)

    if args.thumbnail:
        print("[7/7] Generating thumbnail...")
        from edit_videos_poc.pipeline.thumbnail import generate_thumbnail
        summary = summarize(refined)
        thumb = generate_thumbnail(summary)
        print(f"       Thumbnail: {thumb}")

    print(f"\n[pipeline] Done! Output: {final}")


if __name__ == "__main__":
    main()

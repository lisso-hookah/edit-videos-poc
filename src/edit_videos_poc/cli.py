"""`edit-videos` command: local web UI (default) and the pipeline subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SUBCOMMANDS = ("serve", "pipeline", "short", "clip", "doctor")


def _add_subtitle_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("--language", default="ja", help="Transcription language (default: ja)")
    parser.add_argument("--noise-db", type=float, default=-30.0, help="Silence threshold in dB")
    parser.add_argument("--min-silence", type=float, default=0.5, help="Minimum silence duration (s)")
    parser.add_argument("--skip-refine", action="store_true", help="Skip Gemini refinement step")
    parser.add_argument("--font", default=None, help="Subtitle font name")
    parser.add_argument("--font-color", default="yellow", help="字幕文字色 (yellow / white / red / black など)")
    parser.add_argument("--font-size", type=int, default=48, help="字幕フォントサイズ")
    parser.add_argument("--subtitle-position", type=int, default=2, help="ASS alignment 1-9 (2=下部中央)")
    parser.add_argument("--bold", action="store_true", help="字幕太字")
    parser.add_argument("--italic", action="store_true", help="字幕斜体")
    parser.add_argument("--outline-size", type=int, default=2, help="アウトライン太さ 0-8")
    parser.add_argument("--box-background", action="store_true", help="字幕ボックス背景 (Netflix 風)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="edit-videos", description="無音カット・文字起こし・字幕焼き込み")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="ローカル Web UI を起動（サブコマンド省略時の既定）")
    serve.add_argument("--host", default="127.0.0.1", help="待ち受けアドレス（LAN に公開するなら 0.0.0.0）")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--no-browser", action="store_true", help="起動時にブラウザを開かない")

    pipeline = sub.add_parser("pipeline", help="横動画: 無音カット + 字幕焼き込み")
    _add_subtitle_args(pipeline)
    pipeline.add_argument("--thumbnail", action="store_true", help="Generate thumbnail image via gpt-image-2")

    short = sub.add_parser("short", help="縦型 9:16 ショート: 字幕 + 縦変換")
    _add_subtitle_args(short)
    short.add_argument("--blur-sigma", type=int, default=40, help="Background blur strength (default: 40)")
    short.add_argument("--bg-color", default=None, help="単色背景色 (black / white / など)")
    short.add_argument("--bg-image", default=None, type=Path, help="背景に使う静止画パス（ぼかし適用）")

    clip = sub.add_parser("clip", help="切り抜き + 上下テキスト")
    clip.add_argument("video", type=Path, help="Input video file")
    clip.add_argument("--start", required=True, help="Start time (seconds or HH:MM:SS)")
    clip.add_argument("--end", default=None, help="End time (seconds or HH:MM:SS)")
    clip.add_argument("--duration", type=float, default=None, help="Clip duration in seconds")
    clip.add_argument("--top-text", default=None, help="Text shown at top center")
    clip.add_argument("--bottom-text", default=None, help="Text shown at bottom center")
    clip.add_argument("--text-color", default="white", help="Text color (white / yellow / red / etc.)")
    clip.add_argument("--font", default=None, help="Font name")
    clip.add_argument("--font-size", type=int, default=48)

    sub.add_parser("doctor", help="実行環境（ffmpeg / GPU / フォント / API キー）を診断")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the `edit-videos` console script."""
    argv = list(sys.argv[1:] if argv is None else argv)
    _use_utf8_stdio()
    if not argv or (argv[0] not in _SUBCOMMANDS and argv[0] not in ("-h", "--help")):
        argv = ["serve", *argv]
    args = _build_parser().parse_args(argv)
    try:
        return _HANDLERS[args.command](args) or 0
    except KeyboardInterrupt:
        return 130


def _use_utf8_stdio() -> None:
    # Japanese Windows consoles default to cp932, which cannot encode every character we print.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _resolve_video(path: Path) -> Path:
    video = path.resolve()
    if not video.exists():
        raise FileNotFoundError(f"Video not found: {video}")
    return video


def _refine(segments: list, skip: bool, step: str) -> list:
    from . import config

    if skip:
        print(f"[{step}] Skipping Gemini refinement (--skip-refine)", flush=True)
        return segments
    if not config.GEMINI_API_KEY:
        print(f"[{step}] Skipping Gemini refinement", flush=True)
        print("[warn] GEMINI_API_KEY が未設定のため、フィラー除去をスキップしました", flush=True)
        return segments
    print(f"[{step}] Refining with Gemini...", flush=True)
    try:
        from .pipeline.refine import refine_segments

        return refine_segments(segments)
    except Exception as exc:
        # Refinement is cosmetic; never throw away a finished transcription over an API error.
        reason = (str(exc).splitlines() or [type(exc).__name__])[0]
        print(f"[warn] Gemini でのフィラー除去に失敗したため、元の字幕で続行します: {reason}", flush=True)
        return segments


def _subtitled_render(args: argparse.Namespace, total: int) -> tuple[Path, list]:
    """Steps 1-6 shared by `pipeline` and `short`: returns (cut + subtitled video, refined segments)."""
    from .pipeline.audio import extract_audio
    from .pipeline.render import cut_and_burn
    from .pipeline.silence import detect_silence
    from .pipeline.srt_utils import segments_to_ass, shift_for_cuts
    from .pipeline.transcribe import transcribe

    video = _resolve_video(args.video)
    print(f"[{args.command}] Input: {video}", flush=True)

    print(f"[1/{total}] Extracting audio...", flush=True)
    audio = extract_audio(video)

    print(f"[2/{total}] Transcribing...", flush=True)
    segments = transcribe(audio, language=args.language)
    print(f"       {len(segments)} segments", flush=True)

    print(f"[3/{total}] Detecting silence...", flush=True)
    cuts = detect_silence(audio, noise_db=args.noise_db, min_duration=args.min_silence)
    print(f"       {len(cuts)} silent ranges", flush=True)

    refined = _refine(segments, args.skip_refine, f"4/{total}")

    print(f"[5/{total}] Generating ASS subtitles...", flush=True)
    sub_path = segments_to_ass(
        shift_for_cuts(refined, cuts),
        font=args.font,
        text_color=args.font_color,
        font_size=args.font_size,
        alignment=args.subtitle_position,
        bold=args.bold,
        italic=args.italic,
        outline_size=args.outline_size,
        box_background=args.box_background,
    )
    print(f"       ASS: {sub_path}", flush=True)

    print(f"[6/{total}] Rendering (silence cut + subtitles)...", flush=True)
    return cut_and_burn(video, cuts, sub_path), refined


def _cmd_pipeline(args: argparse.Namespace) -> int:
    final, refined = _subtitled_render(args, total=7 if args.thumbnail else 6)
    if args.thumbnail:
        print("[7/7] Generating thumbnail...", flush=True)
        try:
            from .pipeline.refine import summarize
            from .pipeline.thumbnail import generate_thumbnail

            print(f"       Thumbnail: {generate_thumbnail(summarize(refined))}", flush=True)
        except Exception as exc:
            reason = (str(exc).splitlines() or [type(exc).__name__])[0]
            print(f"[warn] サムネイル生成に失敗しました（動画は出力済み）: {reason}", flush=True)
    print(f"\n[pipeline] Done! Output: {final}", flush=True)
    return 0


def _cmd_short(args: argparse.Namespace) -> int:
    from .pipeline.vertical import make_vertical

    subbed, _refined = _subtitled_render(args, total=7)
    print("[7/7] Converting to vertical (9:16)...", flush=True)
    bg_image = args.bg_image.resolve() if args.bg_image else None
    final = make_vertical(subbed, blur_sigma=args.blur_sigma, bg_color=args.bg_color, bg_image=bg_image)
    print(f"\n[short] Done! Output: {final}", flush=True)
    return 0


def _cmd_clip(args: argparse.Namespace) -> int:
    from .pipeline.clip import clip_video

    video = _resolve_video(args.video)
    print(f"[clip] {video.name}  {args.start} → {args.end or f'+{args.duration}s'}", flush=True)
    final = clip_video(
        video,
        start=args.start,
        end=args.end or None,
        duration=args.duration or None,
        top_text=args.top_text or None,
        bottom_text=args.bottom_text or None,
        font=args.font,
        font_size=args.font_size,
        text_color=args.text_color,
    )
    print(f"[clip] Done: {final}", flush=True)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import socket
    import threading
    import webbrowser

    import uvicorn

    from . import config

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", args.port)) == 0:
            print(f"ポート {args.port} は使用中です。別のポートを指定してください: edit-videos --port {args.port + 1}", file=sys.stderr)
            return 1

    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    print(f"[edit-videos] {url} で起動します（Ctrl+C で終了）", flush=True)
    print(f"[edit-videos] データ保存先: {config.DATA_DIR}", flush=True)
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run("edit_videos_poc.web.app:app", host=args.host, port=args.port, reload=False)
    return 0


def _cmd_doctor(_args: argparse.Namespace) -> int:
    import subprocess

    from . import config
    from .pipeline import transcribe
    from .pipeline._ffmpeg import ffmpeg_exe

    ok = True
    try:
        exe = ffmpeg_exe()
        version = subprocess.run([exe, "-version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        filters = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        print(f"ffmpeg        : {exe}")
        print(f"                {version.stdout.splitlines()[0] if version.stdout else '(バージョン取得失敗)'}")
        for name, used_by in (("subtitles", "字幕焼き込み"), ("drawtext", "Clip のテキスト"), ("gblur", "Short の背景ぼかし")):
            present = f" {name} " in filters
            ok = ok and present
            print(f"  filter {name:<10}: {'OK' if present else f'なし（{used_by}が使えません）'}")
    except RuntimeError as exc:
        ok = False
        print(f"ffmpeg        : 見つかりません — {exc}")

    device, compute = transcribe._select_runtime()
    print(f"Whisper       : model={config.WHISPER_MODEL} device={device} compute={compute}")
    print(f"字幕フォント  : {config.default_font()}")
    print(f"GEMINI_API_KEY: {'設定済み' if config.GEMINI_API_KEY else '未設定（フィラー除去はスキップされます）'}")
    print(f"データ保存先  : {config.DATA_DIR}")
    return 0 if ok else 1


_HANDLERS = {
    "serve": _cmd_serve,
    "pipeline": _cmd_pipeline,
    "short": _cmd_short,
    "clip": _cmd_clip,
    "doctor": _cmd_doctor,
}

if __name__ == "__main__":
    raise SystemExit(main())

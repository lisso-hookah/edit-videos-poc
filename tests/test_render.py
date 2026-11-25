from __future__ import annotations

from pathlib import Path

import pytest

from edit_videos_poc.pipeline._ffmpeg import filter_path
from edit_videos_poc.pipeline.clip import clip_video
from edit_videos_poc.pipeline.render import burn_subtitles, cut_and_burn
from edit_videos_poc.pipeline.silence import SilentRange
from edit_videos_poc.pipeline.srt_utils import segments_to_ass, segments_to_srt, shift_for_cuts
from edit_videos_poc.pipeline.transcribe import Segment
from edit_videos_poc.pipeline.vertical import make_vertical

from .conftest import media_duration

SEGMENTS = [Segment(0.2, 1.0, "こんにちは", []), Segment(2.0, 2.8, "it's a test: 100%", [])]


def test_filter_path_escapes_windows_drive_and_filtergraph_syntax() -> None:
    assert filter_path(r"C:\Users\me\subs.ass") == r"C\\:/Users/me/subs.ass"
    assert filter_path("/tmp/a b/subs.ass") == "/tmp/a b/subs.ass"
    assert filter_path("/tmp/it's [a],b;c/s.ass") == r"/tmp/it\\\'s \[a\]\,b\;c/s.ass"


def test_shift_for_cuts_moves_later_segments_and_clamps_inside_a_cut() -> None:
    shifted = shift_for_cuts(
        [Segment(0.0, 1.0, "a", []), Segment(3.0, 4.0, "b", []), Segment(1.5, 2.5, "c", [])],
        [SilentRange(1.0, 2.0)],
    )
    assert [(s.start, s.end) for s in shifted] == [(0.0, 1.0), (2.0, 3.0), (1.0, 1.5)]


def test_cut_and_burn_single_pass_cuts_and_keeps_one_output(sample_video: Path, isolated_dirs: Path) -> None:
    ass = segments_to_ass(SEGMENTS)
    out = cut_and_burn(sample_video, [SilentRange(1.0, 2.0)], ass)
    assert media_duration(out) == pytest.approx(2.0, abs=0.3)
    # The web UI / workflows pick "the mp4 in rendered/": there must be exactly one.
    assert [p.name for p in out.parent.glob("*.mp4")] == ["sample_cut_subbed.mp4"]


@pytest.mark.parametrize("dirname", ["C:drive colon", "it's [a], b;c", "日本語 フォルダ"])
def test_subtitles_burn_from_awkward_paths(sample_video: Path, tmp_path: Path, dirname: str) -> None:
    folder = tmp_path / dirname
    try:
        folder.mkdir()
    except OSError:
        pytest.skip("this filesystem does not allow the directory name")
    for make in (segments_to_ass, segments_to_srt):
        sub = make(SEGMENTS)
        moved = sub.rename(folder / sub.name)
        out = burn_subtitles(sample_video, moved, out_name=f"{moved.suffix[1:]}.mp4")
        assert media_duration(out) == pytest.approx(3.0, abs=0.3)


def test_clip_end_is_an_absolute_timestamp(sample_video: Path) -> None:
    out = clip_video(sample_video, start=1, end=2, top_text="上: it's 100% \\n [a],b;", bottom_text="下")
    assert media_duration(out) == pytest.approx(1.0, abs=0.3)


@pytest.mark.parametrize("background", ["blur", "color", "image"])
def test_vertical_terminates_for_every_background(sample_video: Path, tmp_path: Path, background: str) -> None:
    kwargs: dict = {}
    if background == "color":
        kwargs["bg_color"] = "black"
    if background == "image":
        from edit_videos_poc.pipeline._ffmpeg import run_ffmpeg

        image = tmp_path / "bg.png"
        run_ffmpeg(["ffmpeg", "-y", "-i", str(sample_video), "-frames:v", "1", str(image)])
        kwargs["bg_image"] = image
    out = make_vertical(sample_video, width=180, height=320, **kwargs)
    assert media_duration(out) == pytest.approx(3.0, abs=0.3)

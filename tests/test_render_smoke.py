"""End-to-end render smoke tests against synthetic lavfi media.

Skipped entirely when ffmpeg is absent so the pure test suite stays portable.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mashup.models import EDL, Clip, Role
from mashup.render import render
from mashup.render.boundaries import ToolError
from mashup.render.cut import MissingSourceError, has_subtitles_filter, probe

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
TEXT = "Synthetic line one for the subtitle rebase. And a second sentence to wrap onto more lines."


def _run(args: list[str]) -> None:
    subprocess.run([FFMPEG, "-y", "-nostdin", "-loglevel", "error", *args], check=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    """Two 3s video clips plus one 3s audio-only file."""
    root = tmp_path_factory.mktemp("media")
    for name, freq in (("a.mp4", 440), ("b.mp4", 660)):
        _run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x240:rate=15:duration=3",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={freq}:duration=3",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(root / name),
            ]
        )
    _run(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=3",
            "-c:a",
            "aac",
            str(root / "voice.m4a"),
        ]
    )
    return root


def make_edl(*paths_and_spans) -> EDL:
    return EDL(
        strategy="test",
        prompt="smoke",
        target_duration=3.0,
        generated_at="2026-07-25T00:00:00Z",
        clips=[
            Clip(
                index=i,
                segment_id=f"seg-{i}",
                source_id=path.stem,
                source_path=str(path),
                start=start,
                end=end,
                render_start=start,
                render_end=end,
                text=TEXT,
                summary="synthetic",
                role=Role.SETUP,
                energy=0.5,
            )
            for i, (path, start, end) in enumerate(paths_and_spans, start=1)
        ],
    )


def test_renders_two_video_clips(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.2, 1.4), (media / "b.mp4", 1.0, 2.5))
    events: list[str] = []
    out = render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work", progress=events.append)

    assert out.exists() and out.stat().st_size > 0
    info = probe(out)
    assert info.has_video and info.has_audio
    assert (info.width, info.height) == (320, 240)
    # 1.2s + 1.5s of material, simple cuts.
    assert info.duration == pytest.approx(2.7, abs=0.4)
    assert events, "progress callback should be called"


def test_sidecar_subtitles_are_rebased_onto_the_output_timeline(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.0, 1.5), (media / "b.mp4", 0.0, 1.5))
    out = render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work", subtitles="sidecar")

    srt = out.with_suffix(".srt")
    assert srt.exists()
    body = srt.read_text()
    assert body.startswith("1\n00:00:00,000 --> ")
    # Second clip's cues must start after the first clip, not back at zero.
    assert "00:00:01," in body or "00:00:02," in body


def test_crossfade_shortens_the_output(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.0, 1.5), (media / "b.mp4", 0.0, 1.5))
    out = render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work", crossfade=0.5)
    # Crossfading overlaps the clips, so 1.5 + 1.5 - 0.5 rather than 3.0.
    assert probe(out).duration == pytest.approx(2.5, abs=0.4)


def test_burned_subtitles(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.0, 1.5), (media / "b.mp4", 0.0, 1.5))
    out_path = tmp_path / "out.mp4"
    if not has_subtitles_filter():
        # Homebrew's default ffmpeg ships without libass; the failure must say so.
        with pytest.raises(ToolError, match="libass"):
            render(edl, out_path, workdir=tmp_path / "work", subtitles="burn")
        return
    out = render(edl, out_path, workdir=tmp_path / "work", subtitles="burn")
    assert probe(out).duration == pytest.approx(3.0, abs=0.4)
    assert out.with_suffix(".srt").exists()  # burn also leaves the sidecar


def test_audio_only_source_gets_a_colour_card(media, tmp_path):
    edl = make_edl((media / "voice.m4a", 0.0, 2.0))
    out = render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work", subtitles="none")

    info = probe(out)
    # Whole archive is audio-only, so the renderer falls back to 720p30.
    assert info.has_video and (info.width, info.height) == (1280, 720)
    assert info.duration == pytest.approx(2.0, abs=0.4)
    assert not out.with_suffix(".srt").exists()


def test_mixed_video_and_audio_only_sources_stay_uniform(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.0, 1.2), (media / "voice.m4a", 0.0, 1.2))
    out = render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work")

    info = probe(out)
    # Target format comes from the first video source, not the default.
    assert (info.width, info.height) == (320, 240)
    assert info.duration == pytest.approx(2.4, abs=0.4)


def test_intermediates_are_reused_on_rerender(media, tmp_path):
    edl = make_edl((media / "a.mp4", 0.0, 1.2))
    work = tmp_path / "work"
    render(edl, tmp_path / "out.mp4", workdir=work, subtitles="none")
    before = {p: p.stat().st_mtime_ns for p in (work / "parts").iterdir()}

    events: list[str] = []
    render(edl, tmp_path / "out2.mp4", workdir=work, subtitles="none", progress=events.append)
    after = {p: p.stat().st_mtime_ns for p in (work / "parts").iterdir()}

    assert before == after, "unchanged clips should not be re-encoded"
    assert any("cached" in e for e in events)


def test_missing_source_lists_every_offender(tmp_path):
    edl = make_edl((tmp_path / "gone-a.mp4", 0.0, 1.0), (tmp_path / "gone-b.mp4", 0.0, 1.0))
    with pytest.raises(MissingSourceError) as excinfo:
        render(edl, tmp_path / "out.mp4", workdir=tmp_path / "work")
    assert "gone-a.mp4" in str(excinfo.value)
    assert "gone-b.mp4" in str(excinfo.value)


def test_render_accepts_a_relative_output_path(media, tmp_path, monkeypatch):
    """ffmpeg runs with cwd=workdir, so a relative output path used to resolve
    against the workdir instead of the caller's directory and fail outright."""
    monkeypatch.chdir(tmp_path)
    edl = make_edl((media / "a.mp4", 0.2, 1.4))
    out = render(edl, Path("elsewhere/out.mp4"), workdir=tmp_path / "work", subtitles="none")
    assert (tmp_path / "elsewhere" / "out.mp4").is_file()
    assert out.is_absolute(), "the returned path should be unambiguous"

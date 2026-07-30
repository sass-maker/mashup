from __future__ import annotations

import json

import pytest
from conftest import make_segment

from mashup.models import EDL, Clip, Cue, Role
from mashup.retrieve import Candidate
from mashup.shorts import (
    attach_visual_manifest,
    build_short_candidates,
    cue_window_candidates,
    validate_short_duration,
)


def cues() -> list[Cue]:
    lines = [
        "And this is earlier context.",
        "So this still needs prior context.",
        "What should founders believe?",
        "The answer starts with conviction.",
        "Chasing money is understandable.",
        "A product needs a stronger center.",
        "Use the thing instead of following narratives.",
        "Talk to real people.",
        "Ask better questions.",
        "Make one deliberate trade-off.",
        "Stay curious.",
        "And this continues elsewhere.",
    ]
    return [
        Cue(index=index, start=index * 5.0, end=(index + 1) * 5.0, text=text)
        for index, text in enumerate(lines)
    ]


def test_cue_window_is_contiguous_complete_and_target_sized():
    anchor_segment = make_segment(
        "anchor",
        start=20,
        duration=25,
        text="anchor words",
        can_open=False,
        can_end=False,
    ).model_copy(update={"cue_start": 4, "cue_end": 8})
    windows = cue_window_candidates(
        Candidate(segment=anchor_segment, relevance=0.9),
        cues(),
        target=45,
    )

    assert windows
    selected = windows[0].segment
    assert (selected.cue_start, selected.cue_end) == (2, 10)
    assert selected.duration == 45
    assert selected.text == " ".join(cue.text for cue in cues()[2:11])
    assert selected.meta.can_open and selected.meta.can_end
    assert selected.anchor_segment_id == "anchor"


def test_short_candidates_reject_missing_clean_windows():
    anchor = Candidate(segment=make_segment("anchor", start=0, duration=10), relevance=0.8)
    with pytest.raises(ValueError, match="no retrieved anchor"):
        build_short_candidates([anchor], {"ep01": cues()[:2]}, target=45)


@pytest.mark.parametrize("target", [0, 29.9, 60.1, 90])
def test_short_duration_rejects_values_outside_social_range(target):
    with pytest.raises(ValueError, match="between 30 and 60"):
        validate_short_duration(target)


def _edl(source_path: str) -> EDL:
    return EDL(
        strategy="short",
        prompt="test",
        target_duration=45,
        generated_at="2026-07-29T00:00:00Z",
        clips=[
            Clip(
                index=0,
                segment_id="segment",
                source_id="episode",
                source_title="Episode",
                source_path=source_path,
                start=0,
                end=45,
                render_start=0,
                render_end=45,
                text="spoken source",
                summary="summary",
                role=Role.CLOSER,
                energy=0.8,
            )
        ],
    )


def test_visual_manifest_is_validated_and_persisted(tmp_path):
    spoken = tmp_path / "spoken.mp3"
    image = tmp_path / "archive.mp4"
    spoken.write_bytes(b"spoken")
    image.write_bytes(b"archive")
    manifest = tmp_path / "visuals.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "clip_index": 0,
                    "mode": "motion",
                    "start": 8,
                    "end": 14,
                    "source_path": str(image),
                    "source_time": 12.5,
                    "source_title": "Public Domain Collection",
                    "source_url": "https://example.test/archive",
                }
            ]
        )
    )

    attached = attach_visual_manifest(_edl(str(spoken)), manifest)

    assert len(attached.clips[0].visuals) == 1
    assert attached.clips[0].visuals[0].source_path == str(image.resolve())
    assert attached.clips[0].visuals[0].source_time == 12.5
    assert attached.clips[0].visuals[0].mode == "motion"


def test_visual_mode_defaults_to_still_for_legacy_manifests(tmp_path):
    spoken = tmp_path / "spoken.mp3"
    image = tmp_path / "archive.mp4"
    spoken.write_bytes(b"spoken")
    image.write_bytes(b"archive")
    manifest = tmp_path / "visuals.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "clip_index": 0,
                    "start": 8,
                    "end": 14,
                    "source_path": str(image),
                    "source_title": "Public Domain Collection",
                }
            ]
        )
    )

    attached = attach_visual_manifest(_edl(str(spoken)), manifest)

    assert attached.clips[0].visuals[0].mode == "still"


def test_visual_manifest_rejects_interval_outside_clip(tmp_path):
    spoken = tmp_path / "spoken.mp3"
    image = tmp_path / "archive.mp4"
    spoken.write_bytes(b"spoken")
    image.write_bytes(b"archive")
    manifest = tmp_path / "visuals.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "clip_index": 0,
                    "start": 40,
                    "end": 50,
                    "source_path": str(image),
                    "source_title": "Public Domain Collection",
                }
            ]
        )
    )

    with pytest.raises(ValueError, match="clip 0 is 45.00s"):
        attach_visual_manifest(_edl(str(spoken)), manifest)

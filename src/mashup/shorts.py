"""Cue-level short-form selection and explicit archival visual manifests."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mashup.models import EDL, Cue, VisualInsert
from mashup.retrieve import Candidate

MIN_SHORT_DURATION = 30.0
MAX_SHORT_DURATION = 60.0
WINDOWS_PER_ANCHOR = 6
CONTEXT_SECONDS = 35.0

_CONTINUATION_START = re.compile(
    r"^(?:[-–—]\s*)?(?:"
    r"yeah|yes|yep|no|exactly|right|so|and|but|because|well|okay|ok|sure|"
    r"also|then|it|this|that|these|those|he|she|they"
    r")\b",
    re.IGNORECASE,
)
_TRAILING_CONNECTOR = re.compile(
    r"\b(?:and|but|so|because|which|to|of|for|with|like|the|a|an)\s*[,.!?-]*$",
    re.IGNORECASE,
)


class ShortPlanningError(ValueError):
    """The archive cannot produce a complete short under the duration contract."""


def validate_short_duration(target: float) -> float:
    if not MIN_SHORT_DURATION <= target <= MAX_SHORT_DURATION:
        raise ValueError(
            f"short duration must be between {MIN_SHORT_DURATION:.0f} and "
            f"{MAX_SHORT_DURATION:.0f} seconds"
        )
    return target


def _starts_cleanly(text: str) -> bool:
    stripped = text.strip()
    spoken = stripped.lstrip("-–— ").strip()
    first_alpha = next((char for char in spoken if char.isalpha()), "")
    return bool(first_alpha and first_alpha.isupper() and not _CONTINUATION_START.match(stripped))


def _ends_cleanly(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped and stripped[-1] in ".?!" and not _TRAILING_CONNECTOR.search(stripped))


def cue_window_candidates(
    anchor: Candidate,
    cues: Sequence[Cue],
    *,
    target: float,
    windows_per_anchor: int = WINDOWS_PER_ANCHOR,
) -> list[Candidate]:
    """Build complete target-sized cue windows containing an anchor's midpoint."""
    validate_short_duration(target)
    segment = anchor.segment
    midpoint = (segment.start + segment.end) / 2
    max_duration = min(MAX_SHORT_DURATION, target * 1.15)
    nearby = [
        cue
        for cue in cues
        if cue.end >= segment.start - CONTEXT_SECONDS
        and cue.start <= segment.end + CONTEXT_SECONDS
        and cue.text.strip()
    ]
    starts = [cue for cue in nearby if cue.start <= midpoint and _starts_cleanly(cue.text)]
    ends = [cue for cue in nearby if cue.end >= midpoint and _ends_cleanly(cue.text)]

    ranked: list[tuple[tuple[float, int, float], Candidate]] = []
    for first in starts:
        for last in ends:
            if last.index < first.index:
                continue
            duration = last.end - first.start
            if not MIN_SHORT_DURATION <= duration <= max_duration:
                continue
            members = [cue for cue in nearby if first.index <= cue.index <= last.index]
            if not members or members[0].index != first.index or members[-1].index != last.index:
                continue
            text = " ".join(cue.text.strip() for cue in members)
            window = segment.model_copy(
                update={
                    "id": f"short:{segment.source_id}:{first.index}-{last.index}",
                    "start": first.start,
                    "end": last.end,
                    "text": text,
                    "cue_start": first.index,
                    "cue_end": last.index,
                    "meta": segment.meta.model_copy(
                        update={"required_context": [], "can_open": True, "can_end": True}
                    ),
                    "member_segment_ids": [segment.id],
                    "anchor_segment_id": segment.id,
                }
            )
            # Prefer the requested length, then question-led openings, then a
            # little more material when two candidates are otherwise equal.
            opening = " ".join(cue.text for cue in members[:8])
            rank = (abs(duration - target), 0 if "?" in opening else 1, -duration)
            ranked.append((rank, Candidate(segment=window, relevance=anchor.relevance)))

    ranked.sort(key=lambda item: item[0])
    return [candidate for _, candidate in ranked[:windows_per_anchor]]


def build_short_candidates(
    anchors: Sequence[Candidate],
    cues_by_source: dict[str, Sequence[Cue]],
    *,
    target: float,
) -> list[Candidate]:
    """Expand retrieved anchors into unique, duration-safe cue windows."""
    validate_short_duration(target)
    unique: dict[tuple[str, int, int], Candidate] = {}
    for anchor in anchors:
        for candidate in cue_window_candidates(
            anchor,
            cues_by_source.get(anchor.segment.source_id, ()),
            target=target,
        ):
            segment = candidate.segment
            key = (segment.source_id, segment.cue_start, segment.cue_end)
            existing = unique.get(key)
            if existing is None or candidate.relevance > existing.relevance:
                unique[key] = candidate
    if not unique:
        raise ShortPlanningError("no retrieved anchor formed a complete 30-60 second cue window")
    return sorted(unique.values(), key=lambda candidate: candidate.relevance, reverse=True)


def _manifest_rows(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read visual manifest {path}: {exc}") from exc
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise ValueError("visual manifest must be a JSON array of objects")
    return raw


def attach_visual_manifest(edl: EDL, path: Path) -> EDL:
    """Validate and persist clip-relative visual decisions in an EDL copy."""
    by_index = {clip.index: clip for clip in edl.clips}
    additions: dict[int, list[VisualInsert]] = {index: [] for index in by_index}
    for position, row in enumerate(_manifest_rows(path), start=1):
        data = dict(row)
        clip_index = data.pop("clip_index", None)
        if not isinstance(clip_index, int) or clip_index not in by_index:
            raise ValueError(f"visual {position} targets unknown clip_index {clip_index!r}")
        visual = VisualInsert.model_validate(data)
        source = Path(visual.source_path).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"visual {position} source does not exist: {source}")
        clip = by_index[clip_index]
        if visual.end > clip.render_duration + 1e-6:
            raise ValueError(
                f"visual {position} ends at {visual.end:.2f}s but clip "
                f"{clip_index} is {clip.render_duration:.2f}s"
            )
        additions[clip_index].append(visual.model_copy(update={"source_path": str(source)}))

    clips = [
        clip.model_copy(update={"visuals": [*clip.visuals, *additions[clip.index]]})
        for clip in edl.clips
    ]
    return edl.model_copy(update={"clips": clips})

from __future__ import annotations

import math

import pytest

from mashup.models import Cue, Role, Segment, SegmentMeta


def make_cues(spans: list[tuple[float, float, str]], speaker: str | None = None) -> list[Cue]:
    return [
        Cue(index=i, start=s, end=e, text=t, speaker=speaker) for i, (s, e, t) in enumerate(spans)
    ]


def unit_vec(angle: float, dim: int = 8) -> list[float]:
    """A deterministic unit vector. Two vectors at a small angle are similar,
    which lets scoring tests assert on similarity without a real embedder."""
    vec = [0.0] * dim
    vec[0] = math.cos(angle)
    vec[1] = math.sin(angle)
    return vec


def make_segment(
    seg_id: str,
    *,
    source_id: str = "ep01",
    start: float = 0.0,
    duration: float = 60.0,
    angle: float = 0.0,
    role: Role = Role.DEVELOPMENT,
    energy: float = 0.5,
    topics: list[str] | None = None,
    entities: list[str] | None = None,
    required_context: list[str] | None = None,
    can_open: bool = False,
    can_end: bool = False,
    text: str = "some material",
) -> Segment:
    return Segment(
        id=seg_id,
        source_id=source_id,
        start=start,
        end=start + duration,
        text=text,
        cue_start=0,
        cue_end=1,
        meta=SegmentMeta(
            topic=topics or ["parents"],
            role=role,
            summary=f"summary for {seg_id}",
            required_context=required_context or [],
            energy=energy,
            can_open=can_open,
            can_end=can_end,
            entities=entities or [],
        ),
        embedding=unit_vec(angle),
    )


@pytest.fixture
def cosine_sim():
    def sim(a: Segment, b: Segment) -> float:
        va, vb = a.embedding or [], b.embedding or []
        dot = sum(x * y for x, y in zip(va, vb, strict=False))
        na = math.sqrt(sum(x * x for x in va)) or 1e-8
        nb = math.sqrt(sum(x * x for x in vb)) or 1e-8
        return dot / (na * nb)

    return sim

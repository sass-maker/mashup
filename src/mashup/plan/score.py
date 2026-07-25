"""Sequence scoring.

The product's claim is that *ordering* material well beats retrieving relevant
material and joining it. That claim only means something if the objective is
written down explicitly, so every term the PRD asks for lives here as a
separate 0..1 signal, and the weights that combine them are what distinguish
one planning strategy from another.

Keeping the terms separate also makes the output inspectable: an EDL carries
its own term breakdown, so a bad mashup can be diagnosed rather than guessed at.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np

from mashup.models import Role, ScoreTerms, Segment

EmbedFn = Callable[[list[str]], list[list[float]]]

# Above this cosine, two segments are the same material told twice.
REDUNDANCY_THRESHOLD = 0.82
# A required_context string is considered covered by an earlier clip at or
# above this cosine. Deliberately lenient — a false "missing context" costs a
# good clip, a false "covered" costs a moment of confusion.
CONTEXT_COVERED_THRESHOLD = 0.55
# Adjacent clips should feel connected but not repetitive.
FLOW_BAND = (0.30, 0.72)

WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    # Archive order. Sequencing is fixed, so the weights that remain are the
    # ones selection can still influence.
    "chronological": {
        "relevance": 0.30,
        "context_completeness": 0.22,
        "non_repetition": 0.16,
        "progression": 0.06,
        "escalation": 0.02,
        "callback": 0.02,
        "duration_fit": 0.14,
        "source_diversity": 0.08,
    },
    # Build to a peak.
    "escalation": {
        "relevance": 0.20,
        "context_completeness": 0.18,
        "non_repetition": 0.12,
        "progression": 0.12,
        "escalation": 0.20,
        "callback": 0.04,
        "duration_fit": 0.10,
        "source_diversity": 0.04,
    },
    # Plant early, pay off late.
    "callback": {
        "relevance": 0.20,
        "context_completeness": 0.18,
        "non_repetition": 0.10,
        "progression": 0.12,
        "escalation": 0.06,
        "callback": 0.20,
        "duration_fit": 0.10,
        "source_diversity": 0.04,
    },
    # The strawman the AI cuts must beat: relevance and nothing else.
    "semantic": {
        "relevance": 0.85,
        "context_completeness": 0.0,
        "non_repetition": 0.0,
        "progression": 0.0,
        "escalation": 0.0,
        "callback": 0.0,
        "duration_fit": 0.15,
        "source_diversity": 0.0,
    },
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _unit(vec: Sequence[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    return arr / max(float(np.linalg.norm(arr)), 1e-8)


@dataclass
class PlanContext:
    """Everything scoring needs that is not the sequence itself."""

    query_vec: list[float]
    target_duration: float
    source_ordinals: dict[str, int] = field(default_factory=dict)
    # Ordered structural beats parsed from the user's prompt, embedded.
    beat_vecs: list[list[float]] = field(default_factory=list)
    beat_labels: list[str] = field(default_factory=list)
    # required_context string -> embedding, filled by `prepare_context`.
    context_vecs: dict[str, list[float]] = field(default_factory=dict)

    def relevance_of(self, seg: Segment) -> float:
        if not seg.embedding:
            return 0.0
        return _clamp01(float(_unit(seg.embedding) @ _unit(self.query_vec)))


def prepare_context(
    ctx: PlanContext,
    segments: list[Segment],
    embed_fn: EmbedFn,
) -> PlanContext:
    """Embed every distinct required_context string once."""
    needed = sorted(
        {c.strip() for s in segments for c in s.meta.required_context if c.strip()}
        - set(ctx.context_vecs)
    )
    if needed:
        for text, vec in zip(needed, embed_fn(needed), strict=True):
            ctx.context_vecs[text] = vec
    return ctx


# ---- individual terms ---------------------------------------------------


def term_relevance(seq: list[Segment], ctx: PlanContext) -> float:
    if not seq:
        return 0.0
    return float(np.mean([ctx.relevance_of(s) for s in seq]))


def term_context_completeness(seq: list[Segment], ctx: PlanContext) -> float:
    """Fraction of clips a viewer can follow at the point they appear."""
    if not seq:
        return 0.0
    scores: list[float] = []
    for i, seg in enumerate(seq):
        reqs = [c.strip() for c in seg.meta.required_context if c.strip()]
        if not reqs:
            scores.append(1.0)
            continue
        if i == 0:
            # Nothing precedes it, so the only thing that saves it is the
            # model judging it able to open cold.
            scores.append(1.0 if seg.meta.can_open else 0.0)
            continue
        prior = [_unit(p.embedding) for p in seq[:i] if p.embedding]
        if not prior:
            scores.append(0.0)
            continue
        prior_mat = np.vstack(prior)
        covered = 0
        for req in reqs:
            vec = ctx.context_vecs.get(req)
            if vec is None:
                continue
            if float(np.max(prior_mat @ _unit(vec))) >= CONTEXT_COVERED_THRESHOLD:
                covered += 1
        scores.append(covered / len(reqs))
    return float(np.mean(scores))


def term_non_repetition(seq: list[Segment], sim: Callable[[Segment, Segment], float]) -> float:
    """Penalises both near-duplicate material and topic monotony."""
    if len(seq) < 2:
        return 1.0
    excesses: list[float] = []
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            s = sim(seq[i], seq[j])
            excesses.append(max(0.0, s - REDUNDANCY_THRESHOLD) / (1.0 - REDUNDANCY_THRESHOLD))
    duplicate_penalty = float(np.mean(excesses))

    topics = [frozenset(t.lower() for t in s.meta.topic) for s in seq]
    seen: set[frozenset[str]] = set()
    repeats = 0
    for t in topics:
        if t and t in seen:
            repeats += 1
        seen.add(t)
    topic_penalty = repeats / len(seq)

    return _clamp01(1.0 - 0.7 * duplicate_penalty - 0.3 * topic_penalty)


def term_progression(
    seq: list[Segment],
    ctx: PlanContext,
    sim: Callable[[Segment, Segment], float],
) -> float:
    """How well the sequence moves somewhere.

    With an explicit requested structure ("start with education, escalate into
    career, finish with marriage") this measures beat order and coverage. With
    no structure it falls back to flow: neighbours should be related but not
    interchangeable.
    """
    if len(seq) < 2:
        return 1.0 if seq else 0.0

    if ctx.beat_vecs:
        beats = np.vstack([_unit(b) for b in ctx.beat_vecs])
        assigned = []
        for s in seq:
            if not s.embedding:
                assigned.append(0)
                continue
            assigned.append(int(np.argmax(beats @ _unit(s.embedding))))
        ordered = sum(1 for a, b in zip(assigned, assigned[1:], strict=False) if b >= a) / (
            len(assigned) - 1
        )
        coverage = len(set(assigned)) / len(ctx.beat_vecs)
        # Landing in the final beat is what makes a structure feel delivered.
        finished = 1.0 if assigned[-1] == len(ctx.beat_vecs) - 1 else 0.0
        return _clamp01(0.5 * ordered + 0.3 * coverage + 0.2 * finished)

    lo, hi = FLOW_BAND
    mid = (lo + hi) / 2
    flows = []
    for a, b in zip(seq, seq[1:], strict=False):
        s = sim(a, b)
        # Triangular preference peaking in the middle of the band.
        flows.append(_clamp01(1.0 - abs(s - mid) / (hi - lo)))
    return float(np.mean(flows))


def term_escalation(seq: list[Segment]) -> float:
    """Rising intensity plus forward movement through the comedic arc."""
    if len(seq) < 2:
        return 0.5
    energies = np.asarray([s.meta.energy for s in seq], dtype=np.float64)
    positions = np.arange(len(seq), dtype=np.float64)
    if float(np.std(energies)) < 1e-6:
        energy_trend = 0.5
    else:
        corr = float(np.corrcoef(positions, energies)[0, 1])
        energy_trend = (corr + 1.0) / 2.0

    arcs = [s.meta.role.arc_index for s in seq]
    forward = sum(1 for a, b in zip(arcs, arcs[1:], strict=False) if b >= a) / (len(arcs) - 1)
    # A peak at the very end matters more than a smooth ramp.
    ends_high = 1.0 if energies[-1] >= float(np.max(energies)) - 0.05 else 0.0
    return _clamp01(0.5 * energy_trend + 0.3 * forward + 0.2 * ends_high)


def term_callback(seq: list[Segment]) -> float:
    """Rewards planted-then-paid-off material.

    A shared entity only counts across a gap — two adjacent clips about the
    same thing are continuation, not callback.
    """
    if len(seq) < 3:
        return 0.0
    ents = [{e.strip().lower() for e in s.meta.entities if e.strip()} for s in seq]
    hits = 0
    for j in range(2, len(seq)):
        for i in range(j - 1):
            if ents[j] & ents[i]:
                hits += 1
                break
    density = hits / (len(seq) - 2)

    bookend = 1.0 if (ents and ents[-1] & ents[0]) else 0.0
    lands = 1.0 if seq[-1].meta.role in (Role.CALLBACK, Role.CLOSER) else 0.0
    return _clamp01(0.5 * density + 0.25 * bookend + 0.25 * lands)


def term_duration_fit(seq: list[Segment], target: float) -> float:
    if target <= 0:
        return 0.0
    total = sum(s.duration for s in seq)
    return _clamp01(1.0 - abs(total - target) / target)


def term_source_diversity(seq: list[Segment]) -> float:
    """Normalised entropy over source episodes.

    A 'mashup' drawn from two episodes is a supercut; the point is breadth.
    """
    if not seq:
        return 0.0
    counts = Counter(s.source_id for s in seq)
    if len(counts) == 1:
        return 0.0
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
    return _clamp01(entropy / math.log(min(len(counts), total)))


# ---- aggregate ----------------------------------------------------------


def score_sequence(
    seq: list[Segment],
    ctx: PlanContext,
    sim: Callable[[Segment, Segment], float],
) -> ScoreTerms:
    return ScoreTerms(
        relevance=term_relevance(seq, ctx),
        context_completeness=term_context_completeness(seq, ctx),
        non_repetition=term_non_repetition(seq, sim),
        progression=term_progression(seq, ctx, sim),
        escalation=term_escalation(seq),
        callback=term_callback(seq),
        duration_fit=term_duration_fit(seq, ctx.target_duration),
        source_diversity=term_source_diversity(seq),
    )


def total_score(terms: ScoreTerms, strategy: str) -> float:
    return terms.total(WEIGHT_PROFILES[strategy])

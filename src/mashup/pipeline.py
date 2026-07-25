"""Stage orchestration.

Each stage is separately resumable and writes its result to the store, because
the expensive stages (transcription, enrichment, embedding) must never be paid
for twice while iterating on the cheap one (planning).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mashup.config import Config
from mashup.gateway import Gateway
from mashup.ingest import ingest_archive
from mashup.models import EDL, Clip, Segment, Source
from mashup.plan.planner import PlanResult, plan, plan_random, plan_semantic
from mashup.plan.prompt import MashupRequest, parse_request
from mashup.plan.score import PlanContext, prepare_context
from mashup.render.boundaries import detect_silences, snap_boundaries
from mashup.retrieve import Retriever, embed_segments
from mashup.segment.enrich import enrich_segments
from mashup.segment.splitter import split_source
from mashup.store import Store

AI_STRATEGIES = ("chronological", "escalation", "callback")


def ingest(
    archive_dir: Path,
    cfg: Config,
    *,
    allow_transcribe: bool = True,
    progress=None,
) -> dict[str, int]:
    """Ingest media + subtitles and split into segments."""
    cfg.ensure_dirs()
    with Store(cfg.db_path) as store:
        items = ingest_archive(
            archive_dir,
            workdir=cfg.workdir,
            allow_transcribe=allow_transcribe,
        )
        for source, cues in items:
            store.upsert_source(source, cues)
            store.replace_segments(source.id, split_source(source.id, cues))
        return store.counts()


# Segments per store write during enrichment. Small enough that a crash costs
# little, large enough that the write is not the bottleneck.
ENRICH_CHECKPOINT = 50


def enrich(cfg: Config, *, concurrency: int = 4, progress=None) -> dict[str, int]:
    with Store(cfg.db_path) as store:
        segments = store.get_segments(with_embeddings=False)
        todo = [s for s in segments if not s.meta.summary]
        if not todo:
            return store.counts()

        gw = Gateway(cfg)
        done = 0
        # Checkpoint to the store as we go. Holding every result until the end
        # meant one failed batch discarded the entire archive's work.
        for i in range(0, len(todo), ENRICH_CHECKPOINT):
            chunk = todo[i : i + ENRICH_CHECKPOINT]

            def chunk_progress(c: int, _t: int, base: int = done) -> None:
                if progress is not None:
                    progress(base + c, len(todo))

            # enrich_segments returns copies rather than mutating in place, so
            # the return value is the only thing carrying the new metadata.
            enriched = enrich_segments(chunk, gw, concurrency=concurrency, progress=chunk_progress)
            # Only persist segments that actually came back enriched, so a
            # failed batch stays on the todo list for the next run.
            store.update_segment_meta([s for s in enriched if s.meta.summary])
            done += len(chunk)
        return store.counts()


def embed(cfg: Config, *, progress=None, reset: bool = False) -> dict[str, int]:
    with Store(cfg.db_path) as store:
        if reset:
            store.clear_embeddings()
        segments = store.get_segments()
        gw = Gateway(cfg)
        embed_segments(segments, gw, progress=progress)
        store.update_segment_embeddings(segments)
        return store.counts()


def _clip_from_segment(
    index: int,
    seg: Segment,
    source: Source,
    store: Store,
    cfg: Config,
    *,
    snap: bool,
    crossfade: float,
) -> Clip:
    render_start, render_end = seg.start, seg.end
    if snap:
        silences = detect_silences(Path(source.path), cache_dir=cfg.cache_dir)
        cues = store.get_cues(seg.source_id)
        render_start, render_end = snap_boundaries(seg.start, seg.end, silences=silences, cues=cues)
    return Clip(
        index=index,
        segment_id=seg.id,
        source_id=seg.source_id,
        source_path=source.path,
        start=seg.start,
        end=seg.end,
        render_start=render_start,
        render_end=render_end,
        text=seg.text,
        summary=seg.meta.summary,
        role=seg.meta.role,
        energy=seg.meta.energy,
        topics=list(seg.meta.topic),
        transition="crossfade" if crossfade > 0 else "cut",
    )


def result_to_edl(
    result: PlanResult,
    request: MashupRequest,
    cfg: Config,
    store: Store,
    *,
    target: float,
    snap: bool = True,
    crossfade: float = 0.0,
) -> EDL:
    sources = {s.id: s for s in store.get_sources()}
    clips = [
        _clip_from_segment(
            i, seg, sources[seg.source_id], store, cfg, snap=snap, crossfade=crossfade
        )
        for i, seg in enumerate(result.sequence)
    ]
    from mashup.plan.score import WEIGHT_PROFILES

    return EDL(
        strategy=result.strategy,
        prompt=request.prompt,
        target_duration=target,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        clips=clips,
        score=result.score,
        terms=result.terms,
        weights=WEIGHT_PROFILES.get(result.strategy, {}),
        rationale=result.rationale,
    )


def make_mashups(
    prompt: str,
    cfg: Config,
    *,
    target: float,
    strategies: tuple[str, ...] = AI_STRATEGIES,
    include_baselines: bool = False,
    pool: int = 40,
    snap: bool = True,
    crossfade: float = 0.0,
) -> list[EDL]:
    """Plan one EDL per strategy from an already-enriched archive."""
    gw = Gateway(cfg)
    request = parse_request(prompt, gw)

    with Store(cfg.db_path) as store:
        segments = store.get_segments()
        retriever = Retriever(segments)
        sources = {s.id: s for s in store.get_sources()}

        query_vec = gw.embed([request.query])[0]
        beat_vecs = gw.embed(request.beats) if request.beats else []

        ctx = PlanContext(
            query_vec=query_vec,
            target_duration=target,
            source_ordinals={sid: s.ordinal for sid, s in sources.items()},
            beat_vecs=beat_vecs,
            beat_labels=list(request.beats),
        )
        # The AI strategies plan over an MMR-diversified pool, because their
        # job is to build variety out of it.
        candidates = retriever.mmr(query_vec, top_k=pool)

        # The baselines deliberately do NOT get MMR. "Retrieve the most
        # relevant clips and join them" is the thing being argued against, so
        # handing it free diversity would soften the very comparison the
        # project exists to make.
        baseline_candidates = retriever.search(query_vec, top_k=pool)

        ctx = prepare_context(
            ctx,
            [c.segment for c in candidates] + [c.segment for c in baseline_candidates],
            gw.embed,
        )

        results = [plan(s, candidates, ctx, retriever.pairwise) for s in strategies]
        if include_baselines:
            results.append(plan_semantic(baseline_candidates, ctx, retriever.pairwise))
            results.append(plan_random(baseline_candidates, ctx, retriever.pairwise))

        return [
            result_to_edl(r, request, cfg, store, target=target, snap=snap, crossfade=crossfade)
            for r in results
        ]

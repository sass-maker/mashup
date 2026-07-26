# mashup docs

Turn a creator-owned video or podcast archive into coherent themed mashups
using only clips that already exist — and find out whether structure-aware
sequencing actually beats retrieve-and-join.

## Start here

- [README](../README.md) — what it is, the thesis, install, configuration, the
  stage-by-stage commands, the dev corpus and the output layout.
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) — what is shipped, what is in
  progress, what is blocked.

## Journey and reasoning

- [decisions.md](decisions.md) — the decision log. Eleven entries covering
  SQLite over pgvector, deterministic-then-LLM segmentation, one shared beam
  search, the eight surfaced score terms, outward-only cut snapping,
  audio-over-a-card rendering, the free-ai gateway, the public-domain corpus,
  resumability, and the stdlib editor backend.
- [decisions-retrieval.md](decisions-retrieval.md) — five further entries on
  running embeddings and enrichment locally, calibrating similarity thresholds
  from the corpus instead of hard-coding them, why the callback strategy needs
  its own candidate pool, and what diffing a weak model against a strong one
  revealed about the enrichment prompt.
- [experiment.md](experiment.md) — how to run the five-condition blind
  comparison: the coverage gate, the withheld key, the rating sheet, the
  success criteria and the kill criterion with their real thresholds, and how
  `timeline_churn` measures the latter.
- [experiment-matched.md](experiment-matched.md) — the two-arm design that
  isolates sequencing by holding the clip set fixed, why its comparator is the
  median shuffle, why six viewers can only reach significance at unanimity,
  and `mashup order-test` — the mechanical proxy you run before recruiting.

## Specification

The OpenSpec change [`build-mashup-mvp`](../openspec/changes/build-mashup-mvp/)
is the authoritative scope document:

- [proposal.md](../openspec/changes/build-mashup-mvp/proposal.md) — why, what
  changes, the six capabilities, the non-goals.
- [design.md](../openspec/changes/build-mashup-mvp/design.md) — the pipeline
  diagram, the design rationale in condensed form, the dev corpus, the risks.
- [tasks.md](../openspec/changes/build-mashup-mvp/tasks.md) — the build
  checklist and the open questions.
- Capability specs, in pipeline order:
  [archive-ingestion](../openspec/changes/build-mashup-mvp/specs/archive-ingestion/spec.md),
  [segment-understanding](../openspec/changes/build-mashup-mvp/specs/segment-understanding/spec.md),
  [mashup-planning](../openspec/changes/build-mashup-mvp/specs/mashup-planning/spec.md),
  [timeline-editing](../openspec/changes/build-mashup-mvp/specs/timeline-editing/spec.md),
  [mashup-rendering](../openspec/changes/build-mashup-mvp/specs/mashup-rendering/spec.md),
  [sequencing-validation](../openspec/changes/build-mashup-mvp/specs/sequencing-validation/spec.md).

## Tooling

- [scripts/README.md](../scripts/README.md) — the licence-gated archive.org
  fetcher, its exit codes, and the licence position on the dev corpus.

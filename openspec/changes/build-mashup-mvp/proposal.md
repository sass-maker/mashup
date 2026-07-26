## Why

A comedian with fifteen recorded sets, or a podcaster with two hundred
episodes, is sitting on material that already contains a good themed set —
it is just scattered across the archive. The existing options are to edit it
by hand, which costs days, or to run semantic search and concatenate the
top hits, which produces a supercut with no shape: repeated premises,
punchlines whose setups were left behind, and no reason for clip four to
follow clip three.

The bet is that the ordering is the hard part and the valuable part. That
bet is falsifiable, so this change builds the thing *and* the experiment
that can kill it.

## What Changes

- Add a CLI that takes an archive directory plus a natural-language brief
  and emits three alternative mashups as editable EDL JSON and rendered MP4.
- Segment transcripts on speech structure rather than subtitle lines, so a
  clip carries a whole setup-and-payoff instead of an orphaned fragment.
- Extract per-segment understanding (topic, role, summary, prerequisites,
  energy, opener/closer suitability, recurring entities) with one LLM pass,
  against either a local in-process model or the fleet free-ai gateway.
- Plan sequences with an explicit, inspectable objective covering all eight
  properties the brief asks for, and expose the per-term breakdown in the
  EDL so a bad result can be diagnosed.
- Ship three strategies — chronological, escalation, callback — that share
  one beam search and differ only in weights and ordering constraints, so
  a win is attributable to the objective rather than to uneven tuning.
- Ship the two baselines (random topic-matched, semantic relevance sort)
  in the same machinery, because the comparison is the deliverable.
- Add a transcript-based timeline editor (Astro + React island, local
  Python server) with remove/reorder/replace/extend, per-clip preview, and
  EDL export.
- Render with FFmpeg: cuts snapped to nearby pauses, per-clip loudness
  normalisation, rebased subtitles, MP4 out.
- Add a blind five-condition experiment harness and a mechanical churn
  metric against the kill criterion.

## Capabilities

### New Capabilities

- `archive-ingestion`: Load a creator-owned archive of media plus subtitles,
  normalise it, and record provenance. Generate subtitles locally when the
  archive ships without them.
- `segment-understanding`: Divide transcripts into self-contained segments
  and attach the structured metadata sequencing depends on.
- `mashup-planning`: Retrieve topic-relevant segments and order them under
  an explicit multi-term objective, in three strategies plus two baselines.
- `timeline-editing`: Review and repair a generated timeline as transcript,
  with full source provenance on every clip.
- `mashup-rendering`: Cut, join, normalise, subtitle, and export.
- `sequencing-validation`: Run the blind comparison and measure the result
  against the stated success and kill criteria.

### Modified Capabilities

None — new project.

## Non-Goals

Carried from the PRD and enforced in scope:

- No fine-tuning, and no generated dialogue, narration, or footage.
- No arbitrary YouTube downloading and no third-party copyrighted archives.
  The dev corpus is public domain and the fetcher refuses `-nd` licences.
- No general-purpose video editor.
- No authentication, billing, or collaboration.
- One content domain at a time. Comedy is the target; music, code, poetry
  and stories are explicitly not simultaneously supported.

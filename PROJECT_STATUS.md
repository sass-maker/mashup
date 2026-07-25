# mashup — PROJECT STATUS

Last updated: 2026-07-25

## Why / What

Turn a creator-owned video or podcast archive into coherent themed mashups
using only clips that already exist. A comedian with fifteen recorded sets is
sitting on a good themed set that is merely scattered; the alternatives today
are days of manual editing or a semantic-search supercut with no shape.

The bet is that **ordering is the hard part and the valuable part**. Because
that bet is falsifiable, the repo builds the tool *and* the blind experiment
that can kill it. It is a validation experiment before it is a product.

**Users:** solo creators with a single-owner archive — stand-ups, podcasters,
long-running YouTubers — plus the owner running the validation study.

**IN scope:** archive ingestion with local transcription; structure-aware
segmentation; LLM segment understanding; multi-term sequence planning in three
strategies plus two baselines; an EDL as the editable document; a transcript
timeline editor; FFmpeg rendering; the five-condition blind experiment.

**OUT of scope:** fine-tuning; generated dialogue, narration or footage;
arbitrary YouTube downloading or third-party copyrighted archives; a
general-purpose video editor; auth, billing, collaboration; more than one
content domain at a time (comedy is the target).

## Dependencies

### External

- Python 3.11+, managed with `uv`.
- FFmpeg — `ffmpeg` and `ffprobe` on `PATH`. Burn-in subtitles additionally
  need a libass-enabled build.
- Runtime packages: httpx, numpy, pydantic, python-dotenv, rich, tenacity, typer.
- Optional transcription: installed `whisperkit-cli` with a local CoreML model
  (preferred) or the `transcribe` extra with mlx-whisper (Apple silicon only).
- archive.org — source of the public-domain dev corpus (`ybylcollection`).
- Editor UI: Node 22 + pnpm, Astro 5 + a React 19 island (`web/`).

### Internal

- Fleet free-ai gateway (`https://ai-gateway.sassmaker.com`), OpenAI-compatible.
  Chat and embeddings both route through it; this repo holds no provider keys.
- `MASHUP_GATEWAY_API_KEY` — from the fleet Infisical `free-ai` project.

## Timeline

- 2026-07-25 — repo scaffolded; OpenSpec change `build-mashup-mvp` written.
- 2026-07-25 — Python pipeline built end to end in-repo: ingest, segment,
  enrich, embed, retrieve, plan, EDL, render, editor server, experiment
  harness. 162 unit tests passing.
- 2026-07-25 — Astro + React transcript editor built under `web/`.
- 2026-07-25 — six capability specs, README and learning docs written.
- 2026-07-25 — verified the three validation CLI surfaces
  (`experiment`, `evaluate`, `churn`), all 178 Python tests, Ruff, the Astro
  editor build, and strict OpenSpec validation.
- 2026-07-25 — added an optional WhisperKit CLI backend for faster local
  transcription, retained mlx-whisper fallback, stripped Whisper control
  tokens before segmentation, and added direct backend/atomic-output tests.
  A five-minute archive slice froze WhisperKit chunking to `none`: VAD emitted
  49% duplicate cues versus 2% genuine audio repeats without chunking.
- Next — run the pipeline end to end against the real Groucho archive, exercise
  the editor against its real media, then run the blind comparison.

## Products

- `mashup` CLI (`uv run mashup`) — the whole pipeline. Subcommands: `ingest`,
  `enrich`, `embed`, `status`, `build`, `preview`, `render`, `serve`; the bare
  invocation `mashup --input … --prompt …` runs everything in one shot.
- `mashup serve` — loopback-only local editor server (stdlib `http.server`)
  exposing the EDL, candidate search, segment detail and range-served media,
  and serving the built editor bundle from `web/dist`.
- `web/` — the transcript timeline editor: Astro static build with a React
  island, `pnpm dev` proxying `/api` to the Python server.
- `scripts/fetch_archive.py` — licence-gated archive.org fetcher for the dev
  corpus.

## Features (shipped)

- **Ingestion** — recursive archive walk with stable slug ids and ordinals;
  `ffprobe` media probe that does not mistake cover art for video; forgiving
  SRT/VTT parsing (ASS overrides, karaoke timestamps, markup, entities, speaker
  extraction) where one bad block never costs an episode; resumable local
  WhisperKit CLI transcription with mlx-whisper fallback.
- **Segmentation** — deterministic pause/speaker atoms, then greedy grouping
  toward a target segment length that closes at the longest nearby pause and
  prefers atoms opening a new thought.
- **Segment understanding** — one batched LLM pass with neighbouring context,
  filling topic, role, summary, `required_context`, energy, `can_open`,
  `can_end` and entities; per-item fallback to neutral metadata so one bad item
  never costs a batch.
- **Gateway client** — defensive JSON parsing with a repair round-trip, batched
  embeddings with index-ordered reassembly, retries on transient status codes,
  and a content-addressed on-disk cache.
- **Planning** — MMR retrieval; eight independently tested 0..1 scoring terms;
  one shared beam search with per-strategy weight profiles; the chronological
  ordering constraint; `duration_fit` excluded during search and restored for
  final scoring; semantic and random baselines in the same machinery; brief
  parsing into query plus ordered beats with a regex fallback.
- **EDL** — pretty-printed, key-sorted JSON carrying clips, score, all eight
  term values, the weight profile and human-readable rationale; plus a
  transcript preview for review without a video player.
- **Editor server** — loopback-only; EDL read/write with renumbering, rescoring
  and atomic writes; candidate search that degrades from embeddings to token
  overlap; segment detail with neighbours; range-served media behind a
  source-id allow-list; honest partial-rescore reporting when offline.
- **Editor UI** — Astro + React transcript timeline with remove, reorder,
  replace, extend, per-clip preview, 50-deep undo, EDL export, keyboard
  navigation (`j/k`, `J/K`, `x`, `u`, `r`, `e`, `p`) and a live score header
  showing which terms were recomputed.
- **Rendering** — cached silence detection; outward-only cut snapping; per-clip
  extraction with EBU R128 loudness normalisation and cached intermediates;
  concat-demuxer join or xfade crossfades; subtitles rebased onto the output
  timeline as sidecar or burned in; audio-only clips composited over a neutral
  card.
- **Validation harness** — five-condition blind generation with a seeded label
  shuffle and a separately withheld `KEY.json`; rating sheet; unblinded
  criteria analysis; mechanical `timeline_churn` against the kill criterion.
- **Verification** — 178 unit tests across subtitles, transcription, gateway, enrichment,
  splitter, scoring, planning, boundaries, EDL I/O, editor server and the
  fetcher, plus an ffmpeg-gated render smoke test.

## Todo / Planned / Deferred / Blocked

### In progress

1. **Editor UI verification.** `web/` builds and `web/dist` exists, but the
   editor has only ever been driven against synthetic fixtures. It has not been
   exercised against a real EDL with real media.

### Planned

2. **Recruit five viewers and run the blind comparison.** The blind set is
   generated and rendered in `experiment/` (A–E plus a withheld `KEY.json`
   and a `ratings.csv` template). This is the only step that can actually
   validate the thesis; everything below is a proxy for it.
3. **Fix the callback strategy.** It scores 0.06 on its own objective while
   chronological scores 0.25 by accident (see First run below). Either the
   entity-overlap signal is too sparse on this archive, or the planner is
   not weighting it hard enough to overcome duration and relevance pressure.
4. Cross-archive validation. The kill criterion is explicitly cross-archive; a
   good Groucho result proves considerably less than it appears to.
5. `chronological` finished 100s under a 420s target because the ordering
   constraint exhausts valid candidates. Either widen the retrieval pool for
   that strategy or let it relax the constraint rather than run short.

### Deferred / open questions

5. `Source.recorded_at` is never populated; ordinals proxy chronology. Real
   creator archives may need a filename date convention parsed.
6. `ingest_archive` raises on the first unreadable file. A real archive
   probably wants to tolerate one bad file and report it.
7. `Config.media_dir` (`.mashup/media`) is created by `ensure_dirs` but nothing
   writes to it. Either give it a job or delete it.
8. Scoring weights are hand-set priors, not learned. The experiment tests
    them; the EDL term breakdown is what makes retuning tractable.

### Blocked

Nothing. The full pipeline has run end to end against the live gateway.

## First run (2026-07-25)

Prompt: *"A seven-minute set about marriage and money. Start with how couples
met, build into arguments about money, and finish with the best marriage
jokes."* The brief parsed into three ordered beats correctly.

All five conditions planned and rendered to MP4. Because each strategy is
scored under its own weight profile, the per-strategy totals are **not**
comparable; scoring every sequence under one common objective is:

| scored under | escalation obj. | callback obj. |
|---|---|---|
| escalation | **0.760** | 0.677 |
| callback | 0.741 | 0.674 |
| chronological | 0.737 | **0.679** |
| semantic (baseline) | 0.692 | 0.604 |
| random (control) | 0.683 | 0.587 |

Per-term, the separation is where the design predicted it would be:

| | context_completeness | progression |
|---|---|---|
| AI cuts | 0.95 – 1.00 | 0.68 – 0.89 |
| semantic | 0.80 | 0.58 |
| random | 0.68 | 0.60 |

**This is the machine grading its own homework and must not be read as
validation.** The planner optimises this objective, so beating the baselines
on it is close to tautological. It establishes only that the machinery works
end to end and that the strategies are genuinely differentiated. The blind
five-viewer comparison is the actual test.

Two honest negatives: the callback strategy scores 0.06 on callback while
chronological scores 0.25 incidentally, and chronological ran 100s short of
target.

Render verified: 6:50 output, valid h264/AAC, rebased sidecar SRT, and
loudness at three points drawn from different source episodes measuring
-15.6, -16.5 and -16.0 LUFS against a -16 target.

## Operational notes

- The gateway falls back between embedding providers under sustained load.
  `gemini-embedding-001` (3072d) cannot serve 727 segments; the run is pinned
  to `@cf/baai/bge-large-en-v1.5` (1024d) via `MASHUP_EMBED_MODEL`. Mixing is
  now rejected rather than silently corrupting retrieval.
- Enrichment needed four passes to drain: batches fail on gateway routing
  errors, and each pass retries only what is still missing, hitting the disk
  cache for everything already done.
- Run everything under `infisical run --silent --command '...'` with
  `MASHUP_GATEWAY_API_KEY="$Free_ai"`.

## Corpus (prepared 2026-07-25)

20 episodes of *You Bet Your Life* fetched from archive.org `ybylcollection`
(Public Domain Mark 1.0, provenance and per-file md5s in
`archive/PROVENANCE.json`). `archive/` and `.mashup/` are gitignored.

| Measure | Value |
|---|---|
| Media | 9.1 hours, 472x360 h264 + AAC |
| Cues | 10,969 (all transcribed locally; the archive ships no subtitles) |
| Segments | 727, covering 7.8 hours (86% — the rest is music and applause) |
| Segment length | mean 38s, p10 24s, p90 52s |
| Speech density | median 2.72 words/sec, min 0.62 |
| Duplicate openings | 3.3%, all genuine cross-episode show boilerplate |

Transcription runs via `whisperkit-cli` against the CoreML large-v3-turbo
model already on this machine, at roughly 24x realtime. Set
`MASHUP_WHISPERKIT_MODEL` to the model directory before `mashup ingest`.

Two transcription defects were found and fixed while preparing this corpus:
WhisperKit's VAD chunking re-emitted whole decoded windows (49% duplicate
cues), and Whisper hallucinated a stock "Thank you." over non-speech audio
(14% of segments). Both would have fed noise directly into the
`non_repetition` scoring term.

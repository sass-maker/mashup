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
- Local embeddings: the `local` extra (torch, transformers), also in the dev
  group so `uv sync` gets a working default. `BAAI/bge-base-en-v1.5` from the
  HuggingFace cache.
- Local chat: the `localchat` extra (mlx-lm), Apple silicon only, also in the
  dev group behind a platform marker.
  `mlx-community/Qwen3-4B-Instruct-2507-4bit` from the HuggingFace cache.
- Optional transcription: installed `whisperkit-cli` with a local CoreML model
  (preferred) or the `transcribe` extra with mlx-whisper (Apple silicon only).
- archive.org — source of the public-domain dev corpus (`ybylcollection`).
- Editor UI: Node 22 + pnpm, Astro 5 + a React 19 island (`web/`).

### Internal

- Fleet free-ai gateway (`https://ai-gateway.sassmaker.com`), OpenAI-compatible.
  Optional now: both chat and embeddings default to local models on Apple
  silicon, so no stage requires it. This repo holds no provider keys.
- `MASHUP_GATEWAY_API_KEY` — from the fleet Infisical `free-ai` project. Only
  needed when a stage is explicitly set back to the gateway backend.

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
- 2026-07-25 — first full end-to-end run against the real archive; five
  conditions planned and rendered. See "First run" below.
- 2026-07-25 — embeddings moved to a local HuggingFace encoder by default.
  Swapping the model exposed three defects the gateway run had hidden: fixed
  cosine thresholds fitted to one model's similarity scale, a callback term
  that counted an archive's boilerplate as running gags, and a beam search
  that preferred short sequences. See "Second run" below.
- 2026-07-26 — enrichment moved to a local mlx model, the last stage that
  needed the network. The whole pipeline now runs offline on Apple silicon.
- Next — exercise the editor against real media, regenerate the blind set,
  then run the blind comparison.

## Products

- `mashup` CLI (`uv run mashup`) — the whole pipeline. Subcommands: `ingest`,
  `enrich`, `embed`, `models`, `status`, `build`, `preview`, `render`, `serve`;
  the bare invocation `mashup --input … --prompt …` runs everything in one
  shot. On Apple silicon no subcommand needs a gateway key.
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
  `can_end` and entities; runs on a local mlx model by default; per-item
  fallback to neutral metadata so one bad item never costs a batch, and
  per-batch isolation so one bad batch never costs the archive.
- **Gateway client** — defensive JSON parsing with a repair round-trip, batched
  embeddings with index-ordered reassembly, retries on transient status codes,
  and a content-addressed on-disk cache.
- **Embedding** — one `Embedder` protocol over a local HuggingFace encoder
  (default) and the gateway; asymmetric query/document handling for the BGE
  family; a bounded in-memory cache; per-vector model identity in the store so
  a model change forces a re-embed instead of silently mixing vector spaces.
- **Planning** — MMR retrieval plus entity expansion for the callback
  strategy; eight independently tested 0..1 scoring terms with similarity
  thresholds calibrated from the candidate pool's own distribution; one shared
  beam search with per-strategy weight profiles; the chronological ordering
  constraint with archive-order branch expansion; `duration_fit` excluded
  during search and restored for final scoring, with full-length sequences
  preferred over better-scoring short ones; semantic and random baselines in
  the same machinery; brief parsing into query plus ordered beats with a regex
  fallback that also covers the no-key case.
- **EDL** — pretty-printed, key-sorted JSON carrying clips, score, all eight
  term values, the weight profile, the calibrated thresholds and
  human-readable rationale; plus a transcript preview for review without a
  video player.
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

2. **Regenerate the blind set and recruit five viewers.** The rendered set in
   `experiment/` predates the calibration and callback fixes and must be
   rebuilt before anyone watches it. Once rebuilt, this is the only step that
   can actually validate the thesis; everything below is a proxy for it.
3. `chronological` still finishes 325s against a 420s target (was 214s). The
   `can_open` filter leaves only three valid seeds in a 40-clip pool, the
   earliest at episode 3 of 20, which caps how much archive the monotonic
   constraint can spend. Widening the seed set is the obvious next move —
   `term_context_completeness` already penalises a bad opener, so the hard
   filter may be redundant.
4. Cross-archive validation. The kill criterion is explicitly cross-archive; a
   good Groucho result proves considerably less than it appears to.
5. **The callback strategy plans over a different pool than the other two.**
   Necessary — MMR removes the material callbacks need — but a confound that
   has to be reported alongside any blind-comparison result.

### Deferred / open questions

5. `Source.recorded_at` is never populated; ordinals proxy chronology. Real
   creator archives may need a filename date convention parsed.
6. `ingest_archive` raises on the first unreadable file. A real archive
   probably wants to tolerate one bad file and report it.
7. `Config.media_dir` (`.mashup/media`) is created by `ensure_dirs` but nothing
   writes to it. Either give it a job or delete it.
8. Scoring weights are hand-set priors, not learned. The calibration
    percentiles (p99, p25–p90, p25) are priors too. The experiment tests them;
    the EDL term breakdown is what makes retuning tractable.
9. `relevance` sits at 0.48–0.51 for every condition including random, so it
    is currently doing no discriminating work. Either the retrieval pool is
    already uniformly on-topic — plausible, since every candidate came from
    the same query — or the term needs rescaling against the corpus the way
    the thresholds now are.

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
target. Both were diagnosed in the second run below — the first was the
callback term measuring boilerplate rather than running gags, the second a
search objective biased toward stopping early.

Render verified: 6:50 output, valid h264/AAC, rebased sidecar SRT, and
loudness at three points drawn from different source episodes measuring
-15.6, -16.5 and -16.0 LUFS against a -16 target.

## Second run (2026-07-25, local embeddings)

Same prompt and archive, re-embedded with `BAAI/bge-base-en-v1.5`: **727
segments in 9.4 seconds**, no key and no network, against four gateway passes
before. `build` now runs offline too, since the brief parser falls back to
regex without a key.

The encoder swap is what made the next three defects visible. Each had been
sitting in the first run's numbers looking like a healthy score.

| | first run | second run |
|---|---|---|
| `non_repetition`, all conditions | 1.00 | 1.00 AI / 0.99 semantic |
| `callback` — callback strategy | 0.06 | **0.15** |
| `callback` — random control | 0.35 | **0.00** |
| `chronological` duration | 320s | 325s |

1. **Fixed cosine thresholds were fitted to one model.** bge-base puts 99.9%
   of this archive's segment pairs below 0.841, so the hard-coded 0.82
   redundancy cut fired on almost nothing and `non_repetition` returned 1.00
   for every candidate sequence — a term that had stopped measuring anything.
   Thresholds are now percentiles of the candidate pool's own distribution and
   are recorded in the EDL.
2. **The callback term was measuring noise.** It counted any shared entity,
   including the host's name (96 segments) and the sponsor (48), and counted
   repeats inside a single episode — which is the original conversation
   continuing, not something the planner built. That is how the *random*
   control was outscoring the callback strategy on callback.
3. **The beam search preferred short sequences.** `relevance` and
   `context_completeness` are means over clips, so every additional clip that
   is merely good drags them down; `duration_fit`'s weight cannot offset it.
   Full-length sequences are now preferred over better-scoring short ones, and
   chronological branches in archive order rather than leaping to the most
   relevant clip ahead of it.

Current term breakdown, same prompt:

| | relevance | context | progression | callback | duration_fit |
|---|---|---|---|---|---|
| chronological | 0.48 | 0.90 | 0.89 | 0.00 | 0.76 |
| escalation | 0.50 | 0.60 | 0.92 | 0.00 | 0.99 |
| callback | 0.50 | 0.75 | 0.91 | **0.15** | 0.96 |
| semantic (baseline) | 0.51 | 0.45 | 0.85 | 0.00 | 0.98 |
| random (control) | 0.50 | 0.33 | 0.62 | 0.00 | 0.99 |

**Still the machine grading its own homework.** The separation on
`context_completeness` and `progression` is where the design predicted it, and
callback is now the only condition scoring on callback — but the planner
optimises this objective, so none of it is evidence about what a viewer
prefers. The blind comparison remains the only real test, and the rendered set
in `experiment/` predates these fixes.

## Third run (2026-07-26, local enrichment)

`enrich` moved to `mlx-community/Qwen3-4B-Instruct-2507-4bit`, the last stage
that needed the network. 727 segments in roughly 25 minutes, offline. Metadata
changed, so every vector was re-embedded.

**The entity prompt was underspecified, and only the weak model showed it.**
See decision 16. After the rewrite:

| entities | gateway | local, before fix | local, after fix |
|---|---|---|---|
| distinct | 1,025 | 2,697 | 1,356 |
| recurring (≥2 segments) | 258 | 674 | 296 |

**Two fields are measurably worse than the gateway's**, both feeding scoring,
neither checked against a human judgement:

| | gateway | local |
|---|---|---|
| `required_context` non-empty | 76% | **100%** |
| `energy` median | 0.50 | **0.70** |
| `energy` range | 0.10–0.90 | **0.40–0.90** |

`required_context` true for every segment carries no information at all. This
is the same failure mode as a pinned term, arriving from the data side.

**The callback term's headline improved while its signal halved.**

| | second run | third run |
|---|---|---|
| `callback` — callback strategy | 0.15 | 0.32 |
| `callback` — random control | 0.00 | 0.25 |
| `chronological` duration (420s target) | 325s | **410s** |

The 0.25 floor is not a better plan. `term_callback` is
`0.5·density + 0.25·bookend + 0.25·lands`, and `lands` is a binary check on
whether the final clip's role is `callback` or `closer` — true for all five
conditions, so a quarter of the term is a constant. Decomposing 0.32 gives
density 1/7: the callback strategy found **one** cross-source callback in nine
clips, against two in the second run. Reporting the term without decomposing
it would have read as an improvement.

Two known defects, deliberately not yet fixed, because both change what all
five recorded conditions mean and the blind set depends on those definitions:

1. `lands` is an ending-quality signal that does not belong in a term named
   callback.
2. `non_repetition` is 1.00 for all five conditions including random. The
   percentile calibration from decision 14 set `redundancy` to 0.8428, the
   p99 of the pool — about 1% of pairs can exceed it, and a nine-clip plan has
   36 pairs. The term moved from always-penalised to never-fires.

Latent, not currently biting: alias fragmentation defeats the boilerplate
filter. The 5% cut drops `groucho` (66) and `desoto` (53) but not
`groucho marx` (28) or `desoto plymouth` (28). Measured zero spurious links in
the current plans, so it is recorded rather than fixed.

## Operational notes

- The whole pipeline runs offline on Apple silicon; no subcommand needs a
  gateway key. `MASHUP_CHAT_BACKEND=gateway` or `MASHUP_EMBED_BACKEND=gateway`
  opts a stage back in, and only then is a key required. Run those under
  `infisical run --silent --command '...'` with
  `MASHUP_GATEWAY_API_KEY="$Free_ai"`.
- The gateway falls back between embedding providers under sustained load,
  which is why the first run had to be pinned to `@cf/baai/bge-large-en-v1.5`
  and why vectors now carry the model that produced them.
- Enrichment needed four passes to drain: batches fail on gateway routing
  errors, and each pass retries only what is still missing, hitting the disk
  cache for everything already done.

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

# mashup — PROJECT STATUS

Last updated: 2026-07-29

## Why / What

Hand it a set of source videos and get back one coherent video that is **a
delight to watch** — extracting the good parts of each and joining them well.
Not a supercut, not a search result. Whether those sources are one creator's
own back catalogue or a folder of unrelated downloads is a difference in
provenance, not in what the tool does; ingestion reads a directory of media
files and is indifferent to where they came from.

The bet is that **ordering is the hard part and the valuable part**. That bet
is falsifiable, so the repo builds the tool *and* the blind experiment that
can kill it.

⚠️ **"A validation experiment before it is a product" is currently a trap, not
a principle.** A real-but-small ordering effect is perfectly good for a product
and impossible to prove with the study as designed. Three sessions have gone
into the apparatus and produced zero human judgments. The next action must
produce a human judgment, not a better instrument.

**Users:** one operator — the author — publishing finished cuts to their own
YouTube channel. The source is publicly readable, but there is no packaged
release, hosted service, or second operator to design for.

Three consequences, recorded because they were conflated once already:

- **The author is the only judge of the tool.** Most of the validation
  apparatus exists to make a subjective call defensible to other people. Blind
  labelling, viewer counterbalancing, sign tests and significance thresholds
  all answer "how do I convince someone else". With one operator and one taste
  the honest loop is: watch it, say whether it is good, change something. The
  underpowered-study problem dissolves rather than being solved.
- **The corpus is not licence-constrained; the uploads are.** Development
  happens locally and nothing leaves the machine, so pick source material on
  whether it tests the thesis. What actually goes up on the channel is a
  separate decision made per video — see D below.
- **No third-party rights burden.** Not shipping the software means no other
  operator can point it at anything, which is the exposure the clipping tools
  handle with terms of service.

Because there *is* a channel, the retention loop in C is a real future step
rather than a hypothetical.

**IN scope:** archive ingestion with local transcription; structure-aware
segmentation; LLM segment understanding; multi-term sequence planning in three
strategies plus two baselines; an EDL as the editable document; a transcript
timeline editor; FFmpeg rendering; the five-condition blind experiment.

**OUT of scope:** fine-tuning; generated dialogue, narration or footage;
*fetching* video — the tool reads a directory of media files and never
downloads anything, so which videos go in the folder, and the rights to use
them, stay with the operator; a general-purpose video editor; auth, billing,
collaboration.

Note this is a scope boundary on the **fetcher**, not on the input. The
pipeline itself is indifferent to where a file came from and already accepts
unrelated sources; what it has never been *tested* on is genuinely
heterogeneous material (see Planned #3).

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

- 2026-07-30 — made the canonical GitHub repository publicly readable. This is
  source visibility, not a packaged release or project-wide software license.
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
- 2026-07-26 — regenerated all five blind conditions from the fully local
  archive in `study/localchat-2026-07-26`; each EDL, sidecar, and MP4 completed.
- 2026-07-26 — verifying that set before recruiting viewers found two design
  faults: an uncounterbalanced viewing order, and a 122s duration spread that
  leaked the blinding. Both addressed; set regenerated at `--pool 160` as
  `study/localchat-2026-07-26-pool160`.
- 2026-07-26 — **that set was measuring noise.** The archive holds no airline
  material, and the flat `relevance` term had been reporting it for three runs.
  Added a measured coverage gate. Separately, the five conditions turned out to
  share 0–5% of their clips, so the design could not attribute a preference to
  sequencing at all; added a matched-pair design that can. See "Feasibility
  audit" below.
- 2026-07-29 — ran a CC0 modern-podcast pilot on four ZEROPOD episodes. The
  pipeline completed, but the first 13-clip escalation cut exposed
  mid-thought starts, context orphans, and a weak landing. Added cached
  candidate-only boundary review, bounded adjacent-segment editorial bits,
  hard integrity gates, overlap-aware planning, and EDL member provenance.
  See "Podcast editorial pilot" below.
- 2026-07-29 — made source provenance visible in exported video. Each clip now
  opens with a six-second, EDL-driven lower-third containing its episode title
  and original source time range. The dependency-free bitmap card works with
  the supported FFmpeg even though it has no `drawtext` or libass filter; use
  `--no-source-label` for a clean master.
- 2026-07-29 — upgraded provenance into persistent premium branding: a
  translucent `FROM THE ARCHIVE` source heading remains visible for the full
  clip and changes at each edit boundary, while a configurable low-opacity
  watermark stays top-right. Transparent graphics are generated as PNGs with
  the Python standard library; the ZEROPOD pilot uses `ZEROPOD`.
- 2026-07-29 — added a true short-form lane after a 45-second control returned
  107 seconds. `mashup short` now selects one complete 30–60 second window at
  stored transcript-cue boundaries, retains the eight surfaced score terms,
  and can place credited provenance-backed archival stills under the persistent
  source heading and watermark. The first ZEROPOD proof is 46.29 seconds with
  three Public Domain Mark 1.0 stills.
- 2026-07-29 — replaced the short proof's sparse held stills with continuous
  moving archival B-roll. Visual manifests now choose backward-compatible
  `still` or `motion` playback; the ZEROPOD motion proof covers all 46.29
  seconds with existing public-domain car, presenter, and road footage while
  keeping spoken-source branding and interval-bound visual credits above it.
- Next — add global beat assignment and seam selection, then compare the
  repaired cut with the original before any matched-pair viewer study.

## Podcast editorial pilot (2026-07-29)

Four ZEROPOD episodes were ingested from the show's official CC0 RSS feed into
the ignored `archive/zeropod-pilot` and `.mashup/zeropod-pilot` state. The
frozen brief was:

> A seven-minute story about how founders turn conviction into products. Start
> with the problem they noticed, move through early failures and difficult
> tradeoffs, and finish with advice about building for real people.

Coverage passed with 108 supporting segments and +0.140 lift over nonsense.
The original escalation output used 13 isolated segments over 7:07. Listening
and transcript inspection found mid-sentence starts, missing premises,
mechanical transitions, and a final clip that did not function as the requested
advice landing.

The editorial-integrity pass now:

- re-reviews only candidate-adjacent boundaries with the configured chat model;
- content-caches 260 reviewed boundaries under the ignored workdir (about four
  minutes cold, under four seconds on an unchanged repeat);
- assembles the smallest clean-opening-to-clean-ending span around each
  retrieved anchor, capped at five stored segments / 300 seconds;
- prevents different overlapping bits from reusing the same stored dialogue;
- applies the same repair to all AI strategies and both baselines; and
- writes every member segment ID into the EDL while retaining the anchor ID for
  editor compatibility. Timeline cards now show the human-readable episode
  title plus original source timecode; replacing a clip updates both.

The viable repaired escalation cut is
`output/zeropod-editorial-final/escalation-premium.mp4`: four bits, 7:18, three sources,
with complete transcript-shaped starts and endings. The reduction from 13
fragments to four complete source runs is a clear boundary improvement, but
the cut is **not publish-ready**. One bit is 182 seconds, the starts remain
conversational rather than authored hooks, and the planner still has no global
representation of the requested problem → failure/tradeoff → advice outline.
The next bottleneck is therefore outline/beat coverage and seam quality, not
another boundary-threshold retune.

The audio sources contain no embedded cover art. The compliant visual lane
uses explicit clip-relative EDL entries to hold frames or play moving footage
from the existing Public Domain Mark 1.0 `You Bet Your Life` archive, with a
separate on-screen visual credit and provenance URL. The continuous-motion
46.29-second proof is
`output/zeropod-short-proof/conviction-motion.mp4`. Automatic semantic image
selection remains out of scope; the operator supplies the licensed visual
manifest, and the renderer never downloads or generates filler.

## Feasibility audit (2026-07-26)

Four mechanical tests of the central claim, run before spending human hours.
The throwaway scripts are now `mashup order-test` (`--sweep` to choose a study
arm, `--study` to audit a set that already exists).

**1. The study prompt had no material behind it.** Nonsense text scores 0.434
against this archive over its ten best matches. `"seven minutes on airline
travel"` scored 0.459 — a lift of +0.024, with three supporting segments in
twenty episodes. `"quantum chromodynamics"` scored higher. The blind set at
`study/localchat-2026-07-26-pool160` is therefore **void**: it asks five people
to rank five piles of off-topic clips. Fixed by `mashup coverage`, which
measures the floor instead of assuming one, and which `experiment` now enforces.

**2. The five conditions do not share clips**, so the design cannot test
sequencing. Jaccard between the chronological cut and the other four: 0.00–0.05.
Fixed by `mashup experiment --matched` — one clip set, two orders.

**3. The scores were mostly made of constants.** Four of eight terms varied by
under 0.10 across all five conditions, supplying 45–67% of each AI score and
100% of both baseline scores. The baselines' weight profile is 100%
order-blind, so the 0.742-vs-0.535 headline was never evidence about ordering.

**4. The search is not broken — but this is circular.** Against 1000 shuffles
of its own clips the planner's order sat at the 99.4th / 99.9th / 100th
percentile. It was first reported here as evidence for the thesis. It is not:
beam search optimises that objective, so winning on it is expected. It says the
optimiser works. It says nothing about whether the objective matches human
taste.

**5. The study cannot detect what it is looking for.** Six viewers, one pair,
sign test — the rejection region is only 6–0 or 0–6, so power is `p⁶+(1−p)⁶`:
**12%** against a planner truly preferred 70% of the time, 26% at 80%, 53% at
90%. Roughly 40–50 judgments are needed. More pairs per person is the cheap
route, not more people.

Building the matched pair immediately exposed a latent bug — `plan` charged a
6% unfinished-ending penalty and `rescore` did not, so any rescored timeline
(including every human edit) was silently inflated. Now shared via
`ending_penalty`.

### Checked, not assumed

Claims about the multi-source goal that turned out to be **already handled**:
ingestion takes any directory of media files, so externally fetched videos work
with no new code; rendering applies per-clip EBU R128 `loudnorm` and letterboxes
every clip to a common size and fps; missing subtitles are transcribed locally.

One real gap: `_target_format` takes resolution and fps from the **first video
source**, so a low-resolution file early in a heterogeneous archive silently
downscales the entire render.

## Products

- Public source and roadmap —
  [`sarthakagrawal927/mashup`](https://github.com/sarthakagrawal927/mashup)
  and [GitHub Issues](https://github.com/sarthakagrawal927/mashup/issues).
- `mashup` CLI (`uv run mashup`) — the whole pipeline. Subcommands: `ingest`,
  `enrich`, `embed`, `models`, `status`, `coverage`, `build`, `preview`,
  `render`, `serve`, `order-test`, `experiment`, `evaluate`, `churn`;
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
- **Short-form planning** — strict 30–60 second output from contiguous stored
  transcript cues around retrieved anchors; exact cue boundaries instead of
  truncating a long editorial bit; one normal EDL with all eight score terms
  and no rewritten or generated speech.
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
  card; persistent spoken-source heading and watermark; optional
  provenance-backed still or motion inserts with interval-bound on-screen
  visual credits.
- **Validation harness** — five-condition blind generation with a seeded label
  shuffle and a separately withheld `KEY.json`; rating sheet; unblinded
  criteria analysis; mechanical `timeline_churn` against the kill criterion.
- **Verification** — 178 unit tests across subtitles, transcription, gateway, enrichment,
  splitter, scoring, planning, boundaries, EDL I/O, editor server and the
  fetcher, plus an ffmpeg-gated render smoke test.

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

After the final five failed JSON segments were retried, `mashup experiment`
completed without a gateway key and wrote five playable h264/AAC MP4s plus
sidecars and EDLs to `study/localchat-2026-07-26`. Durations span 326–450
seconds and every file is non-empty. `KEY.json` remains withheld; this proves
the real-archive machinery, not viewer preference.

## Blind set: VOID (`study/localchat-2026-07-26-pool160`)

**Do not rate this set.** Its prompt, "seven minutes on airline travel", is
indistinguishable from nonsense against this archive (+0.024 lift, three
supporting segments). See "Feasibility audit" above. Kept on disk because the
duration and counterbalancing work below is still correct and still applies to
the replacement.

Prompt "seven minutes on airline travel", seed 0, `--pool 160`. All five
render correctly — h264 + aac, 472×360, sidecar SRTs, MP4 durations matching
their EDLs.

Two design faults were found and fixed before any viewer was recruited.

**Every viewer was to watch A–E in the same order.** Position effects — the
first judged fresh and anchoring the scale, the last judged after half an hour
— would have landed entirely on one condition and been indistinguishable from
preference. The sheet now rotates per viewer, each variant taking each
position once. Carryover stays unbalanced; that needs ten viewers for five.

**The variants were unequal in length**, which leaks the blinding and means
viewers rank different amounts of material:

| pool | A chrono | B semantic | C random | D callback | E escalation | spread |
|---|---|---|---|---|---|---|
| 40 (first set) | **322.7s** | 445.2s | 396.3s | 418.6s | 424.3s | 122s |
| 160 (this set) | 416s | 450s | 423s | 413s | 406s | **44s** |

Chronological was the one starving: it can only walk forward through archive
order, so a small pool leaves it no valid continuations and the duration-band
fallback returns the best short sequence. A wider pool also widened the
AI/baseline gap — chronological 0.742 and escalation 0.751 against semantic
0.535 and random 0.503.

Widening is not a free win, which is why the default stays at 40. On the
second prompt it lifted chronological 0.781 → 0.828 but dropped the callback
strategy's callback term 0.32 → 0.06. Pool is now a `--pool` flag recorded in
`KEY.json`, chosen per run after checking durations with `--no-render`.

Residual: B (semantic) at 450s is 11% longer than E at 406s. Semantic takes
top-relevance clips until it passes the target, so it overshoots by
construction. Recorded rather than trimmed — trimming would change what the
baseline is.

The first set at `study/localchat-2026-07-26` is superseded. Use this one.

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

## Work queue

Open work is tracked only in [GitHub Issues](https://github.com/sarthakagrawal927/mashup/issues).
An open issue is a to-do, a linked pull request is in progress, and merge plus
issue closure makes the work done.

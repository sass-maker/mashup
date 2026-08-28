# Mashup

> Canonical source: this standalone repository.
>
> Mashup independently owns podcast/archive planning, resumable analysis,
> approval, and rendering. Reel Pipeline may consume a completed media receipt,
> but it does not import or execute this runtime.

## Mashup editorial planner

Turn a creator-owned video or podcast archive into coherent themed mashups
using only clips that already exist. Point it at a folder of recordings plus a
one-line brief and it emits several alternative cuts as editable EDL JSON and
rendered MP4.

Agents use the same pipeline through `uv run mashup agent`. Send a strict
`fleet.video-agent-operation.v1` request and start with `manifest`; rendering
still requires an approved editorial contract, and every generated media
receipt links back to the normalized operation identity. Mashup produces media
but never chooses or writes to a publishing channel.

The public website screens approved finished results and their provenance. It
is intentionally static: uploads, archives, rendering, approvals, and posting
remain local operator responsibilities.

Public proof: <https://mashup.highsignal.app>

## The thesis

The bet is that **ordering is the hard part**. Semantic search over an archive
is a solved, cheap thing — and it produces a supercut with no shape: repeated
premises, punchlines whose setups were left behind, and no reason for clip four
to follow clip three. mashup claims that planning the *sequence* under an
explicit objective beats retrieve-and-join.

That claim is falsifiable, so this repo is **a validation experiment before it
is a product**. It ships three AI strategies (`chronological`, `escalation`,
`callback`) and the two baselines they have to beat (`semantic`, `random`),
built on the same beam search and the same scoring code so a win is
attributable to the objective rather than to uneven tuning. See
[`docs/experiment.md`](docs/experiment.md) for the conditions, the success
criteria and the kill criterion.

Comparing those five measures the pipeline end to end — they are built from
different clips, so a preference among them cannot be pinned on ordering.
[`mashup experiment --matched`](docs/experiment-matched.md) is the design that
can: one clip set, two orders, nothing else varying.

Before either, check the archive can serve the brief at all:

```bash
uv run mashup coverage --prompt "how couples met and got married"
```

Similarity from an asymmetric encoder never approaches zero — nonsense text
scores 0.43 against the dev archive — so a topic the archive does not cover
still yields confident-looking clips. `coverage` measures that floor and
reports the brief's lift over it.

## Install

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and FFmpeg
(`ffmpeg` and `ffprobe` on `PATH` — `brew install ffmpeg`).

```bash
uv sync                        # runtime + dev deps, including local models
uv sync --extra transcribe     # adds mlx-whisper (Apple silicon only)
# Optional faster path: brew install whisperkit-cli
```

The dev group carries the local model runtimes: torch and transformers for
embeddings everywhere, and mlx-lm for chat on Apple silicon. A gateway-only
install can skip both (`--no-dev`, then `--extra local` / `--extra localchat`
as wanted).

When an archive has no subtitles, `auto` prefers an installed
`whisperkit-cli` and otherwise falls back to the optional mlx-whisper extra.
Set `MASHUP_WHISPERKIT_MODEL` to an existing local CoreML model directory to
pin the WhisperKit model explicitly. Nothing else in the pipeline loads either
backend.

## Configuration

**Every model runs locally by default.** On Apple silicon the whole pipeline —
transcription, enrichment, embedding, planning, rendering — needs no
credentials and no network. The fleet free-ai gateway remains available per
stage. Values are read from the environment or a `.env` file.

| Variable | Default | Purpose |
|---|---|---|
| `MASHUP_CHAT_BACKEND` | `local` on Apple silicon, else `gateway` | `local` runs an mlx model in-process. |
| `MASHUP_LOCAL_CHAT_MODEL` | `mlx-community/Qwen3-4B-Instruct-2507-4bit` | Any mlx-lm repo id. |
| `MASHUP_EMBED_BACKEND` | `local` | `local` runs a HuggingFace encoder in-process. |
| `MASHUP_LOCAL_EMBED_MODEL` | `bge-base` | Alias from `mashup models`, or any HuggingFace repo id. |
| `MASHUP_GATEWAY_API_KEY` | — | Gateway key. Needed only by a stage set to `gateway`. `GATEWAY_API_KEY` is an alias. |
| `MASHUP_WHISPERKIT_MODEL` | — | Optional existing CoreML model directory for `whisperkit-cli`. |
| `MASHUP_GATEWAY_URL` | `https://ai-gateway.sassmaker.com` | Gateway base URL. |
| `MASHUP_PROJECT_ID` | `mashup` | Sent on every `/v1` call. |
| `MASHUP_CHAT_MODEL` | `auto` | Gateway chat model. Only read when the chat backend is `gateway`. |
| `MASHUP_EMBED_MODEL` | `gemini-embedding-001` | Gateway embedding model. Only read when the backend is `gateway`; the gateway rejects `auto` here. |
| `MASHUP_WORKDIR` | `.mashup` | State directory. `--workdir` overrides it per command. |

`mashup models` prints which backend and model each stage would use right now,
and whether a gateway key is needed at all.

The editor server reads three more: `MASHUP_WEB_DIST` (where the built UI
lives), `MASHUP_SERVE_OFFLINE` (never attempt a gateway call) and
`MASHUP_SERVE_VERBOSE` (log requests).

Fleet operators can inject the key rather than exporting it:

```bash
infisical run --projectId <free-ai> -- mashup enrich
```

### Enrichment

The one LLM pass over the archive, filling `topic`, `role`, `summary`,
`required_context`, `energy`, `can_open`, `can_end` and `entities` per
segment. On Apple silicon it runs `Qwen3-4B-Instruct-2507-4bit` through
mlx-lm: about 25 minutes for a 727-segment archive, offline and free, and —
unlike a gateway that routes to whichever provider is cheapest this minute —
the same model every time.

Prompts go to the backend a window at a time rather than one by one, because
the two parallelise differently: the gateway wants concurrent HTTP, mlx wants
one batched forward pass. Batching is worth 1.9× locally. A batch whose reply
does not parse costs those five segments only; they keep neutral metadata and
the next `enrich` retries them, since completed segments are persisted. A full
run of the dev archive lost exactly one batch this way and a second `enrich`
picked up the five segments in under a minute.

Enrichment quality is what every scoring term reads, so the prompt is written
against the weaker model rather than the stronger one — see
[`docs/decisions-retrieval.md`](docs/decisions-retrieval.md) entry 16 for what
diffing the two revealed.

### Embeddings

Embeddings are the stage you re-run most while tuning retrieval, and the one
where a metered API hurts most. They default to a local encoder:

```bash
mashup models      # list the known aliases
mashup embed       # 727 segments in ~9s on an M-series laptop, no network
```

`bge-base` (`BAAI/bge-base-en-v1.5`, 768d) is the default. `minilm` is roughly
three times faster and a little less accurate; any HuggingFace repo id also
works, with mean pooling assumed. Models in the BGE family are used
asymmetrically — the brief and its beats get the query prefix they were
trained with, transcript segments do not.

Two things follow from making the encoder swappable:

- **Vectors record which model produced them.** Two 384-dimension models mix
  without any dimension check noticing, which corrupts retrieval silently.
  `mashup embed` re-embeds automatically when the model changes, and
  `mashup status` shows what is stored.
- **Similarity thresholds are calibrated, not hard-coded.** A fixed cosine cut
  is a claim about one model's similarity scale. Each run measures the
  redundancy, flow and context-coverage cuts from percentiles of the candidate
  pool's own distribution and records them in the EDL. See
  `docs/decisions.md`.

Set `MASHUP_EMBED_BACKEND=gateway` to compare against the hosted models.

## Quickstart

The PRD's headline invocation runs ingest, enrich, embed, plan and render in
one shot:

```bash
mashup --input ./archive --prompt "seven minutes on airline travel" --duration 420 --variants 3
```

That writes `output/chronological.{json,mp4}`, `output/escalation.{json,mp4}`
and `output/callback.{json,mp4}`.

### Stage by stage

Every stage persists to the workdir and is independently resumable, which
matters because transcription and enrichment cost real money and minutes while
planning is the stage you iterate on fifty times.

```bash
mashup ingest --input ./archive            # probe, transcribe if needed, split into segments
mashup ingest --input ./archive --no-transcribe
mashup enrich --concurrency 4              # local mlx pass -> topic/role/energy/context
mashup embed                               # local encoder -> float32 blobs in SQLite
mashup embed --reset                       # drop and recompute every vector
mashup models                              # which backend and model each stage uses
mashup status                              # counts, plus which embedder produced the vectors

mashup build --prompt "..." --duration 420 --variants 3 --output output
mashup build --prompt "..." --baselines --no-render      # add semantic + random controls
mashup build --prompt "..." --crossfade 0.4 --subtitles burn
mashup build --prompt "..." --no-snap                    # cut exactly on segment bounds

mashup short --prompt "..." --duration 45 --output output/short.mp4
mashup short --prompt "..." --visuals visuals.json --watermark-text MY_SHOW
mashup collections
mashup short-batch --collection startups --angle product-market-fit --count 5

mashup preview output/escalation.json      # transcript with source timecodes
mashup render output/escalation.json --output final.mp4 --subtitles sidecar
mashup serve output/escalation.json --port 8765          # loopback-only editor
```

`--subtitles` takes `none`, `sidecar` or `burn`; burn-in needs a libass-enabled
ffmpeg. `--variants` selects the first N of `chronological, escalation,
callback` (max 3). With both backends local no command needs a gateway key;
`build` falls back to regex brief parsing without one.

`mashup short` is a separate 30–60 second lane. It selects one contiguous
window of existing transcript cues, records the normal independent score terms,
and never rewrites or generates speech. `--visuals` accepts a JSON array of
clip-relative archival stills:

```json
[
  {
    "clip_index": 0,
    "mode": "motion",
    "start": 8,
    "end": 14,
    "source_path": "archive/public-domain-film.mp4",
    "source_time": 125.5,
    "source_title": "Public Domain Film Collection",
    "source_url": "https://archive.org/details/example"
  }
]
```

`mode` may be `still` (the backward-compatible default) or `motion`. Motion
plays existing source-video frames from `source_time`; image files remain held.
The renderer keeps the spoken-source heading and watermark visible and adds a
separate on-screen archival visual credit. Visual source paths resolve from the
current working directory and are persisted as absolute paths in the EDL.

### The Startups clipping desk

`mashup short-batch` is the first category-led operator workflow. It reuses one
already-ingested archive and prepares three to five complete, pairwise
non-overlapping social candidates for one checked-in angle:

```bash
mashup collections
mashup short-batch \
  --collection startups \
  --angle fundraising \
  --count 5 \
  --duration 45 \
  --output output/startups-fundraising
```

The Startups preset currently includes `product-market-fit`, `fundraising`,
`distribution`, `hiring`, `founder-failure`, `moats`, and
`contrarian-lessons`. Use `--prompt` for a free-form angle without changing the
collection identity or watermark.

Rendered batches use the explicit `social` profile: 1080×1920 H.264, full-frame
source fitting rather than face-blind cropping, burned captions, a source
heading, and the `STARTUPS` watermark. Each output directory contains
`clip-01...clip-05` EDL/video/caption artifacts, `batch.json`, and a standalone
`index.html` review desk. Shortlist/pass state stays in that browser's local
storage; Mashup still never publishes.

Plan without rendering when validating a corpus or when the local FFmpeg build
does not have libass:

```bash
mashup short-batch --collection startups --angle distribution --no-render
mashup render clip-01.json --output clip-01.mp4 --profile social --subtitles burn
```

The agent equivalent is `short-batch-plan`. Start with `validateOnly: true`;
the agent operation plans EDLs but does not bypass the existing approval gate
to render them.

### The transcript editor

`mashup serve` serves the built editor bundle from `web/dist`, so build it once:

```bash
cd web && pnpm install && pnpm build     # then: mashup serve output/escalation.json
cd web && pnpm dev                       # or run Astro's dev server; it proxies /api to :8765
```

The timeline is transcript-first: remove, reorder, replace and extend clips,
preview any clip in place, undo up to 50 steps, and export the EDL. Keyboard:
`j`/`k` move, `J`/`K` reorder, `x` remove, `r` replace, `e` extend, `p`
preview, `u` undo. Every save round-trips through the Python server so the
score comes back recomputed — and the header states whether the rescore was
`full` or `partial`.

## Dev corpus

`ybylcollection` on archive.org — *You Bet Your Life* with Groucho Marx, 42
MPEG4 episodes under Public Domain Mark 1.0. One creator, one archive, and a
comedy format built on running gags, which is what gives the callback strategy
something real to find. No subtitles ship with it, so ingest transcribes
locally.

```bash
python scripts/fetch_archive.py --item ybylcollection --dest ./archive --limit 20 --dry-run
python scripts/fetch_archive.py --item ybylcollection --dest ./archive --limit 20
```

The fetcher enforces the licence position rather than assuming it: it refuses
any item whose licence contains `-nd`, refuses missing or unrecognised
licences, and writes a `PROVENANCE.json` with the licence and per-file
checksums. Creators fetching their own material pass `--i-have-rights`. Full
detail in [`scripts/README.md`](scripts/README.md).

## Output layout

```
.mashup/                  # workdir (MASHUP_WORKDIR)
  mashup.db               # sources, cues, segments, metadata, embeddings
  cache/gateway/          # content-addressed LLM + embedding responses
  cache/silences-*.json   # per-file silence detection results
  subtitles/<source>.srt  # locally generated transcripts
  parts/<hash>.mp4        # cached per-clip intermediates
output/
  chronological.json      # EDL: clips, score, eight term values, weights, rationale
  chronological.mp4
  chronological.srt       # when --subtitles sidecar
```

## How it works

```
archive (mp4/mp3 + srt/vtt)
  -> ingest      normalise cues, probe media, transcribe if needed
  -> split       cues -> pause-delimited atoms -> self-contained segments
  -> enrich      one local LLM pass -> SegmentMeta per segment
  -> embed       local encoder -> float32 blobs in SQLite
  -> retrieve    MMR over cosine similarity -> candidate pool
                 (+ entity expansion for the callback strategy)
  -> plan        beam search under a weighted objective -> sequence
  -> EDL         inspectable JSON, the editor's document
  -> render      snap, cut, normalise, concat, subtitle -> MP4
```

Segments are built on speech structure, not subtitle lines, so a clip carries a
whole setup-and-payoff. Every planned sequence is scored on eight separate
0..1 terms — relevance, context completeness, non-repetition, progression,
escalation, callback, duration fit, source diversity — and all eight land in
the EDL alongside their weights, so a bad result can be diagnosed rather than
guessed at. Cuts snap outward to nearby silences, never inward, because
clipping the first syllable of a punchline is the most audible failure this
tool can produce.

The reasoning behind each of those choices is in
[`docs/decisions.md`](docs/decisions.md); the pipeline stages and risks are in
[`openspec/changes/build-mashup-mvp/design.md`](openspec/changes/build-mashup-mvp/design.md).

## Non-goals

- No fine-tuning, and no generated dialogue, narration, or footage.
- No arbitrary YouTube downloading and no third-party copyrighted archives.
- No general-purpose video editor.
- No authentication, billing, or collaboration.
- One content domain at a time. Comedy is the target; music, code, poetry and
  stories are explicitly not simultaneously supported.

## Development

```bash
uv run pytest              # 162 tests; render smoke tests skip without ffmpeg
uv run ruff check .
uv run ruff format --check .
cd web && pnpm build       # the editor bundle
```

Status, shipped features and open work: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
Docs index: [`docs/index.md`](docs/index.md).

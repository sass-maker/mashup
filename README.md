# mashup

Turn a creator-owned video or podcast archive into coherent themed mashups
using only clips that already exist. Point it at a folder of recordings plus a
one-line brief and it emits several alternative cuts as editable EDL JSON and
rendered MP4.

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

## Install

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and FFmpeg
(`ffmpeg` and `ffprobe` on `PATH` — `brew install ffmpeg`).

```bash
uv sync                        # runtime + dev deps
uv sync --extra transcribe     # adds mlx-whisper (Apple silicon only)
# Optional faster path: brew install whisperkit-cli
```

When an archive has no subtitles, `auto` prefers an installed
`whisperkit-cli` and otherwise falls back to the optional mlx-whisper extra.
Set `MASHUP_WHISPERKIT_MODEL` to an existing local CoreML model directory to
pin the WhisperKit model explicitly. Nothing else in the pipeline loads either
backend.

## Configuration

Model access goes through the fleet free-ai gateway (OpenAI-compatible), so
this project holds no provider keys of its own. Values are read from the
environment or a `.env` file.

| Variable | Default | Purpose |
|---|---|---|
| `MASHUP_GATEWAY_API_KEY` | — | Gateway key. Required by `enrich`, `embed` and `build`. `GATEWAY_API_KEY` is accepted as an alias. |
| `MASHUP_WHISPERKIT_MODEL` | — | Optional existing CoreML model directory for `whisperkit-cli`. |
| `MASHUP_GATEWAY_URL` | `https://ai-gateway.sassmaker.com` | Gateway base URL. |
| `MASHUP_PROJECT_ID` | `mashup` | Sent on every `/v1` call. |
| `MASHUP_CHAT_MODEL` | `auto` | Chat model for brief parsing and enrichment. |
| `MASHUP_EMBED_MODEL` | `gemini-embedding-001` | Embedding model. The gateway rejects `auto` here. |
| `MASHUP_WORKDIR` | `.mashup` | State directory. `--workdir` overrides it per command. |

The editor server reads three more: `MASHUP_WEB_DIST` (where the built UI
lives), `MASHUP_SERVE_OFFLINE` (never attempt a gateway call) and
`MASHUP_SERVE_VERBOSE` (log requests).

Fleet operators can inject the key rather than exporting it:

```bash
infisical run --projectId <free-ai> -- mashup build --prompt "..."
```

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
mashup enrich --concurrency 4              # LLM pass -> topic/role/energy/context per segment
mashup embed                               # gateway embeddings -> float32 blobs in SQLite
mashup status                              # sources / cues / segments / enriched / embedded

mashup build --prompt "..." --duration 420 --variants 3 --output output
mashup build --prompt "..." --baselines --no-render      # add semantic + random controls
mashup build --prompt "..." --crossfade 0.4 --subtitles burn
mashup build --prompt "..." --no-snap                    # cut exactly on segment bounds

mashup preview output/escalation.json      # transcript with source timecodes
mashup render output/escalation.json --output final.mp4 --subtitles sidecar
mashup serve output/escalation.json --port 8765          # loopback-only editor
```

`--subtitles` takes `none`, `sidecar` or `burn`; burn-in needs a libass-enabled
ffmpeg. `--variants` selects the first N of `chronological, escalation,
callback` (max 3). `ingest`, `status`, `preview`, `render` and `serve` work
without a gateway key; `enrich`, `embed` and `build` do not.

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
  -> enrich      one LLM pass -> SegmentMeta per segment
  -> embed       gateway embeddings -> float32 blobs in SQLite
  -> retrieve    MMR over cosine similarity -> candidate pool
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

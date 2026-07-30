## Shared Fleet Standard

Also read and follow the shared fleet-level agent standard at `../AGENTS.md`.
Treat this repository as owned product code: protect stability, keep changes
scoped, verify work, and record durable follow-up tasks when something remains
incomplete or blocked.

## Project

- **Stack**: Python 3.11+ (uv, typer, pydantic, httpx, numpy), FFmpeg, SQLite,
  optional whisperkit-cli or mlx-whisper transcription, Astro + a React island
  for the editor.
- **Local dev**:
  ```bash
  uv sync                      # add --extra transcribe for local whisper
  uv run pytest -q
  uv run ruff check . && uv run ruff format --check .
  cd web && pnpm install && pnpm build
  ```
- **Deploy**: none. This is a local CLI plus a loopback-only editor server.
  Nothing here is deployed to Cloudflare.

## What this is

A validation experiment before it is a product. The claim under test is that
**structure-aware sequencing produces a meaningfully better mashup than
retrieving relevant clips and joining them**. Two baselines (`semantic`,
`random`) ship in the same code path as the three AI strategies specifically
so the comparison stays honest. Read
`openspec/changes/build-mashup-mvp/design.md` before changing the planner or
the scoring terms.

## Rules specific to this repo

- **Only creator-owned or public-domain material.** `scripts/fetch_archive.py`
  refuses `-nd` licences and writes `PROVENANCE.json`. Do not add a YouTube
  downloader or bypass the licence gate.
- **No generated speech or deceptive footage.** Do not synthesise dialogue,
  narration, voice clones, or photoreal footage presented as recorded reality.
  Owner-approved procedural non-photoreal motion graphics, typography, shaders,
  and ASCII animation are allowed as a visual layer. Existing filmed or
  photographic media still requires creator ownership or recorded
  public-domain/licence provenance.
- **Model access goes through the fleet free-ai gateway.** No provider keys
  belong in this repo. See `config.py` for the env contract.
- **Expensive stages must stay resumable.** Transcription, enrichment, and
  embedding each cost real time and money; the gateway keeps an on-disk cache
  and the store keeps stage output. Do not add a code path that redoes them.
- **Scoring terms stay separate and surfaced.** Each of the eight terms is
  independently testable and lands in the EDL with its weight. Do not collapse
  them into an opaque score.
- **The `.mashup/` workdir and `archive/` are local state.** Both are ignored;
  a real archive is ~1.5 GiB and must never be committed.

## Visual work

The editor in `web/` is an operational tool: dense, scannable, accessible,
fast. It is not a marketing surface, so `../LANDING_STANDARD.md` and the
Impeccable workflow do not apply to it.

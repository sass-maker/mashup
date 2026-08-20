# Mashup helper agent instructions

When this repository is checked out inside the Fleet workspace, also follow
the shared instructions at `../AGENTS.md`.

## Runtime

- Python 3.11+ managed with uv.
- Astro + React editor under `web/`, managed with pnpm.
- FFmpeg and SQLite remain local runtime dependencies.

## Verify

```bash
uv sync
uv run python -m pytest -q
uv run ruff check .
uv run ruff format --check .
cd web && pnpm install && pnpm check && pnpm build
```

## Agent interface

- Discover capabilities with a `manifest` request to `uv run mashup agent`.
- Send one `fleet.video-agent-operation.v1` JSON object on stdin or with
  `--request`; stdout is one result envelope and progress remains structured.
- Use `validateOnly: true` before mutation or rendering. Render requires an
  approved `fleet.podcast-edit.v1`; finished artifacts use an operation-linked
  `fleet.mashup-media-receipt.v1`.
- The interface rejects unknown fields, commands, code, executables, and
  plugins. Mashup never publishes media.

## Boundaries

- This directory is the canonical home of the independent Mashup helper.
- Keep Reel Pipeline integration at the finished-media receipt boundary. Do
  not import Reel Pipeline modules, read its state, or depend on its paths.
- Only creator-owned, appropriately licensed, or public-domain filmed and
  photographic media may enter an edit. Preserve provenance.
- Procedural non-photoreal motion, typography, diagrams, shaders, and ASCII are
  allowed. Synthetic speech, voice cloning, and deceptive photoreal footage
  are not.
- Keep transcription, enrichment, embedding, boundary review, and render
  intermediates resumable.
- Keep all eight score terms separate and surfaced in every exported edit.
- Do not copy or commit `archive/`, `.mashup/`, `output/`, model payloads,
  credentials, or generated artifacts.
- Existing operator workdirs remain external data. Never move or delete them
  automatically when source ownership changes.

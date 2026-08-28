# Mashup — Project Status

Last updated: 2026-08-28

## Why / What

Mashup is an independent, local-first Fleet helper that turns creator-owned,
licensed, or public-domain podcast and video archives into coherent,
inspectable edits. It owns archive analysis, structure-aware planning,
approval, provenance, and multi-clip rendering.

## Dependencies

### External

- Python 3.11+, uv, SQLite, and FFmpeg.
- Optional local MLX, WhisperKit, Torch, and Transformers model runtimes.

### Fleet

- No runtime dependency on Reel Pipeline.
- Completed media may be handed to consumers through
  `fleet.mashup-media-receipt.v1`.

## Timeline

- **2026-08-28:** released the first public proof surface around the strongest
  Startups result: a source-faithful 47-second argument assembled from four
  beats across three Creative Commons podcast episodes, with a compact
  13-second comparison, browser captions, and inspectable media receipts.
- **2026-08-27:** added the bounded Startups clipping desk pilot: checked-in
  category angles, distinct 3–5 short batches, an explicit 1080×1920 render
  profile, static local review, and strict agent-side batch planning.
- **2026-08-20:** restored the standalone repository as Mashup's canonical
  source, preserving the complete local-first runtime and making the finished
  media receipt the only Fleet/Reel integration boundary.
- **2026-08-09:** added the strict non-interactive `mashup agent` contract for
  capability discovery, resumable stages, approved renders, and
  operation-linked finished-media receipts.
- **2026-08-09:** extracted Mashup from Reel Pipeline into an independently
  owned helper with a finished-media receipt boundary.

## Products

- Local Mashup CLI and loopback editorial interface.
- Static [public proof site](https://mashup.highsignal.app) for approved finished
  media; it does not host the archive, editor, rendering pipeline, accounts,
  uploads, or publishing.

## Features (shipped)

- Resumable archive ingestion, transcription, enrichment, embedding, boundary
  review, planning, approval, and multi-clip rendering.
- Strict `fleet.podcast-edit.v1` editorial contract.
- Source-rights, provenance, source-hash, and non-repetition validation.
- Versioned finished-media receipts for decoupled downstream consumption.
- Machine-readable agent manifest and operations with strict input decoding,
  stable errors, structured progress, approval gates, and no arbitrary code.
- Category-led Startups presets, non-overlapping short batches, vertical social
  rendering, and a standalone browser review manifest with local review state.
- Public proof showcase with responsive source screening, an argument map,
  independent score evidence, episode attribution, captions, and media receipts.

## Work queue

Open work is tracked in [GitHub Issues](https://github.com/sass-maker/mashup/issues).

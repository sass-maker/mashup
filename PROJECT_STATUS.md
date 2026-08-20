# Mashup — Project Status

Last updated: 2026-08-20

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

## Features (shipped)

- Resumable archive ingestion, transcription, enrichment, embedding, boundary
  review, planning, approval, and multi-clip rendering.
- Strict `fleet.podcast-edit.v1` editorial contract.
- Source-rights, provenance, source-hash, and non-repetition validation.
- Versioned finished-media receipts for decoupled downstream consumption.
- Machine-readable agent manifest and operations with strict input decoding,
  stable errors, structured progress, approval gates, and no arbitrary code.

## Work queue

Open work is tracked in [GitHub Issues](https://github.com/sarthakagrawal927/mashup/issues).

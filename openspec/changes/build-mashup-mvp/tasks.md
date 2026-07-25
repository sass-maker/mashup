# Tasks

## 1. Foundation
- [x] Scaffold repo, uv project, package layout, ruff + pytest config
- [x] Define the data contract (`models.py`): Cue, Source, SegmentMeta,
      Segment, ScoreTerms, Clip, EDL
- [x] Config via env, gateway-only credentials (`config.py`)
- [x] SQLite store with float32 vector blobs (`store.py`)

## 2. Ingestion
- [x] SRT + VTT parsers tolerant of markup, cue settings, missing hours,
      malformed blocks; speaker extraction
- [x] `ffprobe` media probe; sibling-subtitle discovery
- [x] Local whisper transcription fallback, resumable
- [x] Archive walker assigning stable ordinals
- [x] Public-domain archive fetcher with licence gate + provenance

## 3. Segment understanding
- [x] Pause/speaker atom builder
- [x] Atom grouping toward target segment length
- [x] Gateway client: chat, defensive JSON, batched embeddings, disk cache,
      retry policy
- [x] LLM enrichment with neighbouring context and per-item fallback

## 4. Planning
- [x] Embedding retrieval with MMR diversification
- [x] Eight scoring terms, each 0..1 and independently tested
- [x] Weight profiles per strategy
- [x] Shared beam search; chronological ordering constraint
- [x] Semantic and random baselines in the same machinery
- [x] Brief parsing into query + ordered beats, with regex fallback

## 5. Editing
- [x] EDL save/load/transcript-preview
- [x] Local server: EDL read/write, candidates, segment detail, ranged media
- [x] Astro + React timeline: remove, reorder, replace, extend, preview,
      undo, export
- [x] `mashup serve` command

## 6. Rendering
- [x] Silence detection with per-file cache
- [x] Outward-snapping boundary selection
- [x] Per-clip extract, loudness normalisation, concat, crossfade option
- [x] Rebased subtitles: sidecar or burned in
- [x] Audio-only sources composited over a card

## 7. Validation
- [x] Five-condition blind generation with a withheld key
- [x] Rating sheet + criteria analysis
- [x] Mechanical timeline-churn metric against the kill criterion
- [x] `mashup experiment` / `evaluate` / `churn` CLI commands
- [ ] Run against the Groucho archive end to end
- [ ] Recruit five viewers, run the blind comparison, record the result

## 8. Verification
- [x] Unit tests across subtitles, gateway, enrichment, splitter, scoring,
      planning, boundaries, EDL I/O, fetcher
- [x] ffmpeg-gated render smoke test
- [x] Offline end-to-end integration test with a stubbed gateway
- [x] CI workflow on the Python toolchain plus a `web` build job

## Open questions
- `Source.recorded_at` is unset; ordinals proxy chronology. Does a
      filename date convention need parsing for real creator archives?
- `ingest_archive` raises on the first unreadable file. Should a real
      archive tolerate one bad file and report it instead?
- The EDL stores `weights` and `terms` but not the query vector or parsed
      beats, so the editor can only fully rescore after re-deriving them from
      the gateway. Persist the query embedding in the EDL?
- `Clip.transition` is per-clip in the model but `render()` takes one
      global crossfade. Either honour it per-clip or mark it advisory.
- Sidecar SRT timings are apportioned by character count because `Clip`
      carries text without internal cue timings. Carry cue timings into the
      clip for frame-accurate subtitles.
- `Config.media_dir` is created but never written to — dead, remove.
- `subtitles="burn"` needs an ffmpeg built with libass; the local
      Homebrew build has none, so it fails fast. Document or vendor.

# archive-ingestion Specification

## Purpose
Turn a directory of a creator's own recordings into `Source` records and a
normalised, plain-text cue timeline, generating subtitles locally when the
archive ships without them, and refusing material whose licence bars
derivatives.

## ADDED Requirements

### Requirement: Deterministic archive walk with stable ordinals
The system SHALL ingest every `.mp4`, `.mkv`, `.mov`, `.mp3`, `.m4a` and `.wav`
file found recursively under the archive directory, ordered by case-folded
relative path, and SHALL assign each source a consecutive ordinal in that
order. Source ids SHALL be slugified from the filename stem so that
re-ingesting the same archive yields the same references.

#### Scenario: Same archive ingested twice
- **WHEN** the same archive directory is ingested on two machines
- **THEN** every source receives the same id and the same ordinal

#### Scenario: Directory with no media
- **WHEN** the archive directory contains no file with a supported suffix
- **THEN** ingestion fails with an error naming the supported suffixes

### Requirement: Media probing distinguishes real video from cover art
The system SHALL probe each media file with `ffprobe` for duration and stream
layout, SHALL NOT count an `attached_pic` stream as a video track, and SHALL
fall back to the longest stream duration when the container reports none.

#### Scenario: MP3 with embedded cover art
- **WHEN** an audio file carries an attached picture stream
- **THEN** the source is recorded with `has_video` false

#### Scenario: No duration anywhere
- **WHEN** neither the container nor any stream reports a usable duration
- **THEN** probing fails rather than recording a zero-length source

### Requirement: Subtitle resolution with a local transcription fallback
The system SHALL use a sibling `.srt` in preference to a sibling `.vtt`, and
when neither exists SHALL reuse a previously generated transcript from the
workdir before generating a new one. Transcription SHALL be resumable: an
existing output is trusted, and new output is written to a `.partial` file and
renamed only once complete.

#### Scenario: Transcription disabled but a cached transcript exists
- **WHEN** ingestion runs with transcription disabled and the workdir already
  holds a transcript for that source
- **THEN** the cached transcript is used instead of failing

#### Scenario: Transcription disabled and nothing cached
- **WHEN** a media file has no sibling subtitle and no cached transcript
- **THEN** ingestion fails with an error naming both remedies

### Requirement: Forgiving subtitle normalisation
The system SHALL parse SRT and WebVTT into cues carrying plain text on a
seconds timeline, stripping ASS overrides, inline karaoke timestamps and
markup, unescaping entities, and lifting the speaker out of `<v Name>` or a
short `NAME:` prefix. A malformed block SHALL be skipped; only a file that
yields no usable cue at all SHALL be an error.

#### Scenario: One broken block in a long episode
- **WHEN** a subtitle file contains one block with an unparseable timing line
- **THEN** that block is dropped and every other cue is still parsed

#### Scenario: Colon inside a sentence
- **WHEN** a cue reads `and then he said: what a night`
- **THEN** no speaker is extracted and the text is left intact

### Requirement: Licence gate and provenance on fetched corpora
The archive fetcher SHALL refuse any archive.org item whose licence contains an
`-nd` term, whose licence is absent, or whose licence it cannot recognise as a
public-domain mark, CC0 or a Creative Commons licence, and SHALL write a
`PROVENANCE.json` recording the item, title, licence URL, source URL, fetch
time and every file's size and md5.

#### Scenario: NoDerivatives item
- **WHEN** the item's `licenseurl` contains `-nd`
- **THEN** the fetcher exits with the licence-refused code and downloads nothing

#### Scenario: Checksum mismatch
- **WHEN** a downloaded file's md5 does not match the published md5
- **THEN** the partial file is deleted and the fetcher exits with the checksum code

### Requirement: Every stage persists to a resumable store
The system SHALL persist sources, cues, segments, segment metadata and
embeddings in SQLite, and SHALL make each stage re-runnable without repeating
work that has already been paid for.

#### Scenario: Re-running ingest after a partial run
- **WHEN** `ingest` is run again over the same archive
- **THEN** existing sources are updated in place and their segments replaced,
  and already-transcribed audio is not transcribed again

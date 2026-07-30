# archival-visuals Specification

## Purpose
TBD - created by archiving change short-form-archival-visuals. Update Purpose after archive.
## Requirements
### Requirement: Archival stills are explicit EDL decisions
The EDL SHALL support clip-relative visual inserts that record local source
path, source frame time, visible source title, provenance URL, output interval,
and `still` or `motion` playback mode. Legacy entries without a mode MUST
remain stills.

#### Scenario: A visual manifest is attached
- **WHEN** the operator supplies valid visual entries for a short
- **THEN** each entry is persisted on its target EDL clip

#### Scenario: A visual entry is invalid
- **WHEN** its path is missing, its clip index is unknown, or its interval falls outside the clip
- **THEN** the command fails before rendering

#### Scenario: A legacy visual has no playback mode
- **WHEN** an existing EDL is loaded without a visual mode
- **THEN** the visual is interpreted as a still

### Requirement: Visual inserts preserve spoken-source branding
The renderer SHALL display archival stills or moving archival video beneath the
persistent podcast source heading and watermark. It SHALL show the archival
visual's own credit only while that insert is visible.

#### Scenario: A still is active
- **WHEN** playback enters a still visual insert interval
- **THEN** the held source frame appears while the podcast source heading, watermark, and image-source credit remain visible

#### Scenario: A still ends
- **WHEN** playback exits a visual insert interval
- **THEN** the audio-led base or next visual returns and the previous image-source credit disappears

#### Scenario: A motion insert is active
- **WHEN** playback enters a motion visual sourced from video
- **THEN** consecutive existing source frames play while spoken-source branding and visual credit remain visible

### Requirement: Visual changes invalidate rendered intermediates
The intermediate cache SHALL include every visual field, including playback
mode, and the identity of each visual source file that affects pixels.

#### Scenario: A visual decision changes
- **WHEN** the asset, source frame time, interval, source title, provenance URL, playback mode, file size, or file modification time changes
- **THEN** the affected clip receives a different intermediate cache key

#### Scenario: Visual decisions are unchanged
- **WHEN** an identical visualized clip is rendered again
- **THEN** the renderer reuses its existing intermediate


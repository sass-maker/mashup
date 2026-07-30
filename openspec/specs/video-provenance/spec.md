# video-provenance Specification

## Purpose
TBD - created by archiving change burn-source-provenance. Update Purpose after archive.
## Requirements
### Requirement: Rendered clips show their source
The renderer SHALL overlay each clip's human-readable source title and original source start/end timecode as a visually hierarchical, semi-transparent source heading. It MUST fall back to `source_id` when the title is absent.

#### Scenario: Clip has a source title
- **WHEN** a labeled render processes a clip with `source_title`
- **THEN** the complete clip shows an archive kicker, the complete title, and original source time range with distinct visual hierarchy

#### Scenario: Legacy clip has no source title
- **WHEN** a labeled render processes a clip without `source_title`
- **THEN** the complete clip shows `source_id` and the original source time range

#### Scenario: Source clip changes
- **WHEN** playback crosses from one EDL clip into another
- **THEN** the persistent source heading changes to the new clip's title and source interval at that boundary

### Requirement: Provenance follows edits
The rendered label SHALL derive from the current EDL clip fields rather than from stale archive or cache metadata.

#### Scenario: Clip was replaced
- **WHEN** an edited EDL changes a clip's source and source interval
- **THEN** the next render shows the replacement source and interval

#### Scenario: Clip was extended
- **WHEN** an edited EDL changes a clip's original start or end
- **THEN** the next render shows the extended source interval

### Requirement: Provenance rendering is portable and optional
The renderer SHALL create source headings and watermarks without requiring FFmpeg text or subtitle filters or a new runtime package. Source headings and watermarks SHALL be enabled by default and SHALL each support an explicit CLI opt-out.

#### Scenario: FFmpeg lacks text filters
- **WHEN** the supported FFmpeg can decode transparent PNG images and overlay video but has no `drawtext` or `subtitles` filter
- **THEN** source-heading and watermark rendering still succeeds

#### Scenario: Operator requests a clean master
- **WHEN** the operator passes `--no-source-label --no-watermark`
- **THEN** the renderer emits video without provenance graphics

### Requirement: Render caching includes provenance
The intermediate-render cache SHALL include every source-heading and watermark input that affects pixels.

#### Scenario: Provenance changes
- **WHEN** source title, source ID, source interval, source-label setting, watermark setting, watermark text, or graphic style changes
- **THEN** the affected clip receives a different intermediate cache key

#### Scenario: Provenance is unchanged
- **WHEN** an identical branded clip is rendered again
- **THEN** the renderer reuses its existing intermediate

### Requirement: Rendered clips carry a configurable watermark
The renderer SHALL show a subtle persistent watermark on every clip when watermarking is enabled. The operator MUST be able to change its text without editing source provenance.

#### Scenario: Default branded render
- **WHEN** rendering runs with watermarking enabled and no custom text
- **THEN** the video shows the default watermark for the duration of each clip

#### Scenario: Custom watermark
- **WHEN** the operator supplies custom watermark text
- **THEN** every rendered clip shows that text

#### Scenario: Watermark disabled
- **WHEN** the operator passes `--no-watermark`
- **THEN** no watermark is composited


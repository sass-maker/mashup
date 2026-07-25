# mashup-rendering Specification

## Purpose
Turn an EDL into one playable MP4: move each cut to a natural edge, extract
every clip at identical codec parameters with per-clip loudness normalisation,
concatenate, and emit subtitles rebased onto the output timeline.

## ADDED Requirements

### Requirement: Cuts snap outward, never inward
The system SHALL move a planned cut to the most natural edge within a bounded
window, preferring the midpoint of a nearby silence over the midpoint of a gap
between subtitle cues, and SHALL always prefer a candidate on the outward side —
starts move earlier, ends move later — over any inward candidate, so speech is
never truncated. A snap that would collapse the clip SHALL fall back to a span
at least as wide as the original.

#### Scenario: Silence just inside and just outside the requested start
- **WHEN** both an earlier and a later candidate lie within the window
- **THEN** the earlier one is chosen, even if the later one is nearer

#### Scenario: No candidate in the window
- **WHEN** neither a silence nor a cue gap falls within the window
- **THEN** the requested boundary is left unchanged

#### Scenario: Snap collapses the clip
- **WHEN** snapping would produce a clip shorter than the minimum clip duration
- **THEN** the union of the snapped and original spans is used, and the result
  is never shorter than the minimum

### Requirement: Silence detection is cached per file and per parameter set
The system SHALL detect silences by decoding the file once and SHALL cache the
result in a sidecar keyed on the file's identity and the detection parameters,
re-scanning when the media changes, the threshold changes, or the sidecar is
unreadable.

#### Scenario: Second render of the same archive
- **WHEN** a source is rendered again with unchanged detection parameters
- **THEN** the cached silence spans are reused and the file is not decoded again

### Requirement: Uniform intermediates, per-clip loudness normalisation
The system SHALL extract each clip to its own intermediate at identical codecs,
resolution, frame rate, sample rate and timebase, re-encoding rather than
stream-copying so cuts land at conversational boundaries rather than keyframes,
and SHALL apply EBU R128 loudness normalisation per clip rather than once over
the finished timeline. Intermediates SHALL be cached on the fields that affect
pixels, so changing the transition style reuses them.

#### Scenario: Clips from episodes recorded years apart
- **WHEN** two clips have very different recorded levels
- **THEN** each is normalised during extraction, so the join has no level jump

#### Scenario: Crossfade length changed and re-rendered
- **WHEN** only the crossfade duration changes
- **THEN** every clip intermediate is reused from cache

### Requirement: Audio-only sources render as video
The system SHALL composite an audio-only clip over a neutral card at the target
resolution and frame rate, and SHALL supply silent audio for a clip with no
audio track, so a mixed archive concatenates uniformly and the output is always
a playable MP4. The target format SHALL be taken from the first clip with a
real video track, defaulting to 720p30 for a wholly audio-only archive.

#### Scenario: Podcast archive
- **WHEN** every source is audio-only
- **THEN** the output is a 720p30 MP4 of the audio over the card

### Requirement: Subtitles rebased onto the output timeline
The system SHALL emit subtitles as a sidecar `.srt` by default, may burn them
in on request, and SHALL derive their timings from each clip's actual position
and duration in the output rather than from source cue times. Burning SHALL
fail with an explanation when the local ffmpeg build has no `subtitles` filter.

#### Scenario: Crossfade shortens a clip
- **WHEN** clips overlap through a crossfade
- **THEN** subtitle timings follow the shortened output positions, not the
  source cue times

#### Scenario: ffmpeg without libass
- **WHEN** burn-in is requested on a build with no `subtitles` filter
- **THEN** rendering fails with a message naming the cause and the remedy

### Requirement: Refuse to render what cannot be rendered
The system SHALL reject an EDL with no clips, and SHALL report every missing
source file before starting work rather than failing partway through.

#### Scenario: Archive moved after planning
- **WHEN** one or more clip source paths no longer exist
- **THEN** rendering fails listing all of them, having encoded nothing

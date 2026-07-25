# timeline-editing Specification

## Purpose
Let a human review and repair a generated timeline as transcript rather than as
a video scrub. The EDL is the document; a loopback-only local server hands the
browser everything needed to judge a cut and takes the corrected EDL back.

## ADDED Requirements

### Requirement: The EDL is a readable, reviewable document
The system SHALL persist an EDL as pretty-printed, key-sorted JSON carrying the
strategy, prompt, target duration, score, term breakdown, weight profile,
rationale and, per clip, the segment id, source id, source path, planner
boundaries, render boundaries, text, summary, role, energy and topics. The
system SHALL also render the EDL as a plain-text transcript with per-clip
source locators.

#### Scenario: Reviewing without a video player
- **WHEN** the operator runs `mashup preview` on an EDL
- **THEN** each clip is printed with its source, timecode range, duration, role
  and energy, followed by its wrapped transcript

#### Scenario: EDL in a diff
- **WHEN** two EDLs for the same archive are compared
- **THEN** the stable key ordering keeps the diff readable

### Requirement: Loopback-only editor server
The system SHALL bind the editor server to loopback addresses only and SHALL
refuse to start on any other host.

#### Scenario: Non-loopback host requested
- **WHEN** the server is constructed with a host that is not localhost
- **THEN** construction fails rather than exposing the archive on the network

### Requirement: Provenance and candidates for every clip
The system SHALL expose the current EDL, a ranked candidate list for a
free-text query, and full detail for any segment — its text, cue range,
entities, prerequisites, opener/closer flags, source, and its neighbouring
segments in the same recording. Candidate ranking SHALL use embeddings when the
archive is embedded and a query vector is available, and SHALL fall back to
token-overlap ranking otherwise, reporting which mode it used.

#### Scenario: Replacing a clip
- **WHEN** the operator searches for a replacement
- **THEN** each result carries its source title, timecode, duration, summary,
  excerpt, role, energy, topics and source path

#### Scenario: Archive never embedded
- **WHEN** a query is issued against an archive with no embeddings
- **THEN** results are ranked by token overlap and the response reports mode
  `substring` rather than failing

### Requirement: Media preview by source id with range requests
The system SHALL serve source media only by `source_id` resolved against an
allow-list built from the store and the open EDL, SHALL never join a
user-supplied string onto a filesystem path, and SHALL answer HTTP `Range`
requests with `206` responses so the browser can seek to a clip's start.

#### Scenario: Browser seeks into an episode
- **WHEN** the player requests a byte range
- **THEN** the server responds `206` with a `Content-Range` header and streams
  only that span

#### Scenario: Path traversal attempted
- **WHEN** the media route is called with a token containing a path separator
  or `..`
- **THEN** the request is refused

### Requirement: Saving an edit renumbers, rescores and writes atomically
The system SHALL validate a submitted EDL, renumber clip indices, rescore the
sequence, and write the file by rename so a crash cannot leave a truncated
document. When the planner's query context can be rebuilt, every term SHALL be
recomputed; when it cannot, only the terms computable from the sequence alone —
escalation, callback, duration fit and source diversity — SHALL be recomputed
and the rest carried forward, with the response stating which mode was used.

#### Scenario: Offline edit
- **WHEN** the editor has no gateway access
- **THEN** the four structural terms are recomputed, relevance and context
  completeness are carried over unchanged, and the response reports `partial`

#### Scenario: Invalid document submitted
- **WHEN** the submitted body fails EDL validation
- **THEN** the server responds with a validation error and does not overwrite
  the file on disk

### Requirement: Transcript-first timeline operations
The editor SHALL present the mashup as a transcript and SHALL support removing
a clip, reordering clips, replacing a clip from ranked candidates, extending a
clip into its neighbouring segment, previewing a clip in place, undoing recent
changes, and exporting the EDL. Every change SHALL be saved through the server
so the displayed score is the server's recomputed score, and the interface
SHALL state whether that rescore was full or partial.

#### Scenario: Clip reordered
- **WHEN** the operator moves a clip up or down the timeline
- **THEN** the EDL is saved, clip indices are renumbered, and the score header
  updates with the recomputed terms

#### Scenario: Undo after an accidental removal
- **WHEN** the operator removes a clip and then undoes
- **THEN** the prior document is restored and saved, and the undo itself does
  not become a new undo step

### Requirement: Honest reporting when the editor UI is not built
The system SHALL respond to a non-API request with actionable build
instructions when the editor's static bundle is absent, and SHALL still return
a not-found error for a missing named asset so build breakage stays visible.

#### Scenario: Server started before the UI is built
- **WHEN** the operator opens the editor root and no built bundle exists
- **THEN** the response explains where the bundle was expected and how to build it

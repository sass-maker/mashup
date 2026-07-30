# short-form-editorial Specification

## Purpose
TBD - created by archiving change short-form-archival-visuals. Update Purpose after archive.
## Requirements
### Requirement: Short-form output obeys a strict duration contract
The system SHALL provide a short-form planning command whose requested duration
is between 30 and 60 seconds inclusive. The resulting unsnapped EDL SHALL also
remain within that range.

#### Scenario: Operator requests a 45-second short
- **WHEN** the operator runs short-form planning with a 45-second target
- **THEN** the emitted EDL contains between 30 and 60 seconds of source material

#### Scenario: Operator requests an invalid short duration
- **WHEN** the requested target is below 30 seconds or above 60 seconds
- **THEN** the command fails before planning with a clear duration error

### Requirement: Short-form cuts use existing speech at cue boundaries
The short-form planner SHALL construct candidates from contiguous stored
transcript cues around retrieved segment anchors. It MUST NOT synthesize,
rewrite, or reorder words within a candidate.

#### Scenario: A candidate is constructed
- **WHEN** a retrieved anchor has a qualifying cue window
- **THEN** candidate start, end, and text exactly match contiguous stored cues

#### Scenario: No qualifying cue window exists
- **WHEN** no retrieved anchor can form a clean 30–60 second cue window
- **THEN** planning fails rather than padding, truncating mid-thought, or generating material

### Requirement: Short-form scoring remains inspectable
Short-form selection SHALL use the existing independent score terms and record
their values and weights in the EDL.

#### Scenario: A short is selected
- **WHEN** planning succeeds
- **THEN** the EDL surfaces relevance, context, repetition, progression, escalation, callback, duration, and source-diversity terms


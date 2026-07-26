# segment-understanding Specification

## Purpose
Divide a cue timeline into segments that hold a whole setup-and-payoff
together, then attach the structured metadata the planner sequences on: topic,
role, summary, prerequisites, energy, opener/closer suitability and recurring
entities.

## ADDED Requirements

### Requirement: Deterministic atom construction
The system SHALL group cues into pause-delimited atoms, closing an atom when
the gap to the next cue reaches the pause threshold, when the run would exceed
the maximum atom length, or when the speaker changes. An atom SHALL never span
a long silence, so a cut between atoms is always a cut between utterances.

#### Scenario: Long pause mid-episode
- **WHEN** two consecutive cues are separated by more than the pause threshold
- **THEN** they land in different atoms

#### Scenario: Speaker change with no pause
- **WHEN** the next cue carries a different speaker label
- **THEN** a new atom starts even though the cues are contiguous

### Requirement: Segment grouping toward a target length
The system SHALL accumulate atoms until the run reaches the target segment
length and SHALL then close the segment at the most natural nearby edge — the
longest inter-atom pause, favouring an atom that opens a new thought and, less
strongly, one that changes speaker — never closing before the minimum length
and always closing at the maximum. A trailing run shorter than the minimum
SHALL be folded into the previous segment rather than emitted as a fragment.

#### Scenario: Over-long run of atoms
- **WHEN** a run reaches the target length and one of the candidate cut points
  opens a new thought
- **THEN** the segment closes at that point in preference to a marginally
  longer pause elsewhere

#### Scenario: Short tail
- **WHEN** the final run of atoms is shorter than the minimum segment length
- **THEN** it is appended to the preceding segment

#### Scenario: One atom longer than the maximum
- **WHEN** a single atom already exceeds the maximum segment length
- **THEN** it becomes a segment on its own rather than being split mid-speech

### Requirement: LLM enrichment with neighbouring context
The system SHALL send segments to a chat model in small batches, each item
accompanied by a bounded excerpt of the preceding and following transcript from
the same recording, and SHALL instruct the model to use that context only to
decide what the segment silently assumes. Each item SHALL be returned with
`topic`, `role`, `summary`, `required_context`, `energy`, `can_open`, `can_end`
and `entities`.

#### Scenario: Clip that references an earlier premise
- **WHEN** the segment relies on a name or bit established in the context before it
- **THEN** the prerequisite is recorded in `required_context` and `can_open` is false

### Requirement: Interchangeable chat backends
The system SHALL support enrichment against either a local in-process model or
the remote gateway, selected by configuration, behind one interface. It SHALL
hand the backend a window of prompts at a time rather than one at a time, so
each can parallelise in its own way, and SHALL report progress per window.

#### Scenario: No credentials available
- **WHEN** every model stage is configured to run locally
- **THEN** enrichment completes without a gateway key and without network access

#### Scenario: A backend cannot answer one window
- **WHEN** one batch's reply is missing or does not parse
- **THEN** only that batch's segments keep default metadata and the run continues

### Requirement: Per-item fallback, never per-batch loss
The system SHALL match a returned item to its segment by the echoed id and
SHALL fall back to positional alignment when the id is missing or mangled. A
single item that fails validation SHALL yield neutral default metadata for that
segment only; an unrecognised `role` SHALL degrade to `development` rather than
discarding the item.

#### Scenario: Model drops one id
- **WHEN** one item in a batch of five omits its id
- **THEN** the other four are matched by id and the fifth is matched by position

#### Scenario: One malformed item
- **WHEN** one item fails schema validation
- **THEN** that segment receives neutral metadata and the rest of the batch is kept

#### Scenario: Reply wrapped in prose or an object
- **WHEN** the model returns a fenced block, or an object wrapping the array
- **THEN** the array is still extracted and the batch succeeds

### Requirement: Enrichment is resumable
The system SHALL enrich only segments that have no summary yet, so an
interrupted or repeated run does not pay for work already done.

#### Scenario: Re-running enrich after a crash
- **WHEN** `enrich` is run again after half the archive has been enriched
- **THEN** only the unenriched segments are sent to the model

# mashup-planning Specification

## Purpose
Turn a natural-language brief into an ordered sequence of clips: parse the
brief into a retrieval query plus ordered beats, retrieve a diverse candidate
pool, and order it under an explicit eight-term objective shared by three
strategies and two baselines.

## ADDED Requirements

### Requirement: Brief parsing with a regex fallback
The system SHALL parse the brief into a dense retrieval query, an ordered list
of structural beats and an optional tone, and SHALL fall back to a regex parse
— splitting on ordering markers and stripping meta words — whenever the gateway
call fails or returns no usable query. An explicit duration in the brief SHALL
override the `--duration` default.

#### Scenario: Gateway unavailable
- **WHEN** brief parsing raises a gateway error
- **THEN** the regex parse is used and planning continues

#### Scenario: Brief with no stated structure
- **WHEN** the brief names no ordering
- **THEN** the beats list is empty and no structure is invented

#### Scenario: Duration in the brief
- **WHEN** the brief says "a seven minute set" and `--duration 420` is not given
- **THEN** the target duration is taken from the brief

### Requirement: Diversified retrieval over an embedded archive
The system SHALL rank segments by cosine similarity to the query vector and
SHALL select the candidate pool by maximal marginal relevance, trading a little
relevance for material the planner can build variety from. Planning SHALL
refuse to run against an archive with no embeddings.

#### Scenario: Archive contains the same bit told three times
- **WHEN** the three near-identical tellings all rank near the top
- **THEN** the pool contains fewer of them than a pure top-k would return

#### Scenario: Archive never embedded
- **WHEN** planning is attempted before `embed` has run
- **THEN** it fails with an error pointing at `mashup embed`

### Requirement: Eight surfaced scoring terms
The system SHALL score a sequence on eight independent terms — relevance,
context completeness, non-repetition, progression, escalation, callback,
duration fit and source diversity — each normalised to 0..1, and SHALL write
both the term values and the weight profile that combined them into the EDL.

#### Scenario: Diagnosing a bad mashup
- **WHEN** a creator inspects a generated EDL
- **THEN** every term value and its weight are present, so a low score can be
  attributed to a named term

#### Scenario: Context prerequisite satisfied earlier in the sequence
- **WHEN** a clip's `required_context` is covered, above a deliberately lenient
  cosine threshold, by any earlier clip in the sequence
- **THEN** that prerequisite counts as satisfied

#### Scenario: Callback requires a gap
- **WHEN** two adjacent clips share an entity
- **THEN** it does not count as a callback; only a shared entity across a gap of
  two or more clips does

### Requirement: One shared beam search, weights and constraints as the only difference
The system SHALL plan all strategies with the same beam search over the same
scoring code, differing only in the weight profile and in whether the
chronological ordering constraint is imposed, so that a win in the blind test
is attributable to the objective rather than to uneven tuning. `duration_fit`
SHALL be excluded during search and restored for final scoring, so a short
prefix of a long set is not pruned as a duration failure.

#### Scenario: Two-clip prefix of a seven-minute target
- **WHEN** the beam holds a partial sequence far short of the target
- **THEN** it is not penalised on duration and can continue to grow

#### Scenario: Chronological strategy
- **WHEN** the chronological strategy extends a beam
- **THEN** only segments strictly later than the last clip, by source ordinal
  then in-source start time, are considered, so the archive is never reordered

#### Scenario: Sequence ending on a clip that cannot end
- **WHEN** the final clip's metadata says it does not land as a final beat
- **THEN** the sequence's final score is discounted

### Requirement: Baselines built from the same machinery
The system SHALL provide a semantic baseline that takes the most relevant clips
in relevance order with no sequencing, and a random control that shuffles
topic-matched clips above a relevance floor under a fixed seed. Both SHALL be
scored by the same scoring code as the AI strategies.

#### Scenario: Reproducing the control
- **WHEN** the random baseline is generated twice with the same seed
- **THEN** it produces the same sequence

### Requirement: Rescoring an edited sequence
The system SHALL recompute the term breakdown and total score for a sequence
that a human has changed, using the strategy's own weights.

#### Scenario: Clip removed by hand
- **WHEN** a clip is deleted from a planned sequence
- **THEN** the terms and total score are recomputed for the shortened sequence

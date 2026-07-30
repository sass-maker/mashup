# editorial-integrity Specification

## Purpose
TBD - created by archiving change improve-editorial-integrity. Update Purpose after archive.
## Requirements
### Requirement: Retrieved anchors become bounded editorial bits
The system SHALL turn each retrieved anchor into a contiguous span of one or more stored segments from the same source. The span MUST contain the anchor, MUST NOT exceed the configured member-count or duration limits, and MUST have a clean opening and ending according to existing enrichment metadata.

#### Scenario: Adjacent context repairs an anchor
- **WHEN** a retrieved anchor cannot open cleanly or cannot end cleanly and qualifying adjacent segments exist within the repair limits
- **THEN** the system produces a bit containing the smallest qualifying contiguous span around that anchor

#### Scenario: An anchor cannot be repaired
- **WHEN** no qualifying contiguous span exists within the repair limits
- **THEN** the system excludes that anchor from the editorial candidate pool

### Requirement: Editorial integrity is a hard planning gate
The system SHALL re-review candidate-adjacent boundaries with the configured chat backend and SHALL pass only editorial bits with a reviewed clean opening, no unresolved opening prerequisite, and a reviewed clean ending to sequencing. It MUST fail with an actionable quality-gate error when no eligible bit remains.

#### Scenario: Candidate boundary was permissively enriched
- **WHEN** the candidate-only review finds that an enriched opener or ending is actually a conversational continuation
- **THEN** the system does not use that boundary to construct an eligible bit

#### Scenario: All candidates fail integrity review
- **WHEN** candidate preparation finds zero eligible editorial bits
- **THEN** planning stops before beam search and reports how many anchors were rejected

### Requirement: Candidate boundary review is resumable
The system SHALL content-cache each valid candidate boundary review using the reviewer model, prompt version, segment text, and neighbouring context. A repeated build MUST reuse an unchanged review without another model call.

#### Scenario: Planning is repeated without boundary changes
- **WHEN** the same model and prompt review a segment with unchanged transcript and neighbouring context
- **THEN** the system loads the cached boundary judgment

#### Scenario: Review inputs change
- **WHEN** the model, prompt version, segment text, or neighbouring context changes
- **THEN** the system treats the previous cache entry as stale and requests a new review

### Requirement: Planning conditions receive equivalent boundary repair
The system SHALL apply the same editorial-bit construction and integrity rules to AI, semantic, random, and callback-expanded candidate pools without changing their retrieval or sequencing semantics.

#### Scenario: Baselines are requested
- **WHEN** a run includes semantic and random baselines
- **THEN** their retrieved anchors are repaired with the same limits and boundary gate used by the AI strategies

### Requirement: Overlapping source material cannot repeat
The system SHALL treat the stored segment IDs inside a bit as its source-material identity. A sequence MUST NOT contain two bits that share any stored segment ID.

#### Scenario: Distinct bits overlap
- **WHEN** two candidate bits have different synthetic IDs but share a stored member segment
- **THEN** a planner or baseline can select at most one of them for the output sequence

### Requirement: Editorial bits retain source provenance
Each planned clip SHALL retain its primary stored `segment_id`, SHALL expose the ordered IDs of every stored segment included in its editorial bit, and SHALL carry the human-readable source title. Existing EDL documents without the new provenance fields MUST remain readable.

#### Scenario: Multi-segment bit is written to an EDL
- **WHEN** a planned bit contains multiple stored segments
- **THEN** its clip interval and transcript cover the full bit while `segment_ids` lists every member in source order

#### Scenario: Legacy EDL is read
- **WHEN** a clip document has `segment_id` but no `segment_ids`
- **THEN** the system loads it as a one-member clip without migration

### Requirement: Timeline shows changeable source provenance
The editor SHALL show each clip's human-readable source title and original source start/end timecode in the compact clip header. Replacing the clip SHALL update the displayed source, timecode, primary segment, and ordered member provenance.

#### Scenario: Operator inspects a planned clip
- **WHEN** the timeline renders a clip with a source title
- **THEN** the clip header shows that title and its original source time range

#### Scenario: Operator replaces a clip
- **WHEN** the operator chooses a candidate from another source
- **THEN** the timeline and saved EDL use the replacement's source title, source ID, source time range, and segment ID

#### Scenario: Legacy clip has no source title
- **WHEN** the timeline renders an older EDL without `source_title`
- **THEN** it shows the stable `source_id` as the source label

### Requirement: Scoring remains inspectable
The system SHALL preserve all eight existing scoring terms and their individual EDL weights. Editorial eligibility MUST remain a separate pre-planning decision rather than being collapsed into an opaque replacement score.

#### Scenario: Repaired mashup is emitted
- **WHEN** planning succeeds over editorial bits
- **THEN** the EDL contains the existing relevance, context completeness, non-repetition, progression, escalation, callback, duration fit, and source diversity terms


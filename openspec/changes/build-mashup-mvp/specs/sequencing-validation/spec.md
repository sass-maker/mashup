# sequencing-validation Specification

## Purpose
Answer the one question the project exists for — does structure-aware
sequencing beat retrieve-and-join? — with a blind five-condition comparison and
a mechanical churn metric measured against a stated kill criterion.

## ADDED Requirements

### Requirement: Five conditions from one brief
The system SHALL generate all five conditions — the random control, the
semantic baseline, and the chronological, escalation and callback AI cuts —
from a single brief and target duration in one run, and SHALL fail loudly if
any condition produced no output.

#### Scenario: A strategy produces nothing
- **WHEN** the planner returns no sequence for one of the five conditions
- **THEN** the experiment run fails naming the missing condition rather than
  quietly comparing four

### Requirement: Blind labelling with a separately withheld key
The system SHALL write each condition to a letter-labelled EDL under a
seed-shuffled assignment, and SHALL record the label-to-condition mapping, the
prompt, the target duration, the seed and the planner scores in a separate key
file that can be withheld from raters.

#### Scenario: Preparing a rating session
- **WHEN** the experiment is generated
- **THEN** the rater can be given the labelled variants and the rating sheet
  without ever seeing which letter is which strategy

#### Scenario: Reproducing an assignment
- **WHEN** the experiment is regenerated with the same seed
- **THEN** the same labels map to the same conditions

### Requirement: A rating sheet that records what the criteria need
The system SHALL emit a rating sheet with one row per viewer per variant and
columns for the viewer, the variant label, the overall rank across the five,
the total clip count, the count of clips that felt like they needed setup, the
count of obvious defects, a would-publish answer and free-text notes.

#### Scenario: Partially completed sheet
- **WHEN** only some rows carry an overall rank
- **THEN** analysis uses the completed rows and fails only if none are complete

### Requirement: Unblinded analysis against the stated success criteria
The system SHALL unblind the ratings using the key and SHALL report, for the
best-performing AI condition, whether it was preferred over the semantic
baseline by enough viewers, whether its mean context completeness met the
target, and whether its mean defect count stayed under the limit.

#### Scenario: AI cut preferred by four of five viewers
- **WHEN** four viewers rank an AI condition above the semantic baseline
- **THEN** the preference criterion is reported as met

#### Scenario: Ranked but not counted
- **WHEN** a viewer ranks the AI cuts but not the semantic baseline
- **THEN** that viewer contributes no preference count

### Requirement: Mechanical churn against the kill criterion
The system SHALL compute timeline churn between a generated EDL and its edited
form as the fraction of clips replaced, counting removals and additions, and
SHALL count reordering only among the clips that survived the edit so a removal
is not charged twice. The result SHALL state whether it passes the kill
criterion.

#### Scenario: Creator replaces most of the timeline
- **WHEN** churn exceeds the kill threshold
- **THEN** the report marks the kill criterion as not passed

#### Scenario: Creator only reorders
- **WHEN** no clips are removed or added and the order changes
- **THEN** churn is zero and the reorder count records the change

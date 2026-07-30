## ADDED Requirements

### Requirement: The visual lab presents materially different animated directions
The local editor SHALL expose Cel Orbit, ASCII Signal, and Kinetic Type probes
that express the same source idea with distinct rendering systems.

#### Scenario: Operator opens the visual lab
- **WHEN** the local visual-lab route loads
- **THEN** one animated probe fills the stage and controls expose all three named directions

#### Scenario: Operator changes direction
- **WHEN** the operator selects another named probe
- **THEN** the stage switches rendering systems without changing the source idea or provenance context

### Requirement: Cel Orbit uses a real WebGL scene
Cel Orbit SHALL use Three.js geometry, orthographic camera, cel-shaded
materials, ink outlines, directional light, and authored rolling motion. It
MUST NOT copy AnimeShader assets or scene composition.

#### Scenario: Cel Orbit is active
- **WHEN** the probe is visible and motion is allowed
- **THEN** a geometric subject rolls through a warm outlined environment with changing light and depth

### Requirement: Alternative probes do not depend on Three.js
ASCII Signal and Kinetic Type SHALL render with browser canvas primitives and
their own visual grammars.

#### Scenario: ASCII Signal is active
- **WHEN** the probe is selected
- **THEN** a glyph field and rolling signal animate around transcript phrases

#### Scenario: Kinetic Type is active
- **WHEN** the probe is selected
- **THEN** a rolling disc materially changes the scale and position of editorial typography

### Requirement: Probe interaction is accessible and bounded
The visual lab SHALL provide keyboard-accessible direction controls, an
explicit selected state, responsive stages, and a reduced-motion presentation.

#### Scenario: Reduced motion is requested
- **WHEN** the browser reports `prefers-reduced-motion: reduce`
- **THEN** each probe presents a composed static frame without continuous animation

#### Scenario: Screen width changes
- **WHEN** the visual lab is viewed at mobile, tablet, or desktop width
- **THEN** controls, provenance, and the active stage remain legible without horizontal scrolling


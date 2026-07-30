# Change: Procedural visual style probes

## Why

The short-form pipeline can now hold or play provenance-backed visuals, but one
archival treatment is not a visual system. Reusing the public-domain comedy dev
corpus for an unrelated podcast demonstrated motion capability while failing
editorial relevance.

The operator explicitly approved procedural graphics and wants several
attractive options before choosing a production style. AnimeShader is the
primary craft reference.

## What changes

- Add a local `/visual-lab` route containing three materially different animated
  direction probes built around the same ZEROPOD conviction excerpt.
- Build:
  - **Cel Orbit** — Three.js cel shading, dark outlines, warm low-poly depth,
    isometric camera, and a rolling geometric subject.
  - **ASCII Signal** — dependency-free canvas glyph field and signal motion.
  - **Kinetic Type** — dependency-free canvas typography and rolling-object
    choreography.
- Add Three.js as the sole new production dependency for the WebGL probe.
- Support keyboard selection, responsive layouts, and reduced motion.
- Capture browser evidence for owner selection.

## Scope

### In

- Interactive visual probes and their local route.
- A durable product-boundary update allowing procedural non-photoreal visuals.
- Browser review at mobile, tablet, and desktop sizes.

### Out

- Selecting a winning direction without owner feedback.
- Wiring any probe into the Python/FFmpeg production renderer.
- Generated speech, narration, or photorealistic synthetic footage.
- Copying AnimeShader assets, scene composition, or source code.

## Impact

- New React/canvas/Three.js visual-lab surface under `web/`.
- One direct MIT production dependency: `three@0.185.1`, zero transitive
  dependencies, approximately 178 KiB gzip before application tree-shaking.
- No deploy impact; the editor remains loopback-only.


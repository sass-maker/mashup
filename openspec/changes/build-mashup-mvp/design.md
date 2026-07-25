# Design

## Pipeline

```
archive (mp4/mp3 + srt/vtt)
  -> ingest      normalise cues, probe media, transcribe if needed
  -> split       cues -> pause-delimited atoms -> self-contained segments
  -> enrich      one LLM pass -> SegmentMeta per segment
  -> embed       gateway embeddings -> float32 blobs in SQLite
  -> retrieve    MMR over cosine similarity -> candidate pool
  -> plan        beam search under a weighted objective -> sequence
  -> EDL         inspectable JSON, the editor's document
  -> render      snap, cut, normalise, concat, subtitle -> MP4
```

Every stage writes to the store and is independently resumable. This is not
tidiness — transcription and enrichment cost real money and minutes, and the
planning stage is the one that gets iterated on fifty times.

## Decisions

### SQLite with brute-force numpy, not pgvector

One creator's archive is order 10^3 segments. An exact scan of a 3k x 768
matrix is sub-millisecond. pgvector would add a service dependency to buy
nothing measurable. Revisit only if a single archive exceeds ~10^5 segments.

### Segmentation is deterministic first, LLM-assisted second

`build_atoms` groups cues on pauses and speaker changes — free, and an atom
boundary is always a safe cut because it never spans speech. `group_atoms`
then merges atoms toward a target segment length, breaking at the longest
pause and preferring atoms that open a new thought.

Pauses alone cannot distinguish a mid-story breath from the end of a story,
so this will sometimes cut a bit in half. The safety net is
`required_context` from enrichment: a fragment that needs prior setup gets
flagged, and the planner either satisfies it or is penalised for using it.
That is a better trade than an LLM boundary pass over every transcript.

### One shared beam search, three weight profiles

The temptation is three bespoke planners. That would make the experiment
meaningless — a win would be unattributable to the objective versus to
whichever planner got more attention. Instead `plan()` runs one beam search
and the strategies differ in exactly two ways: their entry in
`WEIGHT_PROFILES`, and whether they impose the chronological ordering
constraint. The two baselines use the same scoring code.

`duration_fit` is zeroed during search and restored for final scoring. A
two-clip prefix of a seven-minute set is not a duration failure, but a naive
objective would prune it as one.

### Scoring is eight separate terms, all surfaced

Each term is 0..1 and lands in the EDL alongside its weight. A creator who
gets a bad mashup can see that `context_completeness` was 0.4 rather than
guessing. This is also what makes the ablation honest.

`context_completeness` deserves a note: `required_context` is free text, so
satisfaction is tested by embedding the prerequisite and checking whether any
earlier clip in the sequence exceeds a cosine threshold. The threshold is
deliberately lenient — a false "missing context" discards a good clip, while
a false "covered" costs a moment of mild confusion.

`callback` only counts a shared entity across a gap of two or more clips.
Adjacent clips about the same thing are continuation, not a callback.

### Cuts snap outward, never inward

`snap_boundaries` moves a start slightly earlier and an end slightly later,
preferring the midpoint of a nearby silence. Clipping the first syllable of a
punchline is the single most audible failure a tool like this can produce, so
the asymmetry is intentional.

### Audio-only archives still render MP4

Podcast archives have no video. Rather than fork the renderer, audio-only
clips are composited over a neutral card at the target resolution, so a
mixed archive concatenates uniformly and the output is always a playable MP4.

## Dev corpus

`ybylcollection` on archive.org — *You Bet Your Life* with Groucho Marx.
42 MPEG4 episodes, Public Domain Mark 1.0, direct download, no YouTube and
no ToS question. One creator, one archive, and a comedy format built on
running gags, which is what gives the callback strategy something real to
find. No subtitles ship with it, so ingest transcribes locally.

`scripts/fetch_archive.py` enforces this rather than assuming it: it refuses
any item whose licence contains `-nd`, and writes `PROVENANCE.json` recording
the licence and per-file checksums.

## Risks

- **Whisper transcripts are noisy on 1950s broadcast audio.** Segment quality
  is bounded by transcript quality. If enrichment produces mush, that is the
  first thing to check, and a larger whisper model is the first lever.
- **The scoring weights are hand-set priors, not learned.** They are a
  hypothesis. The experiment is what tests them; the term breakdown in the
  EDL is what makes retuning tractable.
- **`can_open` / `can_end` / `energy` are model judgements** on a domain the
  model has no ground truth for. If the blind test shows the AI cuts losing,
  disagreement between these labels and human judgement is the prime suspect.
- **One archive is not three.** The kill criterion is explicitly cross-archive;
  a good result on Groucho alone proves considerably less than it appears to.

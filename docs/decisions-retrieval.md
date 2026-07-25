# Decision log — retrieval and scoring

Continues [`decisions.md`](decisions.md). These three entries all came out of
one change: making the embedding model swappable, which exposed how much of
the scoring layer had been silently fitted to a single model's behaviour.

---

## 12. Embeddings run locally by default

**Context.** Embeddings are re-run every time retrieval is tuned, and the first
gateway run needed four passes to drain 727 segments through rate limits and
provider fallbacks.

**Decision.** A local HuggingFace encoder is the default backend
(`BAAI/bge-base-en-v1.5`, 768d, CLS-pooled, L2-normalised). The gateway remains
available behind `MASHUP_EMBED_BACKEND=gateway`. Both satisfy one `Embedder`
protocol, so nothing downstream knows which is in play.

**Why.** The same 727 segments now embed in about nine seconds with no network
and no key, which turns re-embedding from a chore into a non-event. It also
removes the failure mode that did the most damage: the gateway silently falls
back between providers mid-run, and a run that mixes two vector spaces produces
confident, meaningless rankings. bge-base was chosen over a smaller encoder
because it was already in the local HuggingFace cache and is the same family as
the `bge-large-en-v1.5` the gateway run was pinned to, so results stay broadly
comparable across backends.

**Consequences.**

- **Asymmetric embedding.** BGE-family models are trained with a prefix on the
  query side only. The brief and its beats get it; transcript segments do not.
  A `required_context` string ("the audience knows he is a plumber") is a
  statement compared against other transcript, so it takes the document side.
- **Vectors record their model.** Two 384-dimension models mix without any
  dimension check noticing. `segments.embedding_model` is the only thing that
  can catch it, so `mashup embed` re-embeds automatically on a model change and
  `mashup status` reports what is stored.

**Trade-off accepted.** torch and transformers are a large optional dependency
for a tool whose other requirements are small. They live in a `local` extra,
present in the dev group so `uv sync` produces a working default, absent from a
gateway-only install.

---

## 13. Similarity thresholds are calibrated, not hard-coded

**Context.** The scoring terms carried fixed cosine cuts — 0.82 for redundancy,
0.55 for context coverage, a (0.30, 0.72) flow band. Swapping the embedding
model exposed them as accidental.

**Decision.** Each run measures the cuts from percentiles of the candidate
pool's own pairwise similarity distribution: p99 for redundancy, p25–p90 for
the flow band, p25 of the prerequisite-match distribution for context coverage.
The fixed values survive only as fallbacks below twelve embedded segments,
where percentiles are noise. The chosen cuts are written into the EDL so the
editor rescores against the same thresholds the build used.

**Why.** A fixed cosine threshold is a claim about one model's similarity
scale, not about comedy. Under bge-base this archive puts 99.9% of segment
pairs below 0.841, so the 0.82 redundancy cut fired on almost nothing:
`non_repetition` returned 1.00 for every candidate sequence — a term that had
stopped measuring anything while still looking healthy in the breakdown. The
same shift pushed nearly every adjacent pair inside the fixed flow band and
flattened `progression` too. Calibration is what makes the encoder swappable at
all.

**Trade-off accepted.** Scores are no longer comparable across runs with
different candidate pools, which is why the calibration is recorded rather than
recomputed. A tied block at the top of the distribution would put the
redundancy cut at the ceiling and switch the term off, so that case falls back
to the midpoint between median and maximum.

---

## 14. The callback strategy gets its own candidate pool

**Context.** The callback strategy scored 0.00 on callback while the random
control scored 0.35 — losing at its own objective to noise.

**Decision.** Three changes. Callbacks are counted only across a gap, across
two *different* recordings, and only on entities appearing in at most 5% of the
archive. And the callback strategy plans over the MMR pool plus segments that
reuse an entity already in it.

**Why.** Each of the three sources of the failure was invisible on its own.

- MMR exists to strip near-duplicate material, and two clips about the same
  running gag are near-duplicates in embedding space — so the retrieval stage
  was removing every plant-and-payoff pair before the planner saw the pool.
  Measured: zero cross-gap entity repeats in the MMR pool, several in the
  undiversified one.
- This corpus names the host in 96 segments and the sponsor in 48. Without a
  frequency filter almost any two clips read as a callback.
- A name recurring inside one episode is the original conversation continuing.
  Counting it credited the planner for something the source already did, which
  is precisely how the random control was outscoring the strategy.

**Result.** Callback is now the only condition scoring above zero on callback
(0.15, against 0.00 for both baselines).

**Trade-off accepted.** One strategy planning over a different pool is a
confound in the blind comparison, and it must be reported alongside any result.
The alternative — a strategy structurally unable to do the thing it is named
for — is worse.

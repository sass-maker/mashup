"""Embedding-based retrieval over an ingested archive."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mashup.gateway import Gateway
from mashup.models import Segment

# Cap the raw transcript we send to the embedder. The summary and topics carry
# most of the retrieval signal; the tail of a long segment mostly adds noise.
_EMBED_TEXT_CHARS = 1600


def embedding_text(seg: Segment) -> str:
    parts = []
    if seg.meta.summary:
        parts.append(seg.meta.summary)
    if seg.meta.topic:
        parts.append("Topics: " + ", ".join(seg.meta.topic))
    parts.append(seg.text[:_EMBED_TEXT_CHARS])
    return "\n".join(parts)


def embed_segments(
    segments: list[Segment], gw: Gateway, *, progress=None, batch_size: int = 64
) -> list[Segment]:
    """Attach embeddings in place; returns the same list for chaining."""
    todo = [s for s in segments if not s.embedding]
    if not todo:
        return segments
    # Chunk here rather than handing the whole archive to Gateway.embed so a
    # long run can report progress and so a mid-run failure keeps what it had.
    done = 0
    for i in range(0, len(todo), batch_size):
        chunk = todo[i : i + batch_size]
        vectors = gw.embed([embedding_text(s) for s in chunk], batch_size=batch_size)
        for seg, vec in zip(chunk, vectors, strict=True):
            seg.embedding = vec
        done += len(chunk)
        if progress:
            progress(done, len(todo))
    return segments


def _matrix(segments: list[Segment]) -> np.ndarray:
    mat = np.asarray([s.embedding for s in segments], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return mat / np.clip(norms, 1e-8, None)


def _unit(vec: list[float]) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    return arr / max(float(np.linalg.norm(arr)), 1e-8)


@dataclass
class Candidate:
    segment: Segment
    relevance: float


class Retriever:
    """Holds the normalised segment matrix so repeated planning is cheap."""

    def __init__(self, segments: list[Segment]) -> None:
        self.segments = [s for s in segments if s.embedding]
        if not self.segments:
            raise ValueError("No embedded segments. Run `mashup embed` first.")
        self.matrix = _matrix(self.segments)
        self._index = {s.id: i for i, s in enumerate(self.segments)}

    def similarity_to(self, query_vec: list[float]) -> np.ndarray:
        return self.matrix @ _unit(query_vec)

    def pairwise(self, a: Segment, b: Segment) -> float:
        ia, ib = self._index[a.id], self._index[b.id]
        return float(self.matrix[ia] @ self.matrix[ib])

    def search(
        self,
        query_vec: list[float],
        *,
        top_k: int = 60,
        floor: float = 0.0,
    ) -> list[Candidate]:
        sims = self.similarity_to(query_vec)
        order = np.argsort(-sims)
        out: list[Candidate] = []
        for i in order[:top_k]:
            score = float(sims[i])
            if score < floor:
                break
            out.append(Candidate(segment=self.segments[i], relevance=score))
        return out

    def mmr(
        self,
        query_vec: list[float],
        *,
        top_k: int = 40,
        pool: int = 150,
        lambda_: float = 0.7,
    ) -> list[Candidate]:
        """Maximal-marginal-relevance selection.

        Pure top-k retrieval on a single creator's archive returns many
        near-identical tellings of the same bit. MMR trades a little
        relevance for material the planner can actually build variety from.
        """
        sims = self.similarity_to(query_vec)
        pool_idx = list(np.argsort(-sims)[:pool])
        selected: list[int] = []
        while pool_idx and len(selected) < top_k:
            if not selected:
                best = max(pool_idx, key=lambda i: sims[i])
            else:
                sel = self.matrix[selected]

                def marginal(i: int, sel: np.ndarray = sel) -> float:
                    redundancy = float(np.max(sel @ self.matrix[i]))
                    return lambda_ * float(sims[i]) - (1 - lambda_) * redundancy

                best = max(pool_idx, key=marginal)
            pool_idx.remove(best)
            selected.append(int(best))
        return [Candidate(segment=self.segments[i], relevance=float(sims[i])) for i in selected]

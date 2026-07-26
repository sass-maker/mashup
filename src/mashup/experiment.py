"""The validation experiment.

The project exists to answer one question: does structure-aware sequencing
beat retrieving relevant clips and joining them? That question is only
answerable if the comparison is blind and the churn measurement is mechanical,
so both live in code rather than in a spreadsheet someone fills in by hand.

Five conditions, per the PRD:
  random          topic-matched, unordered      (control)
  semantic        relevance-sorted              (the bar to beat)
  chronological   AI cut
  escalation      AI cut
  callback        AI cut
"""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mashup.config import Config
from mashup.models import EDL
from mashup.pipeline import make_mashups
from mashup.render import save_edl

CONDITIONS = ("random", "semantic", "chronological", "escalation", "callback")
AI_CONDITIONS = ("chronological", "escalation", "callback")

# From the PRD's success criteria.
PREFERENCE_THRESHOLD = 4  # of 5 viewers
CONTEXT_COMPLETE_TARGET = 0.80
MAX_DEFECTS_PER_SEVEN_MIN = 2
MAX_CHURN = 0.30  # kill criterion: creators replacing more than this


@dataclass
class Blind:
    label: str  # A..E, shown to viewers
    condition: str  # the real strategy, hidden until unblinding
    edl_path: Path


def run_experiment(
    prompt: str,
    cfg: Config,
    *,
    outdir: Path,
    target: float,
    seed: int = 0,
    snap: bool = True,
) -> list[Blind]:
    """Generate all five conditions under blind labels."""
    outdir.mkdir(parents=True, exist_ok=True)
    edls = make_mashups(
        prompt,
        cfg,
        target=target,
        strategies=AI_CONDITIONS,
        include_baselines=True,
        snap=snap,
    )
    by_condition = {e.strategy: e for e in edls}
    missing = [c for c in CONDITIONS if c not in by_condition]
    if missing:
        raise RuntimeError(f"planner produced no output for: {', '.join(missing)}")

    order = list(CONDITIONS)
    random.Random(seed).shuffle(order)
    labels = [chr(ord("A") + i) for i in range(len(order))]

    blinds: list[Blind] = []
    for label, condition in zip(labels, order, strict=True):
        path = outdir / f"{label}.json"
        save_edl(by_condition[condition], path)
        blinds.append(Blind(label=label, condition=condition, edl_path=path))

    # The key is written separately so it can be withheld from raters.
    (outdir / "KEY.json").write_text(
        json.dumps(
            {
                "prompt": prompt,
                "target_duration": target,
                "seed": seed,
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "mapping": {b.label: b.condition for b in blinds},
                "scores": {b.label: by_condition[b.condition].score for b in blinds},
            },
            indent=2,
        )
    )
    write_rating_sheet(blinds, outdir / "ratings.csv")
    return blinds


VIEWERS = 5


def viewing_orders(labels: list[str], viewers: int = VIEWERS) -> list[list[str]]:
    """One viewing order per viewer, rotated so no variant keeps a position.

    Showing every viewer A..E in label order confounds the variant with when it
    was watched: whatever plays first is judged fresh and sets the anchor for
    the rest, and whatever plays last is judged tired. Those effects would land
    entirely on one condition. A cyclic square gives each variant each position
    exactly once across five viewers, so position averages out of the ranking.

    It balances position, not carryover — variant order pairs are not balanced,
    which would need ten viewers for five variants. With five viewers this is
    the most that can be balanced.
    """
    ordered = sorted(labels)
    return [[ordered[(i + v) % len(ordered)] for i in range(len(ordered))] for v in range(viewers)]


def write_rating_sheet(blinds: list[Blind], path: Path) -> None:
    """One row per viewer per variant, in the order that viewer watches them."""
    orders = viewing_orders([b.label for b in blinds])
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "viewer",
                "position",  # watch in this order; 1 is first
                "variant",
                "overall_rank",  # 1 = best of the five
                "clips_total",
                "clips_context_incomplete",  # count that felt like they needed setup
                "defects",  # obvious repetitions or broken transitions
                "would_publish",  # yes/no
                "notes",
            ]
        )
        for viewer, order in enumerate(orders, start=1):
            for position, label in enumerate(order, start=1):
                writer.writerow([viewer, position, label, "", "", "", "", "", ""])


# ---- analysis -----------------------------------------------------------


def _load_key(outdir: Path) -> dict[str, str]:
    key = json.loads((outdir / "KEY.json").read_text())
    return key["mapping"]


def summarise_ratings(outdir: Path) -> dict:
    """Unblind the ratings and check them against the PRD's criteria."""
    mapping = _load_key(outdir)
    rows = [
        r
        for r in csv.DictReader((outdir / "ratings.csv").open())
        if (r.get("overall_rank") or "").strip()
    ]
    if not rows:
        raise RuntimeError("ratings.csv has no completed rows")

    by_viewer: dict[str, dict[str, int]] = {}
    context_ratio: dict[str, list[float]] = {}
    defects: dict[str, list[float]] = {}

    for row in rows:
        condition = mapping[row["variant"]]
        by_viewer.setdefault(row["viewer"], {})[condition] = int(row["overall_rank"])
        total = float(row.get("clips_total") or 0)
        if total:
            incomplete = float(row.get("clips_context_incomplete") or 0)
            context_ratio.setdefault(condition, []).append(1.0 - incomplete / total)
        if (row.get("defects") or "").strip():
            defects.setdefault(condition, []).append(float(row["defects"]))

    # Criterion 1: an AI cut beats the semantic baseline for >= 4 of 5 viewers.
    beats_semantic = {c: 0 for c in AI_CONDITIONS}
    for ranks in by_viewer.values():
        baseline = ranks.get("semantic")
        if baseline is None:
            continue
        for cond in AI_CONDITIONS:
            if cond in ranks and ranks[cond] < baseline:
                beats_semantic[cond] += 1

    viewers = len(by_viewer)
    best_ai = max(beats_semantic, key=lambda c: beats_semantic[c])

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    return {
        "viewers": viewers,
        "beats_semantic": beats_semantic,
        "best_ai_condition": best_ai,
        "context_completeness": {c: mean(v) for c, v in context_ratio.items()},
        "defects_mean": {c: mean(v) for c, v in defects.items()},
        "criteria": {
            "preference": beats_semantic[best_ai] >= min(PREFERENCE_THRESHOLD, viewers),
            "context_complete": mean(context_ratio.get(best_ai, [])) >= CONTEXT_COMPLETE_TARGET,
            "defects": mean(defects.get(best_ai, [])) < MAX_DEFECTS_PER_SEVEN_MIN,
        },
    }


def timeline_churn(original: EDL, edited: EDL) -> dict:
    """How much of the generated timeline the creator had to change.

    This is the kill criterion, measured rather than estimated: above 30%
    replacement across three archives, the sequencing is not earning its keep.
    """
    orig_ids = [c.segment_id for c in original.clips]
    edit_ids = [c.segment_id for c in edited.clips]
    orig_set, edit_set = set(orig_ids), set(edit_ids)

    kept = orig_set & edit_set
    removed = orig_set - edit_set
    added = edit_set - orig_set

    # Reorder counts only among survivors, so a removal is not double-charged.
    survivors_orig = [i for i in orig_ids if i in kept]
    survivors_edit = [i for i in edit_ids if i in kept]
    reordered = sum(1 for a, b in zip(survivors_orig, survivors_edit, strict=False) if a != b)

    total = len(orig_ids) or 1
    churn = (len(removed) + len(added)) / (total + len(added))
    return {
        "clips_original": len(orig_ids),
        "clips_edited": len(edit_ids),
        "kept": len(kept),
        "removed": len(removed),
        "added": len(added),
        "reordered": reordered,
        "churn": round(churn, 4),
        "passes_kill_criterion": churn <= MAX_CHURN,
    }

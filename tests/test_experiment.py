"""The validation experiment's own bookkeeping.

This module decides whether the project's central claim passes or fails, so
its arithmetic is worth testing more carefully than the code it grades.
"""

from __future__ import annotations

import csv
import json

import pytest

from mashup.experiment import (
    CONDITIONS,
    VIEWERS,
    Blind,
    summarise_ratings,
    viewing_orders,
    write_rating_sheet,
)

LABELS = ["A", "B", "C", "D", "E"]


def _blinds(tmp_path):
    return [
        Blind(label=label, condition=cond, edl_path=tmp_path / f"{label}.json")
        for label, cond in zip(LABELS, CONDITIONS, strict=True)
    ]


# ---- viewing order ------------------------------------------------------


def test_every_variant_takes_every_position_exactly_once():
    """The Latin square property. Without it, position effects — fresh
    attention first, fatigue last — land on whichever variant is fixed there."""
    orders = viewing_orders(LABELS)
    for position in range(len(LABELS)):
        seen = [order[position] for order in orders]
        assert sorted(seen) == LABELS


def test_each_viewer_sees_all_variants_once():
    for order in viewing_orders(LABELS):
        assert sorted(order) == LABELS


def test_orders_are_distinct():
    orders = viewing_orders(LABELS)
    assert len({tuple(o) for o in orders}) == VIEWERS


def test_order_is_deterministic():
    """Two people generating the sheet must hand raters the same order."""
    assert viewing_orders(LABELS) == viewing_orders(LABELS)


def test_labels_need_not_arrive_sorted():
    assert viewing_orders(["E", "C", "A", "D", "B"]) == viewing_orders(LABELS)


# ---- rating sheet -------------------------------------------------------


def test_sheet_has_one_row_per_viewer_per_variant(tmp_path):
    path = tmp_path / "ratings.csv"
    write_rating_sheet(_blinds(tmp_path), path)
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == VIEWERS * len(LABELS)
    assert {r["variant"] for r in rows} == set(LABELS)


def test_sheet_rows_are_in_viewing_order(tmp_path):
    """The rater works down the sheet, so row order *is* the instruction."""
    path = tmp_path / "ratings.csv"
    write_rating_sheet(_blinds(tmp_path), path)
    rows = list(csv.DictReader(path.open()))
    for viewer, expected in enumerate(viewing_orders(LABELS), start=1):
        got = [r["variant"] for r in rows if r["viewer"] == str(viewer)]
        assert got == expected
        positions = [r["position"] for r in rows if r["viewer"] == str(viewer)]
        assert positions == ["1", "2", "3", "4", "5"]


def test_sheet_leaves_judgement_columns_blank(tmp_path):
    path = tmp_path / "ratings.csv"
    write_rating_sheet(_blinds(tmp_path), path)
    for row in csv.DictReader(path.open()):
        for field in ("overall_rank", "clips_total", "defects", "would_publish", "notes"):
            assert row[field] == ""


# ---- unblinding ---------------------------------------------------------


def _write_key(tmp_path):
    mapping = dict(zip(LABELS, CONDITIONS, strict=True))
    (tmp_path / "KEY.json").write_text(json.dumps({"mapping": mapping}))
    return {cond: label for label, cond in mapping.items()}


def _fill(tmp_path, ranks_by_viewer, **extra):
    """Write a completed sheet. `ranks_by_viewer` maps condition -> rank."""
    label_of = _write_key(tmp_path)
    path = tmp_path / "ratings.csv"
    write_rating_sheet(_blinds(tmp_path), path)
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        viewer = int(row["viewer"])
        if viewer > len(ranks_by_viewer):
            continue
        ranks = ranks_by_viewer[viewer - 1]
        for cond, rank in ranks.items():
            if row["variant"] == label_of[cond]:
                row["overall_rank"] = str(rank)
                row.update(extra)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_added_position_column_does_not_break_unblinding(tmp_path):
    """The sheet grew a column; the analysis reads by name, not by index."""
    _fill(tmp_path, [{"escalation": 1, "semantic": 2}] * 5)
    result = summarise_ratings(tmp_path)
    assert result["viewers"] == 5
    assert result["beats_semantic"]["escalation"] == 5


def test_preference_criterion_needs_four_of_five(tmp_path):
    ranks = [{"escalation": 1, "semantic": 2}] * 3 + [{"escalation": 2, "semantic": 1}] * 2
    _fill(tmp_path, ranks)
    result = summarise_ratings(tmp_path)
    assert result["beats_semantic"]["escalation"] == 3
    assert result["criteria"]["preference"] is False


def test_fewer_viewers_are_scored_against_the_viewers_present(tmp_path):
    """Two viewers agreeing is not a pass of "four of five", but the harness
    still reports against what it has rather than silently failing."""
    _fill(tmp_path, [{"escalation": 1, "semantic": 2}] * 2)
    result = summarise_ratings(tmp_path)
    assert result["viewers"] == 2
    assert result["criteria"]["preference"] is True


def test_empty_sheet_is_an_error_not_a_verdict(tmp_path):
    _write_key(tmp_path)
    write_rating_sheet(_blinds(tmp_path), tmp_path / "ratings.csv")
    with pytest.raises(RuntimeError, match="no completed rows"):
        summarise_ratings(tmp_path)


def test_context_completeness_is_a_ratio_of_counted_clips(tmp_path):
    _fill(
        tmp_path,
        [{"escalation": 1, "semantic": 2}] * 5,
        clips_total="10",
        clips_context_incomplete="3",
    )
    result = summarise_ratings(tmp_path)
    assert result["context_completeness"]["escalation"] == pytest.approx(0.7)
    assert result["criteria"]["context_complete"] is False

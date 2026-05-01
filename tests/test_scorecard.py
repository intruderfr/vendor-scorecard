"""Unit tests for vendor-scorecard."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scorecard import (  # noqa: E402
    Criterion,
    VendorScore,
    load_criteria,
    load_vendors,
    rank,
    render_markdown,
)


# ---------- Criterion ----------------------------------------------------


def test_criterion_rejects_zero_weight():
    with pytest.raises(ValueError):
        Criterion(key="x", label="X", weight=0)


def test_criterion_rejects_weight_above_one():
    with pytest.raises(ValueError):
        Criterion(key="x", label="X", weight=1.5)


# ---------- VendorScore weighted total ------------------------------------


def test_perfect_scores_yield_100():
    criteria = [
        Criterion("a", "A", 0.5),
        Criterion("b", "B", 0.5),
    ]
    v = VendorScore(name="Top", raw={"a": 5, "b": 5})
    assert v.weighted_total(criteria) == 100.0


def test_minimum_scores_yield_0():
    criteria = [
        Criterion("a", "A", 0.5),
        Criterion("b", "B", 0.5),
    ]
    v = VendorScore(name="Bottom", raw={"a": 1, "b": 1})
    assert v.weighted_total(criteria) == 0.0


def test_missing_criterion_contributes_zero():
    criteria = [
        Criterion("a", "A", 0.5),
        Criterion("b", "B", 0.5),
    ]
    v = VendorScore(name="Partial", raw={"a": 5})
    # a=5 → 1.0 * 0.5 = 0.5; b missing → 0
    assert v.weighted_total(criteria) == 50.0


def test_weights_apply_correctly():
    criteria = [
        Criterion("a", "A", 0.8),
        Criterion("b", "B", 0.2),
    ]
    v = VendorScore(name="V", raw={"a": 5, "b": 1})
    # a=5 → 1.0 * 0.8 = 0.8 ; b=1 → 0 * 0.2 = 0
    assert v.weighted_total(criteria) == 80.0


# ---------- File loading -------------------------------------------------


def test_load_criteria_validates_weight_sum(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "criteria:\n"
        "  - {key: a, weight: 0.5}\n"
        "  - {key: b, weight: 0.3}\n"
    )
    with pytest.raises(ValueError, match="sum to 1.0"):
        load_criteria(bad)


def test_load_criteria_accepts_valid(tmp_path: Path):
    good = tmp_path / "good.yaml"
    good.write_text(
        "criteria:\n"
        "  - {key: a, weight: 0.5}\n"
        "  - {key: b, weight: 0.5}\n"
    )
    cs = load_criteria(good)
    assert [c.key for c in cs] == ["a", "b"]


def test_load_vendors_requires_vendor_column(tmp_path: Path):
    csv_path = tmp_path / "v.csv"
    csv_path.write_text("name,a,b\nFoo,3,4\n")
    criteria = [Criterion("a", "A", 0.5), Criterion("b", "B", 0.5)]
    with pytest.raises(ValueError, match="missing required 'vendor' column"):
        load_vendors(csv_path, criteria)


def test_load_vendors_detects_missing_criterion_column(tmp_path: Path):
    csv_path = tmp_path / "v.csv"
    csv_path.write_text("vendor,a\nFoo,3\n")
    criteria = [Criterion("a", "A", 0.5), Criterion("b", "B", 0.5)]
    with pytest.raises(ValueError, match="missing columns for criteria"):
        load_vendors(csv_path, criteria)


# ---------- Ranking & report --------------------------------------------


def test_ranking_sorts_descending():
    criteria = [Criterion("a", "A", 1.0)]
    vendors = [
        VendorScore("Low", {"a": 2}),
        VendorScore("High", {"a": 5}),
        VendorScore("Mid", {"a": 3}),
    ]
    ordered = [v.name for v, _ in rank(vendors, criteria)]
    assert ordered == ["High", "Mid", "Low"]


def test_render_markdown_contains_winner():
    criteria = [Criterion("a", "A", 1.0)]
    ranked = rank(
        [VendorScore("Top", {"a": 5}), VendorScore("Bottom", {"a": 1})],
        criteria,
    )
    md = render_markdown(ranked, criteria)
    assert "Vendor Scorecard" in md
    assert "**Top**" in md
    assert "Recommendation" in md


def test_end_to_end_with_example_files():
    """Run against the bundled example files to catch shape regressions."""
    repo = Path(__file__).resolve().parent.parent
    criteria = load_criteria(repo / "criteria.example.yaml")
    vendors = load_vendors(repo / "vendors.example.csv", criteria)
    ranked = rank(vendors, criteria)
    assert len(ranked) == 5
    # Acme edges out GlobeTech here because its lower cost (3 vs 2)
    # outweighs GlobeTech's slight lead on the qualitative axes
    # given the 20% cost weight — a useful demonstration that
    # weighting matters more than vibes.
    assert ranked[0][0].name == "Acme Cloud Suite"
    assert ranked[1][0].name == "GlobeTech Platform"
    md = render_markdown(ranked, criteria)
    assert "| 1 | **Acme Cloud Suite**" in md

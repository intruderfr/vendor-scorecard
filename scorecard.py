#!/usr/bin/env python3
"""
vendor-scorecard — weighted vendor evaluation CLI.

Reads a YAML file of weighted criteria and a CSV of raw vendor scores,
then produces a weighted ranking and a Markdown report suitable for
RFP shortlisting, board reviews, and procurement decisions.

Usage:
    python scorecard.py score \
        --criteria criteria.example.yaml \
        --vendors vendors.example.csv \
        --output report.md

Author: Aslam Ahamed — Head of IT @ Prestige One Developments, Dubai
License: MIT
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write(
        "Missing dependency 'PyYAML'. Install with: pip install pyyaml\n"
    )
    sys.exit(1)


# ---------- Data model ----------------------------------------------------


@dataclass
class Criterion:
    """A single weighted scoring criterion (e.g. 'security', weight 0.20)."""

    key: str
    label: str
    weight: float
    description: str = ""

    def __post_init__(self) -> None:
        if not 0 < self.weight <= 1:
            raise ValueError(
                f"Criterion '{self.key}' weight must be in (0, 1]; got {self.weight}"
            )


@dataclass
class VendorScore:
    """A vendor with raw 1-5 scores per criterion key."""

    name: str
    raw: Dict[str, float] = field(default_factory=dict)
    notes: str = ""

    def weighted_total(self, criteria: List[Criterion]) -> float:
        """Compute the weighted total across all criteria.

        Raw scores are normalised from a 1-5 scale to 0-1 before
        applying weights. Missing criteria contribute 0.
        """
        total = 0.0
        for c in criteria:
            raw = self.raw.get(c.key, 0)
            normalised = max(0.0, min(1.0, (float(raw) - 1) / 4))
            total += normalised * c.weight
        return round(total * 100, 2)  # return as a 0-100 score


# ---------- Loaders -------------------------------------------------------


def load_criteria(path: Path) -> List[Criterion]:
    """Load the criteria YAML file and validate weights sum to 1.0."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "criteria" not in data:
        raise ValueError(f"{path}: expected a top-level 'criteria' list")

    criteria = [
        Criterion(
            key=c["key"],
            label=c.get("label", c["key"].replace("_", " ").title()),
            weight=float(c["weight"]),
            description=c.get("description", ""),
        )
        for c in data["criteria"]
    ]

    total = sum(c.weight for c in criteria)
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Criterion weights must sum to 1.0 (got {total:.4f}). "
            "Adjust your criteria file."
        )
    return criteria


def load_vendors(path: Path, criteria: List[Criterion]) -> List[VendorScore]:
    """Load vendor scores from a CSV. Required column 'vendor'; one column per criterion key."""
    keys = [c.key for c in criteria]
    vendors: List[VendorScore] = []

    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "vendor" not in reader.fieldnames:
            raise ValueError(f"{path}: missing required 'vendor' column")

        missing = [k for k in keys if k not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"{path}: missing columns for criteria: {', '.join(missing)}"
            )

        for row in reader:
            name = row["vendor"].strip()
            if not name:
                continue
            raw = {}
            for k in keys:
                value = row.get(k, "").strip()
                try:
                    raw[k] = float(value) if value else 0.0
                except ValueError:
                    raise ValueError(
                        f"{path}: vendor '{name}' has non-numeric '{k}' = {value!r}"
                    )
            vendors.append(VendorScore(name=name, raw=raw, notes=row.get("notes", "")))

    if not vendors:
        raise ValueError(f"{path}: no vendor rows found")
    return vendors


# ---------- Reporting -----------------------------------------------------


def rank(
    vendors: List[VendorScore], criteria: List[Criterion]
) -> List[Tuple[VendorScore, float]]:
    """Return vendors sorted by weighted total (descending)."""
    scored = [(v, v.weighted_total(criteria)) for v in vendors]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def render_markdown(
    ranked: List[Tuple[VendorScore, float]], criteria: List[Criterion]
) -> str:
    """Render the ranking and per-criterion matrix as a Markdown report."""
    out: List[str] = []
    out.append("# Vendor Scorecard\n")
    out.append(f"_Evaluated **{len(ranked)} vendors** across **{len(criteria)} weighted criteria**._\n")

    # Weighted ranking
    out.append("## Weighted Ranking\n")
    out.append("| Rank | Vendor | Score / 100 | Notes |")
    out.append("|------|--------|-------------|-------|")
    for i, (v, score) in enumerate(ranked, start=1):
        notes = (v.notes or "").replace("|", "\\|")
        out.append(f"| {i} | **{v.name}** | {score:.2f} | {notes} |")

    # Criteria definitions
    out.append("\n## Criteria & Weights\n")
    out.append("| Key | Label | Weight | Description |")
    out.append("|-----|-------|--------|-------------|")
    for c in criteria:
        out.append(
            f"| `{c.key}` | {c.label} | {c.weight:.2%} | {c.description} |"
        )

    # Raw score matrix
    out.append("\n## Raw Score Matrix (1-5)\n")
    header = "| Vendor | " + " | ".join(c.label for c in criteria) + " |"
    sep = "|--------|" + "|".join(["---"] * len(criteria)) + "|"
    out.append(header)
    out.append(sep)
    for v, _ in ranked:
        cells = [f"{v.raw.get(c.key, 0):.1f}" for c in criteria]
        out.append(f"| {v.name} | " + " | ".join(cells) + " |")

    # Recommendation
    if ranked:
        winner, top_score = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        out.append("\n## Recommendation\n")
        out.append(
            f"**{winner.name}** leads with a weighted score of **{top_score:.2f}/100**."
        )
        if runner_up:
            gap = top_score - runner_up[1]
            out.append(
                f"  Runner-up is _{runner_up[0].name}_ ({runner_up[1]:.2f}); "
                f"gap of {gap:.2f} points."
            )
        out.append("")

    return "\n".join(out) + "\n"


# ---------- CLI -----------------------------------------------------------


def cmd_score(args: argparse.Namespace) -> int:
    criteria = load_criteria(Path(args.criteria))
    vendors = load_vendors(Path(args.vendors), criteria)
    ranked = rank(vendors, criteria)

    if args.format == "json":
        payload = {
            "criteria": [c.__dict__ for c in criteria],
            "ranking": [
                {
                    "vendor": v.name,
                    "score": s,
                    "raw": v.raw,
                    "notes": v.notes,
                }
                for v, s in ranked
            ],
        }
        text = json.dumps(payload, indent=2)
    else:
        text = render_markdown(ranked, criteria)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate criteria & vendor files without producing a report."""
    criteria = load_criteria(Path(args.criteria))
    print(
        f"OK criteria: {len(criteria)} entries, weights sum to "
        f"{sum(c.weight for c in criteria):.4f}"
    )
    if args.vendors:
        vendors = load_vendors(Path(args.vendors), criteria)
        print(f"OK vendors:  {len(vendors)} rows for "
              f"{len(criteria)} criteria")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vendor-scorecard",
        description="Weighted vendor evaluation CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score", help="Score vendors and emit a report")
    p_score.add_argument("--criteria", required=True, help="Path to criteria YAML")
    p_score.add_argument("--vendors", required=True, help="Path to vendors CSV")
    p_score.add_argument("--output", help="Output file (default: stdout)")
    p_score.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    p_score.set_defaults(func=cmd_score)

    p_val = sub.add_parser("validate", help="Validate criteria/vendors files")
    p_val.add_argument("--criteria", required=True)
    p_val.add_argument("--vendors", help="Optional — also validate this CSV")
    p_val.set_defaults(func=cmd_validate)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

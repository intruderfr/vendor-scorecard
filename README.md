# vendor-scorecard

[![ci](https://github.com/intruderfr/vendor-scorecard/actions/workflows/ci.yml/badge.svg)](https://github.com/intruderfr/vendor-scorecard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A no-nonsense Python CLI for running **weighted vendor evaluations** against
a defined set of criteria. Built for IT leaders who run RFPs, procurement
shortlists, and vendor reviews and need a defensible, repeatable scoring
process — not a gut-feel deck slide.

You define **what matters and how much** in a YAML file, score each vendor
1-5 in a CSV, and the tool produces a ranked Markdown report you can drop
straight into a board pack or steering committee deck.

## Why this exists

Most "vendor scoring" in IT departments looks like one of these:

- A consultant's spreadsheet with mystery formulas
- A whiteboard list of vendors with thumbs-up/thumbs-down emoji
- A 60-page RFP response that no one actually reads end to end

`vendor-scorecard` gives you a **transparent, version-controllable**
alternative. Criteria, weights, and raw scores all live in plain-text files
that diff cleanly in git, so when leadership asks "why did we pick X?" six
months later, the answer is checked in alongside the contract.

## Features

- **Weighted scoring** with explicit, validated weights (must sum to 1.0)
- **Plain text inputs** — YAML criteria, CSV vendor scores
- **Markdown report** with ranking, criteria definitions, raw matrix, and a
  one-line recommendation
- **JSON output** mode for downstream tooling (BI, dashboards, archives)
- **Validate** subcommand to catch typos before review meetings
- **Zero runtime dependencies** beyond PyYAML
- **Tested** across Python 3.10, 3.11, 3.12

## Install

```bash
git clone https://github.com/intruderfr/vendor-scorecard.git
cd vendor-scorecard
pip install -r requirements.txt
```

## Quick start

```bash
# Validate the bundled examples
python scorecard.py validate \
  --criteria criteria.example.yaml \
  --vendors vendors.example.csv

# Generate a Markdown report
python scorecard.py score \
  --criteria criteria.example.yaml \
  --vendors vendors.example.csv \
  --output report.md

# Or get JSON for downstream tooling
python scorecard.py score \
  --criteria criteria.example.yaml \
  --vendors vendors.example.csv \
  --format json \
  --output report.json
```

## Defining your criteria

Criteria live in a YAML file. Each entry has a `key` (used to match the CSV
column), a human label, a weight in `(0, 1]`, and a description. **Weights
across all criteria must sum to exactly 1.0** — this is enforced and the
tool refuses to run otherwise, so you cannot accidentally publish a
scorecard where weights drift.

```yaml
criteria:
  - key: cost
    label: Total Cost of Ownership
    weight: 0.20
    description: License + implementation + ongoing run cost over 3 years.

  - key: security
    label: Security Posture
    weight: 0.20
    description: SOC2 / ISO27001 status, encryption, IAM, vuln history.

  - key: reliability
    label: Reliability & SLA
    weight: 0.15
    description: Uptime SLA, status page transparency, regional redundancy.

  # ... must sum to 1.0
```

## Scoring vendors

Vendor scores live in a CSV. The first column must be `vendor`; subsequent
columns must match the `key` values in your YAML. Scores are on a **1-5
scale** (1 = poor, 3 = acceptable, 5 = excellent). Optional `notes` column
flows into the report.

```csv
vendor,cost,security,reliability,support,compliance,scalability,integration,roadmap,notes
Acme Cloud,3,5,5,4,5,5,4,4,Strong incumbent
ContosoStack,5,2,3,3,2,4,3,2,Cheapest but security gaps
```

## How scoring works

For each vendor:

1. Each raw 1-5 score is normalised to 0-1 via `(raw - 1) / 4`.
2. The normalised score is multiplied by that criterion's weight.
3. Results are summed and scaled to **0-100** for readability.

A vendor scoring 5 on every criterion gets 100. A vendor scoring 1 on every
criterion gets 0. Missing criteria contribute 0, so leaving a column blank
penalises the vendor - which is the right behaviour for evaluation.

## Sample output

```
| Rank | Vendor              | Score / 100 |
|------|---------------------|-------------|
| 1    | Acme Cloud Suite    | 83.75       |
| 2    | GlobeTech Platform  | 82.50       |
| 3    | PivotalWorks        | 72.50       |
| 4    | Northwind ERP       | 57.50       |
| 5    | ContosoStack        | 53.75       |
```

The example dataset deliberately shows that a slightly cheaper, slightly
less polished incumbent can edge out a "premium" vendor when cost has real
weight. That's the whole point of weighted scoring — your priorities, made
visible.

## Tips for running a real RFP with this

1. **Set criteria and weights *before* scoring any vendor.** Otherwise the
   weights end up reflecting whoever scores best, which defeats the point.
2. **Score independently first, then reconcile.** Each evaluator scores the
   vendors blind, then the team meets to reconcile differences > 1 point.
3. **Commit the inputs to git.** When the contract review happens 18 months
   later, you'll thank yourself.
4. **Re-run quarterly for incumbent vendors.** A scorecard that only exists
   at procurement time is a sales tool, not a management tool.

## Running the tests

```bash
pip install pytest
pytest tests/ -v
```

## Roadmap

- [ ] Side-by-side diff between two scorecard runs (renewal vs initial)
- [ ] HTML output with embedded radar chart
- [ ] Multi-evaluator merge (per-evaluator CSVs → averaged matrix)
- [ ] Weighted-by-stakeholder mode (different weights per evaluator)

PRs welcome.

## License

MIT — see [LICENSE](LICENSE).

## Author

**Aslam Ahamed** — Head of IT @ Prestige One Developments, Dubai
[LinkedIn](https://www.linkedin.com/in/aslam-ahamed/)

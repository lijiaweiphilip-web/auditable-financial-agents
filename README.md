# Auditable Financial Agents

[![CI](https://github.com/lijiaweiphilip-web/auditable-financial-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/lijiaweiphilip-web/auditable-financial-agents/actions/workflows/ci.yml)
[![Python 3.10-3.12](https://img.shields.io/badge/python-3.10--3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Public-safe research code companion for **evidence-grounded review of financial
artifacts produced by tool-using AI agents**.

This repository implements the core research-label logic described in the
accepted sole-authored ACM HCOMP 2026 paper:

> Jiawei Li. *From Answers to Audit Opinions: Cost-Aware Expert Verification of
> Financial Artifacts from Tool-Using LLM Agents.* HCOMP 2026.
> [DOI: 10.1145/3834580.3838756](https://doi.org/10.1145/3834580.3838756)

It is a compact, inspectable code companion using synthetic/public-safe cases.
It is **not** the official HCOMP implementation, a full paper reproduction, or
the paper's SEC-backed empirical dataset.

## Research question

When a tool-using AI system produces a financial table, memo, or calculation,
can review decisions expose evidence validity, materiality, formula failures,
scope limits, trace gaps, and human-escalation triggers instead of accepting a
plausible-looking artifact blindly?

## Quickstart

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# POSIX:   source .venv/bin/activate
python -m pip install -e .[dev]
financial-agent-audit demo --examples examples
python -m unittest discover -s tests -v
coverage run -m unittest discover -s tests -v
coverage report --fail-under=97
```

Evaluate one synthetic case and save its certificate:

```bash
financial-agent-audit evaluate examples/qualified_formula_error.json \
  --output runs/qualified_formula_error.json
```

Regenerate the deterministic public-safe snapshot:

```bash
python scripts/build_demo_snapshot.py
```

## Implemented research logic

- Clean / Qualified / Adverse / Disclaimer research labels;
- claim-level provenance and entity/period/metric alignment;
- numeric and qualitative materiality, formula-check failure, normalized
  pervasiveness, and claim-level severity decisions;
- evidence sufficiency, critical-matter prioritization, and false-clean helper;
- optional action-trace checks for failed, skipped, expected-but-missing, or
  incompletely documented executions;
- schema-v2 trace counts with nullable executed-action documentation coverage;
- deterministic synthetic examples, tests, coverage, CI and hash manifest.

The current branch is a `v0.2.0` behavior-change candidate, not a published
release. Its input contract rejects partial numeric claims, non-boolean flags,
and non-finite values; unknown formula checks are reviewable by default.

The action-trace code is a **prospective research extension**, not an HCOMP
2026 accepted-paper result. See [`docs/PAPER_MAPPING.md`](docs/PAPER_MAPPING.md)
and [`docs/TRACE_EXTENSION.md`](docs/TRACE_EXTENSION.md).

For a compact paper-to-code view, see [`docs/RESEARCH_MAP.md`](docs/RESEARCH_MAP.md).
The formal prototype rules are summarized in
[`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Synthetic result boundary

[`results/DEMO_RESULTS.md`](results/DEMO_RESULTS.md) and
[`results/demo_results.json`](results/demo_results.json) are deterministic
synthetic functionality/evidence snapshots. They are not the HCOMP empirical
results and do not reproduce the paper's 400-case diagnostic, 100-case
single-expert batch or 40-case blind re-audit.

## Non-claims

This prototype is not a statutory audit opinion, assurance service, investment,
accounting or legal advice, regulatory certification, trading strategy,
portfolio recommendation, production risk approval, or replacement for a
qualified financial reviewer. No customer data, private filings, credentials,
OpenReview materials or reviewer information belong here. See
[`docs/NON_CLAIMS.md`](docs/NON_CLAIMS.md).

## Citation

If this prototype is useful, cite the repository and the preferred archival
paper in [`CITATION.cff`](CITATION.cff).

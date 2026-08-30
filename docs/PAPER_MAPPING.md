# Mapping to the HCOMP 2026 paper

Paper: **From Answers to Audit Opinions: Cost-Aware Expert Verification of Financial Artifacts from Tool-Using LLM Agents**  
DOI: https://doi.org/10.1145/3834580.3838756

## Implemented in this public-safe prototype

- Four research labels: Clean / Qualified / Adverse / Disclaimer.
- Claim-level evidence validity.
- Materiality-normalized numeric severity when source values and thresholds are supplied.
- Qualitative severity override.
- Formula-check failures.
- Evidence sufficiency and scope limitation.
- Material-issue pervasiveness.
- Critical-matter prioritization.
- Batch false-clean-rate helper.
- Normalized-weight aggregation and claim-level effective-severity decision
  invariants in the public prototype.
- Executed-action documentation coverage and explicit expected-action trace
  semantics as a prospective extension.

## Simplified relative to the paper

This repository is intentionally compact. It does **not** claim to reproduce the paper's full SEC-backed dataset, expert protocol, 400-case diagnostic, 100-case single-expert batch, 40-case blind re-audit, threshold-sensitivity grid, or all certificate/checker fields.

Those paper results should be cited from the archival paper, not inferred from this demo repository.

## Public-data boundary

The checked-in examples are synthetic and designed to exercise the logic. No raw SEC dataset or expert-adjudication records are required to understand the code path.

## Future reproducibility option

A later release may add a public, redistributable mini benchmark built from stable public-company facts if the provenance, licensing, and paper-artifact release policy are all rechecked first.

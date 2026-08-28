# Changelog

## Unreleased — formal semantics hardening candidate

- Make label decisions invariant to uniform positive claim-weight scaling by
  using normalized aggregate weights and claim-level effective severity.
- Preserve `max_weighted_severity` as a deprecated diagnostic and add
  `max_effective_severity`.
- Clarify executed-action documentation coverage versus task completeness and
  require human review for every trace issue.
- Candidate v0.2 semantics deprecate `scope_limitation_threshold`, make unknown
  formula verification reviewable by default, reject non-finite numeric input,
  and add nullable trace schema v2 coverage/count fields. No release is created
  by this candidate.

## 0.1.0 — release candidate

- Public-safe research-label and evidence/materiality logic for synthetic financial-artifact examples.
- Deterministic CLI demo covering Clean, Qualified, Adverse, Disclaimer and trace-review cases.
- Python 3.10–3.12 CI, Ruff, compile checks, unit tests and coverage evidence.
- Scope boundaries documented: this is not the official HCOMP implementation, a full empirical reproduction, statutory assurance, investment advice or a trading strategy.

The GitHub release date is intentionally omitted until a real `v0.1.0` release is created.

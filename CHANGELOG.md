# Changelog

## 0.2.0 - 2026-08-30

- Make label decisions invariant to uniform positive claim-weight scaling by
  using normalized aggregate weights and claim-level effective severity.
- Preserve `max_weighted_severity` as a deprecated diagnostic and add
  `max_effective_severity`.
- Clarify executed-action documentation coverage versus task completeness and
  require human review for every trace issue.
- v0.2 semantics deprecate `scope_limitation_threshold`, make unknown
  formula verification reviewable by default, reject non-finite numeric input,
  and add nullable trace schema v2 coverage/count fields.

## 0.1.0 - 2026-08-26

- Public-safe research-label and evidence/materiality logic for synthetic financial-artifact examples.
- Deterministic CLI demo covering Clean, Qualified, Adverse, Disclaimer and trace-review cases.
- Python 3.10–3.12 CI, Ruff, compile checks, unit tests and coverage evidence.
- Scope boundaries documented: this is not the official HCOMP implementation, a full empirical reproduction, statutory assurance, investment advice or a trading strategy.

The public `v0.1.0` release is the historical baseline for the v0.2.0 behavior
and schema changes described above.

# Migration guide: v0.1 to the v0.2 candidate

This branch prepares a future `v0.2.0` behavior change. The candidate package
metadata is set to `0.2.0` for clean-install testing, but it is not a release
until the behavior-change gate is approved.

## Added

- `AuditConfig.review_on_unknown_formula` (default `True`).
- `ArtifactCase.expected_executed_action_count`.
- `AuditResult.schema_version` and `TraceAssessment.schema_version` (`"2.0"`).
- `AuditResult.max_effective_severity` and `informational_matters` make
  claim-level materiality and explicit review opt-outs machine-readable.
- `AuditResult.critical_matters_total`, `critical_matters_truncated`, and
  `critical_matters_limit` make the bounded critical-matter projection
  explicit; material claims remain critical even when an informational opt-out
  is enabled.
- Nullable `TraceAssessment.executed_action_documentation_coverage`.
- Trace counts: `observed_action_records`, `terminal_action_records`, and
  `successful_executions`.

## Deprecated

- `AuditConfig.scope_limitation_threshold`: a warning is emitted when supplied;
  it remains accepted for compatibility but never changes the opinion.
- `TraceAssessment.trace_completeness`: nullable alias for the executed-action
  documentation coverage metric.
- `AuditResult.max_weighted_severity`: diagnostic only; it is not a materiality
  gate.

## Behavior changes

- Evidence decisions use `evidence_threshold` only.
- Unknown formula checks require human review by default without automatically
  changing the label.
- Explicit verification opt-outs affect only non-material matters. A material
  claim always remains in `critical_matters`, and the two matter collections
  are disjoint.
- Non-finite numeric inputs are rejected.
- With no executed actions, both coverage fields are `null`, not `1.0`.
- Expected trace records and expected successful executions are separate
  concepts. Proposed, failed, or skipped-only records are not task-complete.

Consumers should tolerate nullable coverage and inspect `schema_version` before
assuming v2 fields are present. Existing synthetic examples remain public-safe
and are not empirical HCOMP results.

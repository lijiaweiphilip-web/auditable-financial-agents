# Mathematical decision rules

This document describes executable rules in the public-safe prototype. It does
not claim a new theorem or full empirical reproduction of the HCOMP paper.

For a claim with generated value `v_hat`, source value `v`, and positive
threshold `tau`:

`numeric_severity = abs(v_hat - v) / tau`

`effective_severity = max(numeric_severity, qualitative_severity)`

A failed formula check raises effective severity to at least `1.0`.

For positive claim weights, normalize with `w'_i = w_i / sum_j w_j`:

`evidence_sufficiency = sum_i w'_i * evidence_valid_i`

`scope_limitation = 1 - evidence_sufficiency`

`pervasiveness = sum_i w'_i * 1[effective_severity_i >= 1]`

With sufficient evidence, the label decision is:

| Condition | Label |
|---|---|
| `max_effective_severity < 1` | `Clean` |
| `max_effective_severity >= 1` and `pervasiveness < threshold` | `Qualified` |
| sufficient evidence and otherwise material | `Adverse` |
| insufficient evidence | `Disclaimer` |

`max_weighted_severity` remains a deprecated diagnostic field. It is not the
materiality gate because multiplying all weights by a constant must not change
the opinion.

`evidence_threshold` is the sole evidence decision threshold. The historical
`scope_limitation_threshold` is accepted only as a deprecated compatibility
field and emits a warning without affecting the label.

Formula uncertainty remains distinct from formula failure: an unknown formula
does not automatically make a claim material, but it triggers human review by
default and is retained in the basis and critical matters. All numeric inputs
must be finite.

Trace schema version `2.0` reports the fraction of executed actions with both
evidence refs and a result hash as nullable
`executed_action_documentation_coverage`. The legacy `trace_completeness` is a
nullable alias. With no executed actions both are `null`; this metric is not task
completeness. `expected_action_count` counts trace records while
`expected_executed_action_count` counts expected successful executions. Failed,
skipped, or proposed-only traces cannot be task-complete, and every trace issue
sets `human_review_required=True`.

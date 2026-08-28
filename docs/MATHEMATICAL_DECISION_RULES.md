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

Trace completeness is the fraction of executed actions with both evidence refs
and a result hash. It is not task completeness. When an expected action count is
provided, missing actions are an explicit trace issue and require human review.

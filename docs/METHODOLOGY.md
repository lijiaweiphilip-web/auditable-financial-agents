# Methodology notes

## Claim severity

For a numeric claim with generated value `v_hat`, source-supported value `v`, and positive materiality threshold `tau`, the prototype uses:

`numeric_severity = abs(v_hat - v) / tau`

A claim is treated as materially affected when the effective severity is at least 1.0. The effective severity is the maximum of numeric severity and an optional qualitative-severity score. A failed formula check also raises the effective severity to at least 1.0.

## Evidence sufficiency

Let `w'_i = w_i / sum_j w_j` be normalized positive claim weights. Evidence
sufficiency is `sum_i w'_i * evidence_valid_i`, where validity requires
provenance, entity, period, and metric alignment.

Scope limitation is `1 - evidence_sufficiency`.

`evidence_threshold` is the only threshold used for the evidence branch of the
opinion rule. The former `scope_limitation_threshold` is an optional deprecated
compatibility field; supplying it emits a warning but does not change the
opinion. All numeric inputs are required to be finite.

## Pervasiveness

Pervasiveness is `sum_i w'_i * material_i`, where a claim is material when its
effective severity is at least 1.0. Materiality itself is a claim-level
property; it is not hidden by a small weight. The label rule uses the maximum
effective severity across claims, while `max_weighted_severity` is retained only
as a deprecated diagnostic for compatibility.

## Decision rule

With sufficient evidence, the prototype classifies a case as `Clean` only when
`max_effective_severity < 1`. A localized material issue is `Qualified`; a
pervasive material issue is `Adverse`. Insufficient evidence produces
`Disclaimer`. Uniform positive rescaling of all claim weights therefore leaves
the label and normalized aggregate quantities unchanged.

## Research-label rule

With configurable thresholds, the prototype follows the same qualitative structure as the paper:

- `Clean`: sufficient evidence and no material unresolved issue.
- `Qualified`: sufficient evidence, but a material issue is localized.
- `Adverse`: sufficient evidence, but material issues are pervasive.
- `Disclaimer`: insufficient evidence blocks a safe judgment.

This implementation is a public-safe teaching/research prototype and should not be treated as the full experimental implementation of the accepted paper.

## Formula uncertainty and trace schema

`formula_check="unknown"` preserves the claim's label calculation but, by
default, adds `human_review_required=True`, the claim to `critical_matters`, and
an `unresolved_formula_verification` basis entry. `AuditConfig` exposes an
explicit `review_on_unknown_formula=False` opt-out for informational use; the
original `formula_check_unknown` reason remains visible.

Trace assessments use schema version `2.0`. The nullable
`executed_action_documentation_coverage` is the fraction of executed actions
with both evidence references and a result hash. The deprecated
`trace_completeness` field is a nullable alias. With zero executed actions both
fields are `null`, never `1.0`. `expected_action_count` counts expected trace
records; `expected_executed_action_count` separately counts expected successful
executions. Proposed, failed, and skipped records therefore cannot be described
as a completed task. Any trace issue requires human review.

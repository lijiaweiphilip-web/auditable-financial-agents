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

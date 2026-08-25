# Methodology notes

## Claim severity

For a numeric claim with generated value `v_hat`, source-supported value `v`, and positive materiality threshold `tau`, the prototype uses:

`numeric_severity = abs(v_hat - v) / tau`

A claim is treated as materially affected when the effective severity is at least 1.0. The effective severity is the maximum of numeric severity and an optional qualitative-severity score. A failed formula check also raises the effective severity to at least 1.0.

## Evidence sufficiency

Evidence sufficiency is the claim-weighted fraction of claims whose provenance, entity, period, and metric alignment are all valid.

## Pervasiveness

Pervasiveness is the claim-weighted fraction of materially affected claims.

## Research-label rule

With configurable thresholds, the prototype follows the same qualitative structure as the paper:

- `Clean`: sufficient evidence and no material unresolved issue.
- `Qualified`: sufficient evidence, but a material issue is localized.
- `Adverse`: sufficient evidence, but material issues are pervasive.
- `Disclaimer`: insufficient evidence blocks a safe judgment.

This implementation is a public-safe teaching/research prototype and should not be treated as the full experimental implementation of the accepted paper.

# Semantic change report

## Release status

This report describes the published v0.2.0 behavior change.

## Behavior changes

- Label decisions use claim-level `max_effective_severity` instead of the
  absolute-scale-sensitive `max_weighted_severity`.
- Uniform positive weight scaling preserves normalized metrics and opinions.
- Formula failures and qualitative materiality cannot be hidden by low weights.
- Skipped exceptions and all other trace issues require human review.
- Empty traces are not called complete tasks; coverage is nullable and task
  completeness is `None` unless an expected record or execution count is
  supplied.
- `scope_limitation_threshold` is deprecated and no longer affects the opinion;
  `evidence_threshold` is the sole evidence branch threshold.
- Unknown formula checks trigger human review by default, with an explicit
  informational opt-out.
- Trace and result payloads carry schema version `2.0` and separate observed,
  terminal, and successful-execution counts.
- Claims reject partial numeric triplets, non-boolean alignment flags and
  non-finite values at the input boundary; this prevents malformed JSON from
  silently becoming a zero-severity claim.
- Unknown formula checks can be explicitly downgraded to an informational
  matter with `review_on_unknown_formula=False`; the raw unknown reason remains
  in the claim assessment.

## Compatibility

The old `max_weighted_severity` field remains in serialized results as a
deprecated diagnostic. New trace fields have defaults so existing callers can
continue to construct cases and consume the legacy coverage field.

The package metadata and public release are `0.2.0`.

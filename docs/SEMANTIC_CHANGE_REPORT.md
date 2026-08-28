# Semantic change report

## Candidate status

This is an unpublished v0.2.0 behavior-change candidate. No release has been
created.

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

## Compatibility

The old `max_weighted_severity` field remains in serialized results as a
deprecated diagnostic. New trace fields have defaults so existing callers can
continue to construct cases and consume the legacy coverage field.

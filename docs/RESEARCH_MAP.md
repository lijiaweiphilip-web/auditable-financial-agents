# Research map: paper concepts to public code

This map keeps the public code companion's scope explicit. The examples are
synthetic and exercise deterministic logic; they are not the archival paper's
empirical dataset.

| Paper concept | Public implementation | Synthetic evidence | Not reproduced here | Future extension |
|---|---|---|---|---|
| Four research labels | `core.evaluate_case` and `schema.VALID_OPINIONS` | `examples/clean_case.json`, `qualified_formula_error.json`, `adverse_multiple_errors.json`, `disclaimer_missing_evidence.json` | SEC-backed case sampling and expert study | Public case set after provenance review |
| Evidence sufficiency and provenance | `core.assess_claim`, `schema.Claim.evidence_valid` | Claim/entity/period/metric alignment cases | Full paper certificate/checker field grid | Richer evidence lineage adapters |
| Materiality and pervasiveness | `core.assess_claim`, `core.evaluate_case` | Numeric/qualitative severity and multiple-issue examples | Threshold-sensitivity grid and domain calibration | Domain-specific materiality profiles |
| Formula checks and critical matters | `core.assess_claim`, critical sorting in `core.evaluate_case` | `examples/qualified_formula_error.json` and priority fields | Expert toll / broad reviewer protocol | Selective escalation policy experiments |
| False-clean risk | `core.false_clean_rate` | Deterministic helper tests | 400-case diagnostic conclusions | Larger public-safe evaluation once licensed |
| Action trace | `trace.assess_trace`, `schema.ActionRecord`, `schema.TraceAssessment` (schema v2) | `examples/trace_gap_case.json` and `empty_trace_expected.json` | Upstream action logs from the accepted paper | Evidence-aware tool-call and human-escalation research |

The action-trace path is a **prospective extension**, not an HCOMP 2026
accepted-paper result. See [`TRACE_EXTENSION.md`](TRACE_EXTENSION.md) and
[`NON_CLAIMS.md`](NON_CLAIMS.md) for boundaries.

The v0.2 candidate treats `scope_limitation_threshold` as a deprecated
compatibility input, keeps `evidence_threshold` as the sole evidence decision
threshold, and defaults unknown formula checks to human review. These are
prototype behavior semantics, not claims about the accepted paper's complete
implementation.

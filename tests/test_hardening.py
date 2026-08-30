from __future__ import annotations

import json
import math
import tempfile
import unittest
import warnings
from pathlib import Path

from auditable_financial_agents import ActionRecord, ArtifactCase, AuditConfig, Claim, evaluate_case
from auditable_financial_agents.cli import load_case, main
from auditable_financial_agents.trace import assess_trace
from scripts.build_demo_snapshot import main as build_demo_snapshot


class HardeningTests(unittest.TestCase):
    def test_empty_case_and_case_id_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("", [Claim("x")]))
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("empty", []))

    def test_claim_validation_rejects_unsafe_threshold_fields(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("threshold", [Claim("x", materiality_threshold=0)]))
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("formula", [Claim("x", formula_check="maybe")]))
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("severity", [Claim("x", qualitative_severity=-1)]))

    def test_unknown_formula_is_retained_as_uncertainty(self) -> None:
        result = evaluate_case(ArtifactCase("unknown", [Claim("x", formula_check="unknown")]))
        self.assertEqual(result.opinion, "Clean")
        self.assertTrue(result.human_review_required)
        self.assertIn("formula_check_unknown", result.claim_assessments[0].reasons)
        self.assertIn("unresolved_formula_verification", result.basis)

    def test_unknown_formula_can_be_informational_by_explicit_opt_out(self) -> None:
        result = evaluate_case(
            ArtifactCase("unknown-opt-out", [Claim("x", formula_check="unknown")]),
            AuditConfig(review_on_unknown_formula=False),
        )
        self.assertEqual(result.opinion, "Clean")
        self.assertFalse(result.human_review_required)
        self.assertIn("formula_verification_informational", result.basis)

    def test_unknown_formula_enters_critical_matters_by_default(self) -> None:
        result = evaluate_case(ArtifactCase("unknown-critical", [Claim("x", formula_check="unknown")]))
        self.assertEqual(result.critical_matters, ["x"])

    def test_scope_threshold_is_deprecated_and_does_not_change_opinion(self) -> None:
        case = ArtifactCase("scope-compat", [Claim("x", provenance_valid=False)])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            legacy = evaluate_case(case, AuditConfig(scope_limitation_threshold=0.99))
        current = evaluate_case(case)
        self.assertEqual(legacy.opinion, current.opinion)
        self.assertTrue(any(item.category is DeprecationWarning for item in caught))

    def test_nonfinite_claim_values_are_rejected(self) -> None:
        fields = ("weight", "generated_value", "source_value", "materiality_threshold", "qualitative_severity")
        for field_name in fields:
            value = math.inf if field_name != "source_value" else math.nan
            kwargs = {field_name: value}
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("nonfinite-claim", [Claim("x", **kwargs)]))

    def test_nonfinite_config_values_are_rejected(self) -> None:
        for field_name in ("evidence_threshold", "pervasiveness_threshold", "severe_issue_threshold"):
            kwargs = {field_name: math.nan}
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("nonfinite-config", [Claim("x")]), AuditConfig(**kwargs))

    def test_expected_executed_action_count_is_preserved_from_dict(self) -> None:
        case = ArtifactCase.from_dict(
            {"case_id": "expected-executed", "claims": [{"claim_id": "x"}], "expected_executed_action_count": 2}
        )
        self.assertEqual(case.expected_executed_action_count, 2)

    def test_severe_issue_requires_human_review_even_when_localized(self) -> None:
        case = ArtifactCase(
            "severe",
            [
                Claim("ok", weight=5),
                Claim("severe", weight=0.1, qualitative_severity=2.0),
            ],
        )
        result = evaluate_case(case, AuditConfig(pervasiveness_threshold=0.9))
        self.assertEqual(result.opinion, "Qualified")
        self.assertTrue(result.human_review_required)

    def test_skipped_exception_is_a_trace_issue(self) -> None:
        result = assess_trace([ActionRecord("skip", "tool", "skipped", exception="cancelled")])
        self.assertIsNone(result.trace_completeness)
        self.assertIsNone(result.executed_action_documentation_coverage)
        self.assertEqual(result.issues, ("skip:skipped_with_exception",))

    def test_from_dict_preserves_action_evidence_refs(self) -> None:
        case = ArtifactCase.from_dict(
            {
                "case_id": "dict",
                "claims": [{"claim_id": "c"}],
                "actions": [
                    {
                        "action_id": "a",
                        "tool": "calculator",
                        "status": "executed",
                        "evidence_refs": ["claim:c"],
                        "result_digest": {
                            "algorithm": "sha256",
                            "value": "0" * 64,
                        },
                    }
                ],
            }
        )
        result = evaluate_case(case)
        self.assertEqual(result.trace_assessment.trace_completeness, 1.0)
        self.assertEqual(result.trace_assessment.observed_action_records, 1)
        self.assertEqual(result.trace_assessment.successful_executions, 1)

    def test_trace_assessment_has_v2_schema_version(self) -> None:
        result = evaluate_case(ArtifactCase("schema", [Claim("x")]))
        self.assertEqual(result.schema_version, "2.0")
        self.assertEqual(result.trace_assessment.schema_version, "2.0")

    def test_cli_demo_subcommand_returns_zero(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(main(["demo", "--examples", str(root / "examples")]), 0)

    def test_cli_demo_artifacts_use_platform_independent_lf(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(build_demo_snapshot(), 0)
        for name in ("demo_results.json", "DEMO_RESULTS.md", "DEMO_MANIFEST.json"):
            self.assertNotIn(b"\r\n", (root / "results" / name).read_bytes())

    def test_invalid_json_is_not_silently_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_case(path)

    def test_false_clean_rate_zero_when_expected_is_all_clean(self) -> None:
        from auditable_financial_agents import false_clean_rate

        self.assertEqual(false_clean_rate(["Clean"], ["Clean"]), (0, 0, 0.0))


if __name__ == "__main__":
    unittest.main()

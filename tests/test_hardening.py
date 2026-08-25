from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from auditable_financial_agents import ActionRecord, ArtifactCase, AuditConfig, Claim, evaluate_case
from auditable_financial_agents.cli import load_case, main
from auditable_financial_agents.trace import assess_trace


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
        self.assertFalse(result.human_review_required)
        self.assertIn("formula_check_unknown", result.claim_assessments[0].reasons)

    def test_severe_issue_requires_human_review_even_when_localized(self) -> None:
        case = ArtifactCase(
            "severe",
            [
                Claim("ok", weight=5),
                Claim("severe", weight=0.1, qualitative_severity=2.0),
            ],
        )
        result = evaluate_case(case, AuditConfig(pervasiveness_threshold=0.9))
        self.assertEqual(result.opinion, "Clean")
        self.assertTrue(result.human_review_required)

    def test_skipped_exception_is_a_trace_issue(self) -> None:
        result = assess_trace([ActionRecord("skip", "tool", "skipped", exception="cancelled")])
        self.assertEqual(result.trace_completeness, 1.0)
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
                        "result_hash": "abc",
                    }
                ],
            }
        )
        result = evaluate_case(case)
        self.assertEqual(result.trace_assessment.trace_completeness, 1.0)

    def test_cli_demo_subcommand_returns_zero(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(main(["demo", "--examples", str(root / "examples")]), 0)

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

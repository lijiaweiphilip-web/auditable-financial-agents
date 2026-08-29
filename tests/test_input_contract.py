from __future__ import annotations

import json
import math
import unittest

from auditable_financial_agents import ActionRecord, ArtifactCase, AuditConfig, Claim, evaluate_case


class StrictInputContractTests(unittest.TestCase):
    def test_boolean_strings_are_rejected_from_json(self) -> None:
        payload = {"case_id": "bool", "claims": [{"claim_id": "x", "provenance_valid": "false"}]}
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(payload)

    def test_boolean_numbers_are_rejected_from_json(self) -> None:
        payload = {"case_id": "bool", "claims": [{"claim_id": "x", "metric_aligned": 0}]}
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(payload)

    def test_boolean_null_is_rejected_from_json(self) -> None:
        payload = {"case_id": "bool", "claims": [{"claim_id": "x", "period_aligned": None}]}
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(payload)

    def test_unknown_formula_policy_boolean_is_strict(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase("config", [Claim("x")]),
                AuditConfig(review_on_unknown_formula="false"),  # type: ignore[arg-type]
            )

    def test_numeric_boolean_fields_are_rejected(self) -> None:
        numeric_fields = (
            "weight",
            "generated_value",
            "source_value",
            "materiality_threshold",
            "qualitative_severity",
        )
        for field_name in numeric_fields:
            kwargs = {field_name: True}
            with self.subTest(field_name=field_name), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("numeric-bool", [Claim("x", **kwargs)]))

    def test_partial_numeric_group_is_rejected(self) -> None:
        combinations = (
            {"generated_value": 1.0},
            {"source_value": 1.0},
            {"materiality_threshold": 1.0},
            {"generated_value": 1.0, "source_value": 1.0},
        )
        for kwargs in combinations:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("partial", [Claim("x", **kwargs)]))

    def test_complete_numeric_group_is_accepted(self) -> None:
        result = evaluate_case(
            ArtifactCase("complete", [Claim("x", generated_value=1.0, source_value=1.0, materiality_threshold=1.0)])
        )
        self.assertEqual(result.opinion, "Clean")

    def test_action_id_and_tool_must_be_nonempty_strings(self) -> None:
        for action_id, tool in (("", "tool"), ("a", ""), (1, "tool"), ("a", 2)):
            with self.subTest(action_id=action_id, tool=tool), self.assertRaises(ValueError):
                evaluate_case(
                    ArtifactCase("action", [Claim("x")], [ActionRecord(action_id, tool, "proposed")])  # type: ignore[arg-type]
                )

    def test_evidence_refs_cannot_be_a_single_string(self) -> None:
        payload = {
            "case_id": "refs",
            "claims": [{"claim_id": "x"}],
            "actions": [
                {
                    "action_id": "a",
                    "tool": "t",
                    "status": "executed",
                    "evidence_refs": "e",
                    "result_hash": "h",
                }
            ],
        }
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(payload)

    def test_evidence_refs_must_not_contain_empty_or_duplicate_values(self) -> None:
        for refs in ([], [""], ["e", "e"]):
            action = ActionRecord("a", "t", "executed", evidence_refs=tuple(refs), result_hash="h")
            if refs == []:
                result = evaluate_case(ArtifactCase("refs", [Claim("x")], [action]))
                self.assertTrue(result.human_review_required)
            else:
                with self.subTest(refs=refs), self.assertRaises(ValueError):
                    evaluate_case(ArtifactCase("refs", [Claim("x")], [action]))

    def test_proposed_action_cannot_have_result_hash(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase("proposed", [Claim("x")], [ActionRecord("a", "t", "proposed", result_hash="h")])
            )

    def test_skipped_without_reason_is_review_issue(self) -> None:
        result = evaluate_case(
            ArtifactCase("skipped", [Claim("x")], [ActionRecord("a", "t", "skipped")])
        )
        self.assertTrue(result.human_review_required)
        self.assertIn("a:skipped_without_reason", result.trace_assessment.issues)

    def test_failed_without_detail_remains_a_reviewable_trace(self) -> None:
        result = evaluate_case(
            ArtifactCase("failed", [Claim("x")], [ActionRecord("a", "t", "failed")])
        )
        self.assertTrue(result.human_review_required)
        self.assertEqual(result.trace_assessment.failed_actions, 1)

    def test_unknown_formula_opt_out_is_informational(self) -> None:
        result = evaluate_case(
            ArtifactCase("unknown", [Claim("x", formula_check="unknown")]),
            AuditConfig(review_on_unknown_formula=False),
        )
        self.assertFalse(result.human_review_required)
        self.assertEqual(result.critical_matters, [])
        self.assertEqual(result.informational_matters, ["x"])

    def test_numeric_difference_overflow_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase(
                    "overflow",
                    [Claim("x", generated_value=1e308, source_value=-1e308, materiality_threshold=1.0)],
                )
            )

    def test_weighted_diagnostic_overflow_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("overflow", [Claim("x", weight=1e308, qualitative_severity=2.0)]))

    def test_all_audit_outputs_are_finite(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "finite",
                [
                    Claim("a", weight=1e-300, generated_value=1.0, source_value=1.0, materiality_threshold=1.0),
                    Claim("b", weight=1e300, qualitative_severity=0.2),
                ],
            )
        )
        for value in (
            result.evidence_sufficiency,
            result.scope_limitation,
            result.max_weighted_severity,
            result.max_effective_severity,
            result.pervasiveness,
        ):
            self.assertTrue(math.isfinite(value))

    def test_expected_executed_count_cannot_exceed_record_count(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase("counts", [Claim("x")], expected_action_count=1, expected_executed_action_count=2)
            )

    def test_expected_executed_count_requires_successful_execution(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "counts",
                [Claim("x")],
                [ActionRecord("a", "t", "executed", exception="timeout")],
                expected_executed_action_count=1,
            )
        )
        self.assertFalse(result.trace_assessment.task_completeness)
        self.assertEqual(result.trace_assessment.successful_executions, 0)

    def test_result_round_trip_is_json_serializable(self) -> None:
        result = evaluate_case(ArtifactCase("round-trip", [Claim("x")]))
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        self.assertEqual(json.loads(encoded)["schema_version"], "2.0")

    def test_schema_version_is_present_on_trace_and_result(self) -> None:
        result = evaluate_case(ArtifactCase("schema", [Claim("x")]))
        self.assertEqual(result.schema_version, "2.0")
        self.assertEqual(result.trace_assessment.schema_version, "2.0")


if __name__ == "__main__":
    unittest.main()

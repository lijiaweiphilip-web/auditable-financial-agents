from __future__ import annotations

import unittest

from auditable_financial_agents import ActionRecord, ArtifactCase, Claim, evaluate_case
from auditable_financial_agents.trace import assess_trace


class TraceTests(unittest.TestCase):
    def test_empty_trace_has_no_task_completeness_claim(self) -> None:
        result = assess_trace([])
        self.assertEqual(result.trace_completeness, 1.0)
        self.assertIsNone(result.task_completeness)
        self.assertEqual(result.completeness_basis, "no_expected_actions")

    def test_empty_trace_with_expected_actions_requires_review(self) -> None:
        case = ArtifactCase(
            "trace-expected",
            [Claim("x")],
            actions=[],
            expected_action_count=1,
        )
        result = evaluate_case(case)
        self.assertFalse(result.trace_assessment.task_completeness)
        self.assertIn("empty_trace_when_actions_expected", result.trace_assessment.issues)
        self.assertTrue(result.human_review_required)

    def test_documented_execution(self) -> None:
        action = ActionRecord(
            "a", "tool", "executed", evidence_refs=("fact:1",), result_hash="abc"
        )
        result = assess_trace([action])
        self.assertEqual(result.undocumented_executions, 0)
        self.assertEqual(result.trace_completeness, 1.0)

    def test_undocumented_execution_requires_review(self) -> None:
        case = ArtifactCase(
            "trace",
            [Claim("x", generated_value=1, source_value=1, materiality_threshold=0.1)],
            [ActionRecord("a", "tool", "executed")],
        )
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Clean")
        self.assertTrue(result.human_review_required)
        self.assertEqual(result.trace_assessment.undocumented_executions, 1)

    def test_failed_action_requires_review(self) -> None:
        case = ArtifactCase(
            "trace_fail",
            [Claim("x")],
            [ActionRecord("a", "tool", "failed", exception="timeout")],
        )
        result = evaluate_case(case)
        self.assertTrue(result.human_review_required)
        self.assertEqual(result.trace_assessment.failed_actions, 1)

    def test_skipped_exception_requires_review(self) -> None:
        case = ArtifactCase(
            "trace_skip",
            [Claim("x")],
            [ActionRecord("a", "tool", "skipped", exception="cancelled")],
        )
        result = evaluate_case(case)
        self.assertTrue(result.human_review_required)

    def test_invalid_action_status_rejected(self) -> None:
        case = ArtifactCase(
            "invalid",
            [Claim("x")],
            [ActionRecord("a", "tool", "mystery")],
        )
        with self.assertRaises(ValueError):
            evaluate_case(case)

    def test_duplicate_action_id_rejected(self) -> None:
        case = ArtifactCase(
            "dup_action",
            [Claim("x")],
            [ActionRecord("a", "tool", "proposed"), ActionRecord("a", "tool", "skipped")],
        )
        with self.assertRaises(ValueError):
            evaluate_case(case)


if __name__ == "__main__":
    unittest.main()

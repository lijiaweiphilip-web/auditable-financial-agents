from __future__ import annotations

import unittest

from auditable_financial_agents import ActionRecord, ArtifactCase, Claim, ResultDigest, evaluate_case
from auditable_financial_agents.trace import assess_trace

DIGEST = ResultDigest("sha256", "0" * 64)


class TraceTests(unittest.TestCase):
    def test_empty_trace_has_no_task_completeness_claim(self) -> None:
        result = assess_trace([])
        self.assertIsNone(result.trace_completeness)
        self.assertIsNone(result.executed_action_documentation_coverage)
        self.assertIsNone(result.task_completeness)
        self.assertEqual(result.completeness_basis, "no_expected_actions")
        self.assertEqual(result.observed_action_records, 0)
        self.assertEqual(result.terminal_action_records, 0)

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
            "a", "tool", "executed", evidence_refs=("fact:1",), result_digest=DIGEST
        )
        result = assess_trace([action])
        self.assertEqual(result.undocumented_executions, 0)
        self.assertEqual(result.trace_completeness, 1.0)
        self.assertEqual(result.executed_action_documentation_coverage, 1.0)
        self.assertEqual(result.terminal_action_records, 1)
        self.assertEqual(result.successful_executions, 1)

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

    def test_failed_only_trace_is_not_task_complete_when_expected(self) -> None:
        result = assess_trace(
            [ActionRecord("a", "tool", "failed", exception="timeout")],
            expected_action_count=1,
            expected_executed_action_count=1,
        )
        self.assertFalse(result.task_completeness)
        self.assertIsNone(result.trace_completeness)
        self.assertEqual(result.terminal_action_records, 1)

    def test_proposed_only_trace_is_not_task_complete(self) -> None:
        result = assess_trace(
            [ActionRecord("a", "tool", "proposed")],
            expected_action_count=1,
        )
        self.assertFalse(result.task_completeness)
        self.assertEqual(result.issues, ())

    def test_skipped_only_trace_is_not_task_complete(self) -> None:
        result = assess_trace(
            [ActionRecord("a", "tool", "skipped")],
            expected_action_count=1,
        )
        self.assertFalse(result.task_completeness)
        self.assertIsNone(result.trace_completeness)

    def test_mixed_trace_counts_and_coverage(self) -> None:
        result = assess_trace(
            [
                ActionRecord("ok", "tool", "executed", evidence_refs=("e",), result_digest=DIGEST),
                ActionRecord("bad", "tool", "failed", exception="timeout"),
                ActionRecord("plan", "tool", "proposed"),
            ],
            expected_action_count=3,
            expected_executed_action_count=2,
        )
        self.assertEqual(result.observed_action_records, 3)
        self.assertEqual(result.terminal_action_records, 2)
        self.assertEqual(result.successful_executions, 1)
        self.assertEqual(result.executed_action_documentation_coverage, 1.0)
        self.assertFalse(result.task_completeness)
        self.assertIn("bad:failed_action", ",".join(result.issues))

    def test_expected_executed_count_can_mark_all_executed_records_complete(self) -> None:
        action = ActionRecord("a", "tool", "executed", evidence_refs=("e",), result_digest=DIGEST)
        result = assess_trace([action], expected_executed_action_count=1)
        self.assertTrue(result.task_completeness)
        self.assertEqual(result.completeness_basis, "expected_executed_actions")

    def test_expected_zero_records_empty_trace_is_complete_without_coverage_claim(self) -> None:
        result = assess_trace([], expected_action_count=0, expected_executed_action_count=0)
        self.assertTrue(result.task_completeness)
        self.assertIsNone(result.trace_completeness)
        self.assertEqual(result.completeness_basis, "expected_action_records_and_executions")

    def test_expected_action_count_rejects_non_integer(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("bad-count", [Claim("x")], expected_action_count=1.5))

    def test_invalid_action_status_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ActionRecord("a", "tool", "mystery")

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

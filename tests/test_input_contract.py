from __future__ import annotations

import json
import math
import unittest
import warnings

from auditable_financial_agents import ActionRecord, ArtifactCase, AuditConfig, Claim, ResultDigest, evaluate_case
from auditable_financial_agents.schema import InputValidationError

DIGEST = ResultDigest("sha256", "0" * 64)


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
                    "result_digest": {
                        "algorithm": "sha256",
                        "value": "0" * 64,
                    },
                }
            ],
        }
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(payload)

    def test_evidence_refs_must_not_contain_empty_or_duplicate_values(self) -> None:
        for refs in ([], [""], ["e", "e"]):
            if refs == []:
                action = ActionRecord("a", "t", "executed", evidence_refs=tuple(refs), result_digest=DIGEST)
                result = evaluate_case(ArtifactCase("refs", [Claim("x")], [action]))
                self.assertTrue(result.human_review_required)
            else:
                with self.subTest(refs=refs), self.assertRaises(ValueError):
                    ActionRecord("a", "t", "executed", evidence_refs=tuple(refs), result_digest=DIGEST)

    def test_proposed_action_cannot_have_result_hash(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase("proposed", [Claim("x")], [ActionRecord("a", "t", "proposed", result_digest=DIGEST)])
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

    def test_unknown_case_key_is_path_aware(self) -> None:
        with self.assertRaises(InputValidationError) as context:
            ArtifactCase.from_dict({"case_id": "x", "claims": [{"claim_id": "c"}], "surprise": 1})
        self.assertIn("case.surprise", str(context.exception))

    def test_unknown_claim_key_is_rejected(self) -> None:
        with self.assertRaises(InputValidationError):
            ArtifactCase.from_dict({"case_id": "x", "claims": [{"claim_id": "c", "extra": 1}]})

    def test_unknown_action_key_is_rejected(self) -> None:
        with self.assertRaises(InputValidationError):
            ArtifactCase.from_dict(
                {
                    "case_id": "x",
                    "claims": [{"claim_id": "c"}],
                    "actions": [{"action_id": "a", "tool": "t", "status": "proposed", "extra": 1}],
                }
            )

    def test_typed_digest_is_required_for_new_action_output(self) -> None:
        with self.assertRaises(ValueError):
            ActionRecord("a", "t", "executed", evidence_refs=("e",), result_hash="abc")

    def test_legacy_digest_alias_warns_and_requires_sha256(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            action = ActionRecord("a", "t", "executed", evidence_refs=("e",), result_hash="sha256:" + "0" * 64)
            evaluate_case(ArtifactCase("legacy", [Claim("c")], [action]))
        self.assertTrue(any(item.category is DeprecationWarning for item in caught))
        with self.assertRaises(ValueError):
            ActionRecord("b", "t", "executed", result_hash="sha256:" + "A" * 64)

    def test_digest_and_legacy_alias_are_mutually_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            ArtifactCase.from_dict(
                {
                    "case_id": "x",
                    "claims": [{"claim_id": "c"}],
                    "actions": [
                        {
                            "action_id": "a",
                            "tool": "t",
                            "status": "executed",
                            "result_digest": {"algorithm": "sha256", "value": "0" * 64},
                            "result_hash": "sha256:" + "0" * 64,
                        }
                    ],
                }
            )

    def test_false_clean_rate_rejects_unknown_labels(self) -> None:
        from auditable_financial_agents import false_clean_rate

        with self.assertRaises(ValueError):
            false_clean_rate(["Clean"], ["Unknown"])

    def test_invalid_evidence_defaults_to_review_even_if_low_weight(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "invalid-evidence",
                [
                    Claim("x", weight=0.01, provenance_valid=False),
                    Claim("ok", weight=99.0),
                ],
            )
        )
        self.assertTrue(result.human_review_required)
        self.assertIn("x", result.critical_matters)

    def test_invalid_evidence_opt_out_is_informational_when_nonmaterial(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "invalid-evidence",
                [Claim("x", weight=1.0, provenance_valid=False), Claim("ok", weight=99.0)],
            ),
            AuditConfig(review_on_invalid_evidence=False),
        )
        self.assertFalse(result.human_review_required)
        self.assertIn("x", result.informational_matters)

    def test_clean_with_review_has_coherent_basis(self) -> None:
        result = evaluate_case(ArtifactCase("review-clean", [Claim("x", formula_check="unknown")]))
        self.assertTrue(result.human_review_required)
        self.assertIn("clean opinion with unresolved human-review matters", result.basis)

    def test_material_unknown_formula_stays_critical_after_opt_out(self) -> None:
        result = evaluate_case(
            ArtifactCase("material-unknown", [Claim("x", formula_check="unknown", qualitative_severity=1.1)]),
            AuditConfig(review_on_unknown_formula=False),
        )
        self.assertEqual(result.opinion, "Adverse")
        self.assertIn("x", result.critical_matters)
        self.assertNotIn("x", result.informational_matters)
        self.assertTrue(result.human_review_required)

    def test_material_invalid_evidence_stays_critical_after_opt_out(self) -> None:
        result = evaluate_case(
            ArtifactCase("material-invalid", [Claim("x", provenance_valid=False, qualitative_severity=1.1)]),
            AuditConfig(review_on_invalid_evidence=False),
        )
        self.assertIn("x", result.critical_matters)
        self.assertNotIn("x", result.informational_matters)
        self.assertTrue(result.human_review_required)

    def test_critical_and_informational_matters_are_disjoint(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "mixed-matters",
                [
                    Claim("unknown", formula_check="unknown"),
                    Claim("material", formula_check="unknown", qualitative_severity=1.1),
                    Claim("invalid", provenance_valid=False),
                ],
            ),
            AuditConfig(review_on_unknown_formula=False, review_on_invalid_evidence=False),
        )
        self.assertTrue(set(result.critical_matters).isdisjoint(result.informational_matters))

    def test_critical_truncation_is_explicit(self) -> None:
        result = evaluate_case(
            ArtifactCase("many-critical", [Claim(str(index), formula_check="unknown") for index in range(6)]),
            AuditConfig(max_critical_matters=3),
        )
        self.assertEqual(result.critical_matters_total, 6)
        self.assertEqual(result.critical_matters_limit, 3)
        self.assertTrue(result.critical_matters_truncated)
        self.assertEqual(len(result.critical_matters), 3)

    def test_critical_limit_must_be_positive_integer(self) -> None:
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("limit", [Claim("x")]), AuditConfig(max_critical_matters=value))  # type: ignore[arg-type]

    def test_nested_input_errors_include_item_index(self) -> None:
        with self.assertRaises(InputValidationError) as context:
            ArtifactCase.from_dict(
                {
                    "case_id": "nested",
                    "claims": [{"claim_id": "x"}, {"claim_id": "y", "unexpected": True}],
                }
            )
        self.assertIn("case.claims[1].unexpected", str(context.exception))

        with self.assertRaises(InputValidationError) as context:
            ArtifactCase.from_dict(
                {
                    "case_id": "nested",
                    "claims": [{"claim_id": "x"}],
                    "actions": [
                        {
                            "action_id": "a",
                            "tool": "t",
                            "status": "executed",
                            "result_digest": {"algorithm": "sha256", "value": "bad"},
                        }
                    ],
                }
            )
        self.assertIn("case.actions[0].result_digest.value", str(context.exception))

    def test_weight_scaling_preserves_aggregate_opinion_and_metrics(self) -> None:
        claims = [Claim("a", weight=1.0), Claim("b", weight=2.0, qualitative_severity=0.8)]
        scaled = [Claim("a", weight=10.0), Claim("b", weight=20.0, qualitative_severity=0.8)]
        first, second = evaluate_case(ArtifactCase("base", claims)), evaluate_case(ArtifactCase("scaled", scaled))
        self.assertEqual(first.opinion, second.opinion)
        self.assertAlmostEqual(first.evidence_sufficiency, second.evidence_sufficiency)
        self.assertAlmostEqual(first.pervasiveness, second.pervasiveness)
        self.assertAlmostEqual(first.scope_limitation, second.scope_limitation)


if __name__ == "__main__":
    unittest.main()

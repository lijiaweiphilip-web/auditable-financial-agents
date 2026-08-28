from __future__ import annotations

import unittest

from auditable_financial_agents import ArtifactCase, AuditConfig, Claim, evaluate_case, false_clean_rate


class AuditCoreTests(unittest.TestCase):
    def test_clean_case(self) -> None:
        case = ArtifactCase("c", [Claim("x", generated_value=10, source_value=10, materiality_threshold=2)])
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Clean")
        self.assertFalse(result.human_review_required)

    def test_qualified_localized_material_issue(self) -> None:
        case = ArtifactCase(
            "q",
            [
                Claim("ok", weight=1.0, generated_value=10, source_value=10, materiality_threshold=2),
                Claim("bad", weight=0.3, generated_value=20, source_value=10, materiality_threshold=2),
            ],
        )
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Qualified")
        self.assertTrue(result.human_review_required)

    def test_adverse_pervasive_issues(self) -> None:
        case = ArtifactCase(
            "a",
            [
                Claim("bad1", generated_value=20, source_value=10, materiality_threshold=2),
                Claim("bad2", generated_value=20, source_value=10, materiality_threshold=2),
            ],
        )
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Adverse")

    def test_disclaimer_low_evidence(self) -> None:
        case = ArtifactCase("d", [Claim("x", provenance_valid=False)])
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Disclaimer")
        self.assertEqual(result.evidence_sufficiency, 0.0)

    def test_formula_fail_can_make_claim_material(self) -> None:
        case = ArtifactCase(
            "f",
            [
                Claim("ok", weight=1.0),
                Claim("formula", weight=0.2, formula_check="fail"),
            ],
        )
        result = evaluate_case(case)
        assessment = next(x for x in result.claim_assessments if x.claim_id == "formula")
        self.assertTrue(assessment.material)
        self.assertIn("formula_check_failed", assessment.reasons)

    def test_qualitative_override(self) -> None:
        case = ArtifactCase(
            "qual",
            [
                Claim("ok", weight=2.0),
                Claim("cause", weight=1.0, qualitative_severity=1.2),
            ],
        )
        result = evaluate_case(case)
        self.assertEqual(result.opinion, "Qualified")

    def test_increasing_claim_severity_cannot_make_opinion_safer(self) -> None:
        claims = [Claim("ok", weight=3.0), Claim("risk", weight=1.0, qualitative_severity=0.8)]
        lower = evaluate_case(ArtifactCase("severity-low", claims))
        higher = evaluate_case(
            ArtifactCase(
                "severity-high",
                [Claim("ok", weight=3.0), Claim("risk", weight=1.0, qualitative_severity=1.2)],
            )
        )
        self.assertEqual(lower.opinion, "Clean")
        self.assertEqual(higher.opinion, "Qualified")
        self.assertGreaterEqual(higher.max_effective_severity, lower.max_effective_severity)

    def test_invalidating_evidence_cannot_improve_to_clean(self) -> None:
        valid = evaluate_case(
            ArtifactCase("valid-material", [Claim("risk", qualitative_severity=1.2)])
        )
        invalid = evaluate_case(
            ArtifactCase("invalid-material", [Claim("risk", qualitative_severity=1.2, provenance_valid=False)])
        )
        self.assertNotEqual(valid.opinion, "Clean")
        self.assertNotEqual(invalid.opinion, "Clean")
        self.assertLess(invalid.evidence_sufficiency, valid.evidence_sufficiency)

    def test_materiality_threshold_boundary_is_deterministic(self) -> None:
        boundary = ArtifactCase(
            "boundary",
            [Claim("bad", generated_value=2.0, source_value=1.0, materiality_threshold=1.0)],
        )
        first = evaluate_case(boundary)
        second = evaluate_case(boundary)
        self.assertEqual(first.opinion, second.opinion)
        self.assertEqual(first.pervasiveness, second.pervasiveness)
        self.assertEqual(first.critical_matters, second.critical_matters)

    def test_uniform_weight_scaling_preserves_decision_metrics(self) -> None:
        claims = [
            Claim("ok", weight=2.0),
            Claim("bad", weight=1.0, qualitative_severity=1.2),
        ]
        original = evaluate_case(ArtifactCase("scale-a", claims))
        scaled = evaluate_case(
            ArtifactCase(
                "scale-b",
                [
                    Claim("ok", weight=20.0),
                    Claim("bad", weight=10.0, qualitative_severity=1.2),
                ],
            )
        )
        self.assertEqual(scaled.opinion, original.opinion)
        self.assertEqual(scaled.evidence_sufficiency, original.evidence_sufficiency)
        self.assertEqual(scaled.pervasiveness, original.pervasiveness)
        self.assertEqual(scaled.scope_limitation, original.scope_limitation)

    def test_low_weight_formula_failure_cannot_be_clean(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "formula-material",
                [Claim("ok", weight=100.0), Claim("bad", weight=0.01, formula_check="fail")],
            )
        )
        self.assertNotEqual(result.opinion, "Clean")
        self.assertGreaterEqual(result.max_effective_severity, 1.0)

    def test_max_effective_severity_is_claim_level_not_weighted(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "severity-metric",
                [Claim("bad", weight=0.01, qualitative_severity=2.0)],
            )
        )
        self.assertEqual(result.max_effective_severity, 2.0)
        self.assertAlmostEqual(result.max_weighted_severity, 0.02)

    def test_custom_thresholds(self) -> None:
        case = ArtifactCase(
            "custom",
            [
                Claim("ok", weight=2.0),
                Claim("bad", weight=1.0, generated_value=11.1, source_value=10, materiality_threshold=1),
            ],
        )
        result = evaluate_case(case, AuditConfig(pervasiveness_threshold=0.4))
        self.assertEqual(result.opinion, "Qualified")

    def test_thresholds_outside_unit_interval_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("bad-evidence-threshold", [Claim("x")]), AuditConfig(evidence_threshold=1.1))
        with self.assertRaises(ValueError):
            evaluate_case(
                ArtifactCase("bad-pervasive-threshold", [Claim("x")]),
                AuditConfig(pervasiveness_threshold=-0.1),
            )

    def test_false_clean_rate(self) -> None:
        numerator, denominator, rate = false_clean_rate(
            ["Clean", "Qualified", "Clean"], ["Qualified", "Qualified", "Clean"]
        )
        self.assertEqual((numerator, denominator), (1, 2))
        self.assertAlmostEqual(rate, 0.5)

    def test_false_clean_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            false_clean_rate(["Clean"], ["Clean", "Qualified"])

    def test_duplicate_claim_ids_rejected(self) -> None:
        case = ArtifactCase("dup", [Claim("x"), Claim("x")])
        with self.assertRaises(ValueError):
            evaluate_case(case)

    def test_nonpositive_weight_rejected(self) -> None:
        case = ArtifactCase("w", [Claim("x", weight=0)])
        with self.assertRaises(ValueError):
            evaluate_case(case)


if __name__ == "__main__":
    unittest.main()

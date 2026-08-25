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

    def test_custom_thresholds(self) -> None:
        case = ArtifactCase(
            "custom",
            [Claim("bad", generated_value=11.1, source_value=10, materiality_threshold=1)],
        )
        result = evaluate_case(case, AuditConfig(pervasiveness_threshold=1.1))
        self.assertEqual(result.opinion, "Qualified")

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

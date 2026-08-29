from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from auditable_financial_agents import (
    ActionRecord,
    ArtifactCase,
    AuditConfig,
    Claim,
    InputValidationError,
    ResultDigest,
    evaluate_case,
)
from auditable_financial_agents.cli import main, validate_case_path
from auditable_financial_agents.schema import validate_action, validate_case

DIGEST = ResultDigest("sha256", "0" * 64)
ROOT = Path(__file__).resolve().parents[1]


class ContractEdgeTests(unittest.TestCase):
    def test_result_digest_rejects_malformed_payloads(self) -> None:
        payloads = (
            None,
            [],
            {"algorithm": "md5", "value": "0" * 64},
            {"algorithm": "sha256", "value": 1},
            {"algorithm": "sha256", "value": "A" * 64},
            {"algorithm": "sha256", "value": "0" * 64, "extra": 1},
        )
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(InputValidationError):
                ResultDigest.from_dict(payload)  # type: ignore[arg-type]

    def test_claim_from_dict_rejects_nonobjects_and_missing_required_id(self) -> None:
        with self.assertRaises(InputValidationError):
            Claim.from_dict([])  # type: ignore[arg-type]
        with self.assertRaises(InputValidationError):
            Claim.from_dict({})

    def test_action_from_dict_rejects_nonobjects_missing_id_and_bad_types(self) -> None:
        with self.assertRaises(InputValidationError):
            ActionRecord.from_dict("action")  # type: ignore[arg-type]
        with self.assertRaises(InputValidationError):
            ActionRecord.from_dict({"tool": "t", "status": "proposed"})
        with self.assertRaises(InputValidationError):
            ActionRecord.from_dict({"action_id": "a", "tool": "t", "status": "proposed", "evidence_refs": [1]})

    def test_case_from_dict_rejects_wrong_container_types_and_missing_id(self) -> None:
        for payload in (
            None,
            {"case_id": "x", "claims": {}},
            {"case_id": "x", "claims": [], "actions": {}},
            {"case_id": "x", "claims": [], "metadata": []},
            {"claims": []},
        ):
            with self.subTest(payload=payload), self.assertRaises((InputValidationError, ValueError)):
                ArtifactCase.from_dict(payload)  # type: ignore[arg-type]

    def test_config_rejects_invalid_scope_and_severe_thresholds(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("scope", [Claim("x")]), AuditConfig(scope_limitation_threshold=1.1))
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("severe", [Claim("x")]), AuditConfig(severe_issue_threshold=-1.0))

    def test_claim_validation_rejects_invalid_materiality_formula_severity_and_note(self) -> None:
        invalid_claims = (
            Claim("x", generated_value=1.0, source_value=1.0, materiality_threshold=0.0),
            Claim("x", formula_check="maybe"),
            Claim("x", qualitative_severity=-0.1),
            Claim("x", note=1),  # type: ignore[arg-type]
        )
        for claim in invalid_claims:
            with self.subTest(claim=claim), self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("invalid", [claim]))

    def test_validate_action_rejects_wrong_digest_and_evidence_shape(self) -> None:
        object_action = object.__new__(ActionRecord)
        object.__setattr__(object_action, "action_id", "a")
        object.__setattr__(object_action, "tool", "t")
        object.__setattr__(object_action, "status", "executed")
        object.__setattr__(object_action, "evidence_refs", ())
        object.__setattr__(object_action, "result_hash", None)
        object.__setattr__(object_action, "exception", None)
        object.__setattr__(object_action, "result_digest", "not-a-digest")
        with self.assertRaises(ValueError):
            validate_action(object_action)

        object.__setattr__(object_action, "result_digest", None)
        object.__setattr__(object_action, "evidence_refs", "ref")
        with self.assertRaises(ValueError):
            validate_action(object_action)

    def test_validate_case_rejects_wrong_internal_types(self) -> None:
        for field, value in (("claims", (Claim("x"),)), ("actions", ()), ("metadata", [])):
            case = ArtifactCase("x", [Claim("x")])
            setattr(case, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_case(case)

        with self.assertRaises(ValueError):
            validate_case(ArtifactCase("x", ["not-a-claim"]))  # type: ignore[list-item]
        with self.assertRaises(ValueError):
            validate_case(ArtifactCase("x", [Claim("x")], ["not-an-action"]))  # type: ignore[list-item]

    def test_core_records_alignment_reasons(self) -> None:
        result = evaluate_case(
            ArtifactCase(
                "alignment",
                [Claim("x", entity_aligned=False, metric_aligned=False)],
            )
        )
        reasons = result.claim_assessments[0].reasons
        self.assertIn("entity_mismatch", reasons)
        self.assertIn("metric_mismatch", reasons)

    def test_weight_sum_overflow_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_case(ArtifactCase("overflow", [Claim("a", weight=1e308), Claim("b", weight=1e308)]))

    def test_cli_validate_case_reports_valid_and_invalid_without_traceback(self) -> None:
        self.assertEqual(validate_case_path(ROOT / "examples" / "clean_case.json"), 0)
        with patch("auditable_financial_agents.cli.load_case", side_effect=ValueError("bad input")):
            self.assertEqual(validate_case_path(Path("missing.json")), 2)
        self.assertEqual(main(["validate-case", str(ROOT / "examples" / "clean_case.json")]), 0)

    def test_finite_guard_rejects_nonfinite_derived_output(self) -> None:
        # Exercise the final defense-in-depth check without changing scientific
        # calculations: all earlier numeric validation remains active.
        with patch("auditable_financial_agents.core.math.isfinite", side_effect=[True] * 6 + [False]):
            with self.assertRaises(ValueError):
                evaluate_case(ArtifactCase("finite-guard", [Claim("x")]))


if __name__ == "__main__":
    unittest.main()

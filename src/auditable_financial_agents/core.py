from __future__ import annotations

import math
from collections.abc import Iterable

from .schema import (
    VALID_OPINIONS,
    ArtifactCase,
    AuditConfig,
    AuditResult,
    Claim,
    ClaimAssessment,
    validate_case,
)
from .trace import assess_trace


def _numeric_severity(claim: Claim) -> float:
    if (
        claim.generated_value is None
        or claim.source_value is None
        or claim.materiality_threshold is None
    ):
        return 0.0
    difference = claim.generated_value - claim.source_value
    if not math.isfinite(difference):
        raise ValueError(f"claim {claim.claim_id}: numeric difference overflowed")
    severity = abs(difference) / claim.materiality_threshold
    if not math.isfinite(severity):
        raise ValueError(f"claim {claim.claim_id}: numeric severity overflowed")
    return severity


def _finite_product(name: str, left: float, right: float) -> float:
    value = left * right
    if not math.isfinite(value):
        raise ValueError(f"{name} overflowed; use finite, representable inputs")
    return value


def assess_claim(claim: Claim) -> ClaimAssessment:
    reasons: list[str] = []
    evidence_valid = claim.evidence_valid()
    if not claim.provenance_valid:
        reasons.append("missing_or_invalid_provenance")
    if not claim.entity_aligned:
        reasons.append("entity_mismatch")
    if not claim.period_aligned:
        reasons.append("period_mismatch")
    if not claim.metric_aligned:
        reasons.append("metric_mismatch")

    numeric_severity = _numeric_severity(claim)
    effective_severity = max(numeric_severity, claim.qualitative_severity)

    if claim.formula_check == "fail":
        effective_severity = max(effective_severity, 1.0)
        reasons.append("formula_check_failed")
    elif claim.formula_check == "unknown":
        reasons.append("formula_check_unknown")

    if claim.qualitative_severity >= 1.0:
        reasons.append("qualitative_materiality_override")
    if numeric_severity >= 1.0:
        reasons.append("numeric_materiality_threshold_exceeded")

    material = effective_severity >= 1.0
    uncertainty_multiplier = 1.25 if not evidence_valid or claim.formula_check == "unknown" else 1.0
    weighted_priority = _finite_product(
        f"claim {claim.claim_id} weighted priority",
        _finite_product(
            f"claim {claim.claim_id} weighted severity",
            claim.weight,
            max(effective_severity, 0.10),
        ),
        uncertainty_multiplier,
    )

    return ClaimAssessment(
        claim_id=claim.claim_id,
        evidence_valid=evidence_valid,
        numeric_severity=numeric_severity,
        effective_severity=effective_severity,
        material=material,
        weighted_priority=weighted_priority,
        reasons=tuple(reasons),
    )


def evaluate_case(case: ArtifactCase, config: AuditConfig | None = None) -> AuditResult:
    validate_case(case)
    config = config or AuditConfig()
    config.validate()

    assessments = [assess_claim(claim) for claim in case.claims]
    try:
        total_weight = math.fsum(claim.weight for claim in case.claims)
    except OverflowError as exc:
        raise ValueError("claim weights must have a finite positive sum") from exc
    if not math.isfinite(total_weight) or total_weight <= 0:
        raise ValueError("claim weights must have a finite positive sum")
    normalized_weights = [claim.weight / total_weight for claim in case.claims]
    total_normalized_weight = math.fsum(normalized_weights)
    valid_weight = math.fsum(
        normalized_weight
        for normalized_weight, assessment in zip(
            normalized_weights, assessments, strict=True
        )
        if assessment.evidence_valid
    )
    evidence_sufficiency = valid_weight / total_normalized_weight
    scope_limitation = 1.0 - evidence_sufficiency

    max_weighted_severity = max(
        _finite_product(
            f"claim {claim.claim_id} weighted severity",
            claim.weight,
            assessment.effective_severity,
        )
        for claim, assessment in zip(case.claims, assessments, strict=True)
    )
    max_effective_severity = max(
        assessment.effective_severity for assessment in assessments
    )
    material_weight = math.fsum(
        normalized_weight
        for normalized_weight, assessment in zip(
            normalized_weights, assessments, strict=True
        )
        if assessment.material
    )
    pervasiveness = material_weight / total_normalized_weight

    if evidence_sufficiency < config.evidence_threshold:
        opinion = "Disclaimer"
    elif evidence_sufficiency >= config.evidence_threshold and max_effective_severity < 1.0:
        opinion = "Clean"
    elif (
        evidence_sufficiency >= config.evidence_threshold
        and max_effective_severity >= 1.0
        and pervasiveness < config.pervasiveness_threshold
    ):
        opinion = "Qualified"
    elif evidence_sufficiency >= config.evidence_threshold:
        opinion = "Adverse"
    else:
        # Conservative fallback for low-evidence cases that sit below the explicit
        # scope-limit threshold because of unusual weights/threshold choices.
        opinion = "Disclaimer"

    trace = assess_trace(
        case.actions,
        case.expected_action_count,
        case.expected_executed_action_count,
    )
    critical_candidates: list[ClaimAssessment] = []
    informational_ids: set[str] = set()
    for claim, assessment in zip(case.claims, assessments, strict=True):
        unknown_formula = claim.formula_check == "unknown"
        invalid_evidence = not assessment.evidence_valid
        unknown_opt_out = unknown_formula and not config.review_on_unknown_formula
        invalid_opt_out = invalid_evidence and not config.review_on_invalid_evidence

        # Materiality is claim-level.  An explicit opt-out can downgrade only
        # a non-material uncertainty; it can never hide a material claim from
        # critical matters or make the review basis contradictory.
        if assessment.material:
            critical_candidates.append(assessment)
        elif (unknown_formula and config.review_on_unknown_formula) or (
            invalid_evidence and config.review_on_invalid_evidence
        ):
            critical_candidates.append(assessment)
        elif (unknown_opt_out or invalid_opt_out) and assessment.reasons:
            informational_ids.add(assessment.claim_id)
        elif assessment.reasons:
            critical_candidates.append(assessment)

    critical = sorted(
        critical_candidates,
        key=lambda item: (-item.weighted_priority, item.claim_id),
    )
    critical_matters_total = len(critical)
    critical_matters = [
        item.claim_id for item in critical[: config.max_critical_matters]
    ]
    informational_matters = sorted(informational_ids - set(critical_matters))
    invalid_evidence_ids = {
        assessment.claim_id for assessment in assessments if not assessment.evidence_valid
    }

    severe_claim = any(
        assessment.effective_severity >= config.severe_issue_threshold
        for assessment in assessments
    )
    unknown_formula_review = config.review_on_unknown_formula and any(
        claim.formula_check == "unknown" for claim in case.claims
    )
    invalid_evidence_review = config.review_on_invalid_evidence and bool(invalid_evidence_ids)
    human_review_required = (
        opinion != "Clean"
        or severe_claim
        or bool(trace.issues)
        or unknown_formula_review
        or invalid_evidence_review
        or critical_matters_total > 0
    )

    coverage_text = (
        "null"
        if trace.trace_completeness is None
        else f"{trace.trace_completeness:.3f}"
    )

    basis: list[str] = [
        f"evidence_sufficiency={evidence_sufficiency:.3f}",
        f"max_weighted_severity={max_weighted_severity:.3f}",
        f"max_effective_severity={max_effective_severity:.3f}",
        f"pervasiveness={pervasiveness:.3f}",
        f"trace_completeness={coverage_text}",
    ]
    if unknown_formula_review:
        basis.append("unresolved_formula_verification")
    elif any(claim.formula_check == "unknown" for claim in case.claims):
        basis.append("formula_verification_informational")
    if opinion == "Clean" and human_review_required:
        basis.append("clean opinion with unresolved human-review matters")
    elif opinion == "Clean":
        basis.append("sufficient evidence with no material unresolved issue")
    elif opinion == "Qualified":
        basis.append("material issue is localized under the configured threshold")
    elif opinion == "Adverse":
        basis.append("material issues are pervasive under the configured threshold")
    else:
        basis.append("evidence limitation blocks a safe clean judgment")

    numeric_outputs = {
        "evidence_sufficiency": evidence_sufficiency,
        "scope_limitation": scope_limitation,
        "max_weighted_severity": max_weighted_severity,
        "max_effective_severity": max_effective_severity,
        "pervasiveness": pervasiveness,
    }
    if not all(math.isfinite(value) for value in numeric_outputs.values()):
        raise ValueError("audit result contains a non-finite numeric output")

    return AuditResult(
        case_id=case.case_id,
        opinion=opinion,
        evidence_sufficiency=evidence_sufficiency,
        scope_limitation=scope_limitation,
        max_weighted_severity=max_weighted_severity,
        max_effective_severity=max_effective_severity,
        pervasiveness=pervasiveness,
        human_review_required=human_review_required,
        critical_matters=critical_matters,
        claim_assessments=assessments,
        trace_assessment=trace,
        basis=basis,
        schema_version="2.0",
        informational_matters=informational_matters,
        critical_matters_total=critical_matters_total,
        critical_matters_truncated=critical_matters_total > len(critical_matters),
        critical_matters_limit=config.max_critical_matters,
    )


def false_clean_rate(
    predicted: Iterable[str], expected: Iterable[str]
) -> tuple[int, int, float]:
    predicted_list = list(predicted)
    expected_list = list(expected)
    if len(predicted_list) != len(expected_list):
        raise ValueError("predicted and expected lengths differ")
    for name, labels in (("predicted", predicted_list), ("expected", expected_list)):
        invalid = [label for label in labels if label not in VALID_OPINIONS]
        if invalid:
            raise ValueError(f"{name} contains invalid opinion label: {invalid[0]!r}")
    non_clean = sum(label != "Clean" for label in expected_list)
    false_clean = sum(
        p == "Clean" and e != "Clean"
        for p, e in zip(predicted_list, expected_list, strict=True)
    )
    rate = 0.0 if non_clean == 0 else false_clean / non_clean
    return false_clean, non_clean, rate

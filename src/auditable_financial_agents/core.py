from __future__ import annotations

from collections.abc import Iterable

from .schema import (
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
    return abs(claim.generated_value - claim.source_value) / claim.materiality_threshold


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
    weighted_priority = claim.weight * max(effective_severity, 0.10) * uncertainty_multiplier

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

    assessments = [assess_claim(claim) for claim in case.claims]
    total_weight = sum(claim.weight for claim in case.claims)
    valid_weight = sum(
        claim.weight
        for claim, assessment in zip(case.claims, assessments, strict=True)
        if assessment.evidence_valid
    )
    evidence_sufficiency = valid_weight / total_weight
    scope_limitation = 1.0 - evidence_sufficiency

    max_weighted_severity = max(
        claim.weight * assessment.effective_severity
        for claim, assessment in zip(case.claims, assessments, strict=True)
    )
    material_weight = sum(
        claim.weight
        for claim, assessment in zip(case.claims, assessments, strict=True)
        if assessment.material
    )
    pervasiveness = material_weight / total_weight

    if (
        evidence_sufficiency < config.evidence_threshold
        and scope_limitation >= config.scope_limitation_threshold
    ):
        opinion = "Disclaimer"
    elif evidence_sufficiency >= config.evidence_threshold and max_weighted_severity < 1.0:
        opinion = "Clean"
    elif (
        evidence_sufficiency >= config.evidence_threshold
        and max_weighted_severity >= 1.0
        and pervasiveness < config.pervasiveness_threshold
    ):
        opinion = "Qualified"
    elif evidence_sufficiency >= config.evidence_threshold:
        opinion = "Adverse"
    else:
        # Conservative fallback for low-evidence cases that sit below the explicit
        # scope-limit threshold because of unusual weights/threshold choices.
        opinion = "Disclaimer"

    trace = assess_trace(case.actions)
    critical = sorted(
        (
            assessment
            for assessment in assessments
            if assessment.material or not assessment.evidence_valid or assessment.reasons
        ),
        key=lambda item: (-item.weighted_priority, item.claim_id),
    )
    critical_matters = [item.claim_id for item in critical[:5]]

    severe_claim = any(
        assessment.effective_severity >= config.severe_issue_threshold
        for assessment in assessments
    )
    human_review_required = (
        opinion != "Clean"
        or severe_claim
        or trace.failed_actions > 0
        or trace.undocumented_executions > 0
    )

    basis: list[str] = [
        f"evidence_sufficiency={evidence_sufficiency:.3f}",
        f"max_weighted_severity={max_weighted_severity:.3f}",
        f"pervasiveness={pervasiveness:.3f}",
        f"trace_completeness={trace.trace_completeness:.3f}",
    ]
    if opinion == "Clean":
        basis.append("sufficient evidence with no material unresolved issue")
    elif opinion == "Qualified":
        basis.append("material issue is localized under the configured threshold")
    elif opinion == "Adverse":
        basis.append("material issues are pervasive under the configured threshold")
    else:
        basis.append("evidence limitation blocks a safe clean judgment")

    return AuditResult(
        case_id=case.case_id,
        opinion=opinion,
        evidence_sufficiency=evidence_sufficiency,
        scope_limitation=scope_limitation,
        max_weighted_severity=max_weighted_severity,
        pervasiveness=pervasiveness,
        human_review_required=human_review_required,
        critical_matters=critical_matters,
        claim_assessments=assessments,
        trace_assessment=trace,
        basis=basis,
    )


def false_clean_rate(
    predicted: Iterable[str], expected: Iterable[str]
) -> tuple[int, int, float]:
    predicted_list = list(predicted)
    expected_list = list(expected)
    if len(predicted_list) != len(expected_list):
        raise ValueError("predicted and expected lengths differ")
    non_clean = sum(label != "Clean" for label in expected_list)
    false_clean = sum(
        p == "Clean" and e != "Clean"
        for p, e in zip(predicted_list, expected_list, strict=True)
    )
    rate = 0.0 if non_clean == 0 else false_clean / non_clean
    return false_clean, non_clean, rate

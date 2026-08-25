from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

VALID_OPINIONS = {"Clean", "Qualified", "Adverse", "Disclaimer"}
VALID_ACTION_STATUS = {"proposed", "executed", "failed", "skipped"}


@dataclass(frozen=True)
class Claim:
    claim_id: str
    weight: float = 1.0
    generated_value: float | None = None
    source_value: float | None = None
    materiality_threshold: float | None = None
    provenance_valid: bool = True
    entity_aligned: bool = True
    period_aligned: bool = True
    metric_aligned: bool = True
    formula_check: str = "pass"  # pass | fail | unknown
    qualitative_severity: float = 0.0
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Claim:
        return cls(**data)

    def evidence_valid(self) -> bool:
        return all(
            [
                self.provenance_valid,
                self.entity_aligned,
                self.period_aligned,
                self.metric_aligned,
            ]
        )


@dataclass(frozen=True)
class ActionRecord:
    action_id: str
    tool: str
    status: str
    evidence_refs: tuple[str, ...] = ()
    result_hash: str | None = None
    exception: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionRecord:
        evidence_refs = tuple(data.get("evidence_refs", ()))
        return cls(
            action_id=data["action_id"],
            tool=data["tool"],
            status=data["status"],
            evidence_refs=evidence_refs,
            result_hash=data.get("result_hash"),
            exception=data.get("exception"),
        )


@dataclass(frozen=True)
class AuditConfig:
    evidence_threshold: float = 0.85
    pervasiveness_threshold: float = 0.50
    scope_limitation_threshold: float = 0.15
    severe_issue_threshold: float = 1.50


@dataclass
class ArtifactCase:
    case_id: str
    claims: list[Claim]
    actions: list[ActionRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactCase:
        return cls(
            case_id=data["case_id"],
            claims=[Claim.from_dict(item) for item in data.get("claims", [])],
            actions=[ActionRecord.from_dict(item) for item in data.get("actions", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class ClaimAssessment:
    claim_id: str
    evidence_valid: bool
    numeric_severity: float
    effective_severity: float
    material: bool
    weighted_priority: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TraceAssessment:
    total_actions: int
    executed_actions: int
    failed_actions: int
    undocumented_executions: int
    trace_completeness: float
    issues: tuple[str, ...]


@dataclass
class AuditResult:
    case_id: str
    opinion: str
    evidence_sufficiency: float
    scope_limitation: float
    max_weighted_severity: float
    pervasiveness: float
    human_review_required: bool
    critical_matters: list[str]
    claim_assessments: list[ClaimAssessment]
    trace_assessment: TraceAssessment
    basis: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def validate_case(case: ArtifactCase) -> None:
    if not case.case_id.strip():
        raise ValueError("case_id must be non-empty")
    if not case.claims:
        raise ValueError("at least one claim is required")
    seen: set[str] = set()
    for claim in case.claims:
        if claim.claim_id in seen:
            raise ValueError(f"duplicate claim_id: {claim.claim_id}")
        seen.add(claim.claim_id)
        if claim.weight <= 0:
            raise ValueError(f"claim {claim.claim_id}: weight must be positive")
        if claim.materiality_threshold is not None and claim.materiality_threshold <= 0:
            raise ValueError(
                f"claim {claim.claim_id}: materiality_threshold must be positive"
            )
        if claim.formula_check not in {"pass", "fail", "unknown"}:
            raise ValueError(
                f"claim {claim.claim_id}: formula_check must be pass/fail/unknown"
            )
        if claim.qualitative_severity < 0:
            raise ValueError(
                f"claim {claim.claim_id}: qualitative_severity must be non-negative"
            )
    seen_actions: set[str] = set()
    for action in case.actions:
        if action.action_id in seen_actions:
            raise ValueError(f"duplicate action_id: {action.action_id}")
        seen_actions.add(action.action_id)
        if action.status not in VALID_ACTION_STATUS:
            raise ValueError(
                f"action {action.action_id}: invalid status {action.status!r}"
            )

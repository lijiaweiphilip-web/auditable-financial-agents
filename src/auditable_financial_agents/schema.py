from __future__ import annotations

import math
import warnings
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
    scope_limitation_threshold: float | None = None
    severe_issue_threshold: float = 1.50
    review_on_unknown_formula: bool = True

    def __post_init__(self) -> None:
        if self.scope_limitation_threshold is not None:
            warnings.warn(
                "scope_limitation_threshold is deprecated and no longer affects opinion; "
                "use evidence_threshold instead",
                DeprecationWarning,
                stacklevel=2,
            )

    def validate(self) -> None:
        for name, value in (
            ("evidence_threshold", self.evidence_threshold),
            ("pervasiveness_threshold", self.pervasiveness_threshold),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.scope_limitation_threshold is not None:
            if not math.isfinite(self.scope_limitation_threshold):
                raise ValueError("scope_limitation_threshold must be finite")
            if not 0.0 <= self.scope_limitation_threshold <= 1.0:
                raise ValueError("scope_limitation_threshold must be within [0, 1]")
        if not math.isfinite(self.severe_issue_threshold) or self.severe_issue_threshold < 0.0:
            raise ValueError("severe_issue_threshold must be non-negative")


@dataclass
class ArtifactCase:
    case_id: str
    claims: list[Claim]
    actions: list[ActionRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    expected_action_count: int | None = None
    expected_executed_action_count: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactCase:
        return cls(
            case_id=data["case_id"],
            claims=[Claim.from_dict(item) for item in data.get("claims", [])],
            actions=[ActionRecord.from_dict(item) for item in data.get("actions", [])],
            metadata=dict(data.get("metadata", {})),
            expected_action_count=data.get("expected_action_count"),
            expected_executed_action_count=data.get("expected_executed_action_count"),
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
    trace_completeness: float | None
    issues: tuple[str, ...]
    task_completeness: bool | None = None
    completeness_basis: str = "executed_action_documentation_coverage"
    schema_version: str = "2.0"
    executed_action_documentation_coverage: float | None = None
    observed_action_records: int = 0
    terminal_action_records: int = 0
    successful_executions: int = 0
    expected_executed_action_count: int | None = None


@dataclass
class AuditResult:
    case_id: str
    opinion: str
    evidence_sufficiency: float
    scope_limitation: float
    max_weighted_severity: float
    max_effective_severity: float
    pervasiveness: float
    human_review_required: bool
    critical_matters: list[str]
    claim_assessments: list[ClaimAssessment]
    trace_assessment: TraceAssessment
    basis: list[str]
    schema_version: str = "2.0"

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
        if not math.isfinite(claim.weight) or claim.weight <= 0:
            raise ValueError(f"claim {claim.claim_id}: weight must be positive")
        for field_name, field_value in (
            ("generated_value", claim.generated_value),
            ("source_value", claim.source_value),
            ("materiality_threshold", claim.materiality_threshold),
            ("qualitative_severity", claim.qualitative_severity),
        ):
            if field_value is not None and not math.isfinite(field_value):
                raise ValueError(f"claim {claim.claim_id}: {field_name} must be finite")
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
    for name, count in (
        ("expected_action_count", case.expected_action_count),
        ("expected_executed_action_count", case.expected_executed_action_count),
    ):
        if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
            raise ValueError(f"{name} must be a non-negative integer when provided")

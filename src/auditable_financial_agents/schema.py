from __future__ import annotations

import math
import warnings
from dataclasses import asdict, dataclass, field
from numbers import Real
from typing import Any

VALID_OPINIONS = {"Clean", "Qualified", "Adverse", "Disclaimer"}
VALID_ACTION_STATUS = {"proposed", "executed", "failed", "skipped"}


def _is_real_number(value: Any) -> bool:
    """Return true for finite-number candidates, excluding Python bool."""

    return isinstance(value, Real) and not isinstance(value, bool)


def _require_non_empty_string(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_bool(name: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")


def _require_finite_number(name: str, value: Any) -> None:
    if not _is_real_number(value) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")


def _require_optional_finite_number(name: str, value: Any) -> None:
    if value is not None:
        _require_finite_number(name, value)


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
        if not isinstance(data, dict):
            raise ValueError("claim must be an object")
        claim = cls(**data)
        _validate_claim(claim)
        return claim

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
        if not isinstance(data, dict):
            raise ValueError("action must be an object")
        raw_refs = data.get("evidence_refs", ())
        if isinstance(raw_refs, str) or not isinstance(raw_refs, (list, tuple)):
            raise ValueError("evidence_refs must be a list or tuple of strings")
        action = cls(
            action_id=data["action_id"],
            tool=data["tool"],
            status=data["status"],
            evidence_refs=tuple(raw_refs),
            result_hash=data.get("result_hash"),
            exception=data.get("exception"),
        )
        validate_action(action)
        return action


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
        _require_finite_number("evidence_threshold", self.evidence_threshold)
        _require_finite_number("pervasiveness_threshold", self.pervasiveness_threshold)
        _require_finite_number("severe_issue_threshold", self.severe_issue_threshold)
        _require_bool("review_on_unknown_formula", self.review_on_unknown_formula)
        for name, value in (
            ("evidence_threshold", self.evidence_threshold),
            ("pervasiveness_threshold", self.pervasiveness_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.scope_limitation_threshold is not None:
            _require_finite_number(
                "scope_limitation_threshold", self.scope_limitation_threshold
            )
            if not 0.0 <= self.scope_limitation_threshold <= 1.0:
                raise ValueError("scope_limitation_threshold must be within [0, 1]")
        if self.severe_issue_threshold < 0.0:
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
        if not isinstance(data, dict):
            raise ValueError("case must be an object")
        raw_claims = data.get("claims", [])
        raw_actions = data.get("actions", [])
        if not isinstance(raw_claims, list):
            raise ValueError("claims must be a list")
        if not isinstance(raw_actions, list):
            raise ValueError("actions must be a list")
        raw_metadata = data.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raise ValueError("metadata must be an object")
        case = cls(
            case_id=data["case_id"],
            claims=[Claim.from_dict(item) for item in raw_claims],
            actions=[ActionRecord.from_dict(item) for item in raw_actions],
            metadata=dict(raw_metadata),
            expected_action_count=data.get("expected_action_count"),
            expected_executed_action_count=data.get("expected_executed_action_count"),
        )
        validate_case(case)
        return case


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
    expected_action_count: int | None = None
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
    informational_matters: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def _validate_claim(claim: Claim) -> None:
    _require_non_empty_string("claim_id", claim.claim_id)
    _require_finite_number("claim weight", claim.weight)
    if claim.weight <= 0:
        raise ValueError(f"claim {claim.claim_id}: weight must be positive")
    numeric_values = (
        claim.generated_value,
        claim.source_value,
        claim.materiality_threshold,
    )
    numeric_present = [value is not None for value in numeric_values]
    if any(numeric_present) and not all(numeric_present):
        raise ValueError(
            f"claim {claim.claim_id}: generated_value, source_value and "
            "materiality_threshold must be supplied together"
        )
    for field_name, field_value in (
        ("generated_value", claim.generated_value),
        ("source_value", claim.source_value),
        ("materiality_threshold", claim.materiality_threshold),
        ("qualitative_severity", claim.qualitative_severity),
    ):
        _require_optional_finite_number(
            f"claim {claim.claim_id}: {field_name}", field_value
        )
    for field_name, field_value in (
        ("provenance_valid", claim.provenance_valid),
        ("entity_aligned", claim.entity_aligned),
        ("period_aligned", claim.period_aligned),
        ("metric_aligned", claim.metric_aligned),
    ):
        _require_bool(f"claim {claim.claim_id}: {field_name}", field_value)
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
    if not isinstance(claim.note, str):
        raise ValueError(f"claim {claim.claim_id}: note must be a string")


def validate_action(action: ActionRecord) -> None:
    _require_non_empty_string("action_id", action.action_id)
    _require_non_empty_string("tool", action.tool)
    if not isinstance(action.status, str) or action.status not in VALID_ACTION_STATUS:
        raise ValueError(f"action {action.action_id}: invalid status {action.status!r}")
    if isinstance(action.evidence_refs, str) or not isinstance(
        action.evidence_refs, (list, tuple)
    ):
        raise ValueError(
            f"action {action.action_id}: evidence_refs must be a list or tuple"
        )
    for reference in action.evidence_refs:
        _require_non_empty_string("evidence reference", reference)
    if len(set(action.evidence_refs)) != len(action.evidence_refs):
        raise ValueError(f"action {action.action_id}: duplicate evidence reference")
    if action.result_hash is not None:
        _require_non_empty_string("result_hash", action.result_hash)
    if action.exception is not None:
        _require_non_empty_string("exception", action.exception)
    if action.status in {"proposed", "skipped"} and action.result_hash is not None:
        raise ValueError(
            f"action {action.action_id}: {action.status} action cannot carry result_hash"
        )


def validate_case(case: ArtifactCase) -> None:
    _require_non_empty_string("case_id", case.case_id)
    if not case.claims:
        raise ValueError("at least one claim is required")
    if not isinstance(case.claims, list):
        raise ValueError("claims must be a list")
    if not isinstance(case.actions, list):
        raise ValueError("actions must be a list")
    if not isinstance(case.metadata, dict):
        raise ValueError("metadata must be an object")
    seen: set[str] = set()
    for claim in case.claims:
        if not isinstance(claim, Claim):
            raise ValueError("claims must contain Claim objects")
        if claim.claim_id in seen:
            raise ValueError(f"duplicate claim_id: {claim.claim_id}")
        seen.add(claim.claim_id)
        _validate_claim(claim)
    seen_actions: set[str] = set()
    for action in case.actions:
        if not isinstance(action, ActionRecord):
            raise ValueError("actions must contain ActionRecord objects")
        validate_action(action)
        if action.action_id in seen_actions:
            raise ValueError(f"duplicate action_id: {action.action_id}")
        seen_actions.add(action.action_id)
    for name, count in (
        ("expected_action_count", case.expected_action_count),
        ("expected_executed_action_count", case.expected_executed_action_count),
    ):
        if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
            raise ValueError(f"{name} must be a non-negative integer when provided")
    if (
        case.expected_action_count is not None
        and case.expected_executed_action_count is not None
        and case.expected_executed_action_count > case.expected_action_count
    ):
        raise ValueError(
            "expected_executed_action_count cannot exceed expected_action_count"
        )

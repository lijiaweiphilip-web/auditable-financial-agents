from __future__ import annotations

from collections.abc import Sequence

from .schema import ActionRecord, TraceAssessment, validate_action


def _validate_expected_count(name: str, value: int | None) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{name} must be a non-negative integer when provided")


def assess_trace(
    actions: Sequence[ActionRecord],
    expected_action_count: int | None = None,
    expected_executed_action_count: int | None = None,
) -> TraceAssessment:
    _validate_expected_count("expected_action_count", expected_action_count)
    _validate_expected_count("expected_executed_action_count", expected_executed_action_count)
    issues: list[str] = []
    executed = 0
    failed = 0
    undocumented = 0
    documented = 0
    successful = 0

    terminal = 0
    for action in actions:
        validate_action(action)
        if action.status == "executed":
            executed += 1
            terminal += 1
            has_evidence = bool(action.evidence_refs)
            has_hash = bool(action.result_hash)
            if has_evidence and has_hash:
                documented += 1
            else:
                undocumented += 1
                issues.append(f"{action.action_id}:executed_without_complete_evidence")
            if action.exception:
                issues.append(f"{action.action_id}:executed_with_exception")
            else:
                successful += 1
        elif action.status == "failed":
            failed += 1
            terminal += 1
            issues.append(f"{action.action_id}:failed_action")
        elif action.status == "skipped":
            terminal += 1
            if action.exception:
                issues.append(f"{action.action_id}:skipped_with_exception")
            else:
                issues.append(f"{action.action_id}:skipped_without_reason")

    record_count_ok = expected_action_count is None or len(actions) >= expected_action_count
    execution_count_ok = (
        expected_executed_action_count is None
        or successful >= expected_executed_action_count
    )
    if expected_action_count is None and expected_executed_action_count is None:
        task_completeness = None
        completeness_basis = "no_expected_actions"
    else:
        if expected_action_count is not None and expected_executed_action_count is not None:
            completeness_basis = "expected_action_records_and_executions"
        elif expected_executed_action_count is not None:
            completeness_basis = "expected_executed_actions"
        else:
            completeness_basis = "expected_action_records"
        all_records_successful = bool(actions) and all(
            action.status == "executed" and not action.exception for action in actions
        )
        no_records_expected = expected_action_count == 0 and expected_executed_action_count in (None, 0)
        task_completeness = no_records_expected or (
            record_count_ok and execution_count_ok and all_records_successful
        )
        if not record_count_ok:
            issues.append(
                "empty_trace_when_actions_expected"
                if not actions
                else "trace_shorter_than_expected"
            )
        if not execution_count_ok:
            issues.append("executed_actions_shorter_than_expected")

    trace_completeness = documented / executed if executed else None
    return TraceAssessment(
        total_actions=len(actions),
        executed_actions=executed,
        failed_actions=failed,
        undocumented_executions=undocumented,
        trace_completeness=trace_completeness,
        issues=tuple(issues),
        task_completeness=task_completeness,
        completeness_basis=completeness_basis,
        executed_action_documentation_coverage=trace_completeness,
        observed_action_records=len(actions),
        terminal_action_records=terminal,
        successful_executions=successful,
        expected_action_count=expected_action_count,
        expected_executed_action_count=expected_executed_action_count,
    )

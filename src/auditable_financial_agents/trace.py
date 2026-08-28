from __future__ import annotations

from collections.abc import Sequence

from .schema import ActionRecord, TraceAssessment


def assess_trace(
    actions: Sequence[ActionRecord], expected_action_count: int | None = None
) -> TraceAssessment:
    if not actions:
        if expected_action_count is None:
            task_completeness = None
            completeness_basis = "no_expected_actions"
            issues: tuple[str, ...] = ()
        elif expected_action_count == 0:
            task_completeness = True
            completeness_basis = "expected_action_count"
            issues = ()
        else:
            task_completeness = False
            completeness_basis = "expected_action_count"
            issues = ("empty_trace_when_actions_expected",)
        return TraceAssessment(
            total_actions=0,
            executed_actions=0,
            failed_actions=0,
            undocumented_executions=0,
            trace_completeness=1.0,
            issues=issues,
            task_completeness=task_completeness,
            completeness_basis=completeness_basis,
        )

    issues: list[str] = []
    executed = 0
    failed = 0
    undocumented = 0
    documented = 0

    for action in actions:
        if action.status == "executed":
            executed += 1
            has_evidence = bool(action.evidence_refs)
            has_hash = bool(action.result_hash)
            if has_evidence and has_hash:
                documented += 1
            else:
                undocumented += 1
                issues.append(f"{action.action_id}:executed_without_complete_evidence")
        elif action.status == "failed":
            failed += 1
            issues.append(f"{action.action_id}:failed_action")
        elif action.status == "skipped" and action.exception:
            issues.append(f"{action.action_id}:skipped_with_exception")

    if expected_action_count is None:
        task_completeness = None
        completeness_basis = "executed_action_documentation_coverage"
    else:
        task_completeness = len(actions) >= expected_action_count
        completeness_basis = "expected_action_count"
        if not task_completeness:
            issues.append("trace_shorter_than_expected")

    denominator = max(executed, 1)
    trace_completeness = documented / denominator if executed else 1.0
    return TraceAssessment(
        total_actions=len(actions),
        executed_actions=executed,
        failed_actions=failed,
        undocumented_executions=undocumented,
        trace_completeness=trace_completeness,
        issues=tuple(issues),
        task_completeness=task_completeness,
        completeness_basis=completeness_basis,
    )

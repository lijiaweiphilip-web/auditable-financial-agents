from __future__ import annotations

from collections.abc import Sequence

from .schema import ActionRecord, TraceAssessment


def assess_trace(actions: Sequence[ActionRecord]) -> TraceAssessment:
    if not actions:
        return TraceAssessment(
            total_actions=0,
            executed_actions=0,
            failed_actions=0,
            undocumented_executions=0,
            trace_completeness=1.0,
            issues=(),
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

    denominator = max(executed, 1)
    trace_completeness = documented / denominator if executed else 1.0
    return TraceAssessment(
        total_actions=len(actions),
        executed_actions=executed,
        failed_actions=failed,
        undocumented_executions=undocumented,
        trace_completeness=trace_completeness,
        issues=tuple(issues),
    )

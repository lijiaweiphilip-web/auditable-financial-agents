# Trace state contract (schema v2)

The trace assessor distinguishes observed records from successful executions.
`expected_action_count` is a minimum number of expected trace records;
`expected_executed_action_count` is a minimum number of successful executions.
Neither field turns a proposed or failed record into a successful task step.

| State | Schema valid | Trace issue | Human review | Successful execution |
|---|---:|---:|---:|---:|
| No records, no expectation | yes | no | no | 0 |
| No records, expected records | yes | yes | yes | 0 |
| Proposed-only | yes | no | no, unless an expectation is unmet | 0 |
| Executed with evidence and digest | yes | no | no | 1 |
| Executed without evidence or digest | yes | yes | yes | 1 |
| Executed with exception | yes | yes | yes | 0 |
| Failed | yes | yes | yes | 0 |
| Skipped with a reason | yes | yes | yes | 0 |
| Skipped with an exception | yes | yes | yes | 0 |

`executed_action_documentation_coverage` is
`documented executed actions / executed actions`. It is `null` when no action
has status `executed`; the deprecated `trace_completeness` alias is also
nullable. Neither metric claims that a task plan was complete. When expected
counts are supplied, `task_completeness` is true only when the minimum counts
are met and every observed record is a successful, documented execution.

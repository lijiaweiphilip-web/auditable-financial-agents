**Prospective research extension. Not an HCOMP 2026 accepted-paper result.**

# Action-trace extension

The accepted paper evaluates generated financial artifacts and evidence certificates. A natural next question for professional financial agents is whether review can extend upstream into the agent's action chain.

## Current prototype checks

An optional action record contains:

- action identifier;
- tool name;
- status (`proposed`, `executed`, `failed`, `skipped`);
- evidence references;
- result hash;
- exception note.

The prototype reports:

- executed actions;
- failed actions;
- executed actions without complete evidence/hash records;
- an executed-action documentation coverage ratio. This is not a claim that the
  complete task plan was executed.

`ArtifactCase.expected_action_count` may be supplied when a task has an
explicit expected action count. In that mode an empty or shorter trace is an
issue and requires human review. Without an expected count, an empty trace has
`task_completeness=None` rather than being described as a complete task.

Any trace issue—including failed actions, skipped actions with exceptions,
undocumented executions, or an unmet expected action count—sets
`human_review_required=True`, even when final claims receive a `Clean` research
label.

## Research questions for a stronger extension

1. Can trace completeness predict false-clean artifact decisions?
2. Which action classes deserve mandatory deterministic checks?
3. When should a monitor escalate to a human reviewer rather than allow an autonomous retry?
4. How should review cost be allocated across claims, calculations, tool calls, and scope limitations?
5. Can action-trace certificates improve reproducibility for professional economic/financial research agents?

These questions align with research on AI agents that plan, execute, interpret, and audit professional analytical work, but no claim is made that this prototype solves them.

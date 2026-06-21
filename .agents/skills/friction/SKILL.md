---
name: friction
description: Use when repo work exposes repeated steering, workflow confusion, false-success checks, missing evidence, unclear ownership, brittle process, todo/work friction, memory/history-based recurring friction, or a proposed new process gate. Classify the observed friction from available evidence and route the smallest useful fix without mutating state.
---

# Friction

Use this skill as a read-only lens. Try to identify friction from current
thread context, explicit corrections, tool output, validation logs, review
output, git history, active state, todos, and available memory. Treat memory as
recall, not authority.

## Rules

- Classify observed friction, not imagined future friction.
- Separate available evidence from inference and missing history.
- Record recurrence only when available context or memory shows it.
- Route deferred needs to the owning tracker, docs, or an explicit user
  decision.
- Route active objective, scope, validation, or closeout changes to the current
  work plan.
- Use the boundary workflow for unclear ownership.
- Prefer checks when the condition is mechanically observable.
- Prefer prose only for durable judgment, stop conditions, or workflow intent.
- Use human review when the condition needs judgment the repo cannot observe.
- Reject gates that add ceremony without protecting observable value.
- Do not mutate state, add hooks, or change workflow guidance from this skill.

## Classes

- `check`: a repo check can observe the condition.
- `prose`: instructions need clearer behavior, authority, or stop conditions.
- `todo`: defer the need for later discussion or implementation.
- `work`: adjust the active work objective, scope, validation, or closeout.
- `human_review`: judgment is needed and cannot be automated yet.
- `external`: blocked by access, tooling, platform behavior, or policy.
- `reject`: the proposed fix is overreach or not source-backed.

## Output

```text
Friction verdict: observe | record | fix | reject
Friction:
Evidence:
Missing evidence:
Class:
Owner:
Smallest useful change:
Validation:
```

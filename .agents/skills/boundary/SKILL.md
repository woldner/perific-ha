---
name: boundary
description: Use when deciding where behavior, styling, data, validation, docs, generated output, automation, or human judgment belongs. Apply whenever a task asks or implies "where does this belong?", "which layer owns this?", "should this be code, config, prose, a check, data, or review?", or when a change might be placed in more than one surface. Keep the call source-backed and do not treat prompts or prose as enforcement.
---

# Boundary

Use this skill to decide the owning surface before changing behavior, styling,
data, validation, docs, generated output, automation, or review workflow.

## Rules

- State the behavior or decision being placed.
- Name the source authority an agent can inspect.
- Choose the narrowest owner that can make the behavior observable.
- Prefer existing source patterns before adding a new surface.
- Keep generated output owned by its source input and build step.
- Put runtime data, credentials, external platform state, and host/device facts
  in the owning system or config source unless repo automation owns the desired
  state.
- Put validation in automated checks when the expected result is observable.
- Use documentation for durable intent, workflow, and decision rules; do not use
  docs as proof that behavior works.
- Use human review for judgment that cannot yet be made observable.
- Reject prompt-only, prose-only, or comment-only enforcement for behavior,
  safety, completion, or release readiness.
- Treat user examples as probes, not scope limits or authority.
- Stop when the authority, owner, credentials, or validation path is unclear
  enough that choosing a surface would be guesswork.

## Method

1. State the proposed change in one sentence.
2. List the plausible owners.
3. Pick the owner with the closest authority and smallest durable surface.
4. Name what must not own the change.
5. Name the validation that proves the chosen boundary.

## Output

Use this standalone output only when the user asks for a boundary review or when
no stronger workflow output format applies. If another workflow requires a
specific format, keep that format and apply this skill to the boundary call
inside it.

Standalone output:

```text
Boundary verdict: pass | adjust | reject
Behavior:
Authority:
Owner:
Not owner:
Validation:
```

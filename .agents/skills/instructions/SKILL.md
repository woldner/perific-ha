---
name: instructions
description: Use when creating, editing, shortening, or reviewing durable instructional prose for agents or maintainers, including skills, prompts, diagnostics, runbooks, workflow guidance, and documentation rules. Apply before adding or recommending wording, even for small wording tweaks, so the result stays short, reusable, unambiguous, and source-backed. Do not use for ordinary descriptive, customer-facing, or one-off task prose.
---

# Instructions

Use this skill to turn proposed durable instructional prose into short reusable
guidance for future agents or maintainers. It applies when prose tells someone
how to work, decide, validate, or stop. Treat it as a filter before prose is
added, not as proof that the rule is enforced.

## Rules

- Write one behavior per instruction.
- Use direct verbs and observable nouns.
- Name the authority an agent can check: source, config, command, test, log,
  doc, or explicit human approval.
- Include stop conditions when proceeding would be unsafe or guesswork.
- Keep only behavior, authority, stop condition, and observable validation.
- Remove rationale, history, examples, temporary paths, raw logs, version trivia,
  and implementation detail unless needed for current behavior.
- Separate local facts from reusable rules. Keep facts beside their owning
  source; write rules without naming the triggering example.
- Prefer stable project terms already used by the target surface.
- Avoid vague words unless the same sentence defines observable evidence.
- Do not include secrets, credentials, private data, or loop-local state in
  reusable prose.
- Do not claim prose proves, enforces, approves, or completes work.
- If deterministic enforcement is needed, say what check or code should own it
  instead of adding more prose.

## Method

1. Identify the audience and expected lifetime.
2. State the behavior the prose must change.
3. Separate authority-backed facts from assumptions.
4. Delete content that belongs in source, checks, tests, logs, or task records.
5. Prefer the shortest wording that preserves the rule.

## Output

Use this standalone output only when the user asks for an instruction review or
when no stronger workflow output format applies. If another workflow requires a
specific format, keep that format and apply this skill to the wording inside it.

Standalone output:

```text
Instruction verdict: pass | edit | reject
Authority:
Instruction:
Boundary:
Validation:
```

---
name: testing
description: Use when adding, removing, widening, narrowing, or reviewing tests or validation, including automated tests, smoke tests, smoke checks, browser checks, visual checks, manual verification, coverage proposals, brittle assertions, broad snapshots, or any question about what should be tested. Decide the smallest high-signal proof for the explicit contract and reject validation that pins unrelated behavior.
---

# Testing

Use this skill to choose high-signal validation. The goal is to prove the
contract at risk, not to increase coverage for its own sake.

## Rules

- Name the risk the validation should reduce.
- Name the source authority: code, config, schema, command, generated artifact,
  preview, log, or explicit human approval.
- Name the owner closest to the behavior under test.
- Test explicit repo-owned contracts, not everything reachable from a workflow.
- Prefer the narrowest stable proof that catches the real failure.
- Use broader checks only when the narrower owner cannot prove the contract.
- State the blast radius: what future changes should and should not break this
  validation.
- Assert emitted text, payloads, visuals, generated files, and serialized shapes
  only at the layer that owns emitting them.
- Prefer neutral fixtures unless realistic data is required to exercise the
  contract.
- Treat existing checks as evidence; do not duplicate typecheck, lint, schema,
  build, smoke tests, review, or another test without a distinct risk.
- Reject tests that mainly pin implementation shape, incidental formatting,
  setup, routing, mocks, fixtures, or third-party internals.
- Stop when the contract, owner, authority, or proof path is unclear enough that
  adding validation would be guesswork.

## Method

1. State the behavior or regression risk.
2. Identify the owner and authority for that behavior.
3. State the explicit contract the validation must prove.
4. Check existing proof before adding or widening validation.
5. Choose the smallest stable validation boundary.
6. Reject unrelated scope and name the intended blast radius.

## Output

Use this standalone output only when the user asks for a testing decision or
when no stronger workflow output format applies. If another workflow requires a
specific format, keep that format and apply this skill to the testing decision
inside it.

Standalone output:

```text
Testing verdict: add | adjust | skip
Risk:
Authority:
Owner:
Contract:
Existing proof:
Chosen boundary:
Blast radius:
Rejected scope:
Validation:
```

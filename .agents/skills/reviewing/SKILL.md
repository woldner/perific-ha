---
name: reviewing
description: Use when reviewing code, docs, skills, commits, pull requests, staged or uncommitted diffs, native review output, review findings, review cadence, "scan the diff", "are these findings real?", "what should we review?", or when work may be complete and Codex must decide whether to review now or wait for a named gate. Choose the smallest source-backed review target and reject speculative findings.
---

# Reviewing

Use this skill to decide when and how to review a change. Review the contract at
risk; do not turn review into broad inspection or extra testing.

## Rules

- Name the review purpose and the contract at risk.
- Name the source authority: diff, commit, files, generated output, validation
  logs, preview, browser evidence, official docs, or explicit approval.
- Choose the smallest reviewable target that covers the contract.
- Review after coherent work reaches its validation gate.
- Wait when work is still mixed, unvalidated, or missing required proof;
  name the gate that must finish first.
- Lead with P0/P1 findings unless the user asks for broader review.
- Treat no P0/P1 findings as a valid result.
- Reject speculative findings, style-only comments, and unrelated scope.
- Check boundary drift, false-success behavior, stale same-contract references,
  generated-output drift, secret exposure, and missing proof.
- Treat native review as evidence, not authority.
- Use the current agent's native review surface for concrete reviewable diffs
  that are being approved, finalized, committed, or merged.
- Do not require native review for planning-only or no-diff decisions.
- If the question becomes what proof to add or run, use the testing workflow.
- Stop when the target, authority, diff state, or review command shape is
  unclear enough that review would be guesswork.

## Method

1. State the review decision: review now, wait, adjust scope, skip, or stop.
2. Name the target, authority, contract, and current evidence.
3. Choose the narrowest useful review boundary.
4. Name any gate that must finish before review.
5. Run or request native review only when the boundary requires it.
6. Accept, reject, or defer findings from source evidence.

## Output

Use this standalone output only when the user asks for a review decision or
when no stronger workflow output format applies. If another workflow requires a
specific format, keep that format and apply this skill to the review decision
inside it.

Standalone output:

```text
Reviewing verdict: review_now | wait_for_gate | adjust_scope | skip | stop_for_evidence
Target:
Authority:
Contract:
Current evidence:
Review boundary:
Gate:
Native review:
Rejected scope:
Next action:
```

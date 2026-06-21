---
name: commit
description: Use when coherent repo work may be ready to save, when work risks becoming a broad mixed diff, when the user asks to commit, save, checkpoint, isolate review, or write a commit message, or after validation/native review completes. Decide whether to commit now, keep working, split first, or report the commit point; then create a safe local Conventional Commit when authorized.
---

# Commit

Use this skill to keep local history small, reviewable, and recoverable. Local
commits are encouraged for coherent validated work, but staging unrelated work
is not.

## Cadence

- Prefer committing completed work before starting unrelated work.
- Commit only coherent, validated, reviewed work.
- Split independent changes before committing.
- Treat user-owned or pre-existing edits as separate work.
- If commits are not authorized or hooks block on unrelated baseline failures,
  report the commit point instead of bypassing safeguards.
- Do not push unless the user explicitly authorizes push in the current request.

## Safe Commit Flow

1. Inspect `git status --short`, staged state, and the relevant diff.
2. Decide: `commit_now`, `keep_working`, `split_first`, or
   `report_commit_point`.
3. Run validation that matches the touched contract. State only checks that ran.
4. Run native review on the narrowest reviewable target when required. Reuse
   unchanged review evidence instead of rerunning for the same diff.
5. Before staging, run:

   ```sh
   python3 "$(git rev-parse --show-toplevel)/.agents/skills/commit/scripts/status-screen.py" --repo "$(git rev-parse --show-toplevel)"
   ```

   Stop on `blocked`. On `selection_required`, ask for the recommended staging
   decision; include staged-only when staged content exists. Keep staged content
   as-is on `staged_only`. Stage all only on `safe_to_stage_all` and only when
   it matches the chosen work.
6. Stage only coherent work. Use `git add -A` only when every changed path
   belongs to that work.
7. Before committing, run:

   ```sh
   python3 "$(git rev-parse --show-toplevel)/.agents/skills/commit/scripts/staged-secret-scan.py" --repo "$(git rev-parse --show-toplevel)"
   ```

   Stop on findings or scanner failure. Do not print raw secret content.
8. Review `git diff --staged --stat` and `git diff --staged --name-status`.
   Inspect representative staged diffs when broad, rename-heavy, or multi-area.
9. Commit with a Conventional Commits header and a short body by default.
10. Re-check `git status --short`. Report the commit hash and remaining work.

## Message

Use:

```text
type(scope): lowercase imperative subject

short body explaining the change
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `perf`,
`style`, `build`.

Do not add `Co-Authored-By`, use force flags, amend by default, or bypass hooks
with `--no-verify`.

## Output

Use this standalone output only when deciding cadence without committing or when
no stronger workflow output format applies.

```text
Commit cadence: commit_now | keep_working | split_first | report_commit_point
Work:
Validation:
Review:
Unrelated changes:
Commit authorized:
Next action:
```

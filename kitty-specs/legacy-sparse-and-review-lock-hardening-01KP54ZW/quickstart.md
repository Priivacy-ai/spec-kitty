# Quickstart: Legacy Sparse-Checkout Cleanup and Review-Lock Hardening

**Mission**: `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Phase**: 1 (Design)
**Date**: 2026-04-14

This quickstart walks the four user-facing flows that this mission delivers. It is written against the interfaces and behaviours defined in `data-model.md` and `plan.md`; it doubles as the acceptance script for the success criteria in `spec.md`.

---

## Flow 1 — Detect and remediate a legacy-sparse repo

**Setup**: An upgraded repo where `git config --get core.sparseCheckout` returns `true` and `.git/info/sparse-checkout` exists. This is Kent's configuration on `kg-automation`.

```bash
spec-kitty doctor
```

Expected excerpt of output:

```
⚠ Legacy sparse-checkout state detected
  Primary: /Users/you/your-repo
    core.sparseCheckout = true
    pattern file: .git/info/sparse-checkout (42 lines)
  Lane worktrees: 2 affected
    .worktrees/feature-lane-a
    .worktrees/feature-lane-b

  Why this matters:
    spec-kitty v3.0+ removed sparse-checkout support but does not ship a
    migration. This state can cause silent data loss during mission merge
    and broken lane worktrees on agent action implement.

  Fix:
    spec-kitty doctor --fix sparse-checkout
```

Run the fix:

```bash
spec-kitty doctor --fix sparse-checkout
```

Doctor refuses on a dirty tree (FR-005). If the primary or any worktree has uncommitted tracked changes, the output is:

```
✗ Cannot remediate: uncommitted changes in:
  .worktrees/feature-lane-a (2 tracked files modified)

  Commit or stash your changes and retry:
    cd .worktrees/feature-lane-a
    git stash push -u
    spec-kitty doctor --fix sparse-checkout
```

On a clean tree, doctor prompts once (interactive TTY only) and applies the remediation:

```
Proceed? This will:
  1. git sparse-checkout disable (primary)
  2. git config --unset core.sparseCheckout (primary)
  3. rm .git/info/sparse-checkout (primary)
  4. git checkout HEAD -- . (primary)
  5. repeat steps 1–4 in .worktrees/feature-lane-a
  6. repeat steps 1–4 in .worktrees/feature-lane-b
[y/N] y

✓ Primary: remediated (4 steps, clean verify)
✓ .worktrees/feature-lane-a: remediated
✓ .worktrees/feature-lane-b: remediated
```

Verification:

```bash
git config --get core.sparseCheckout             # empty
cat .git/info/sparse-checkout                    # No such file or directory
git status --short                               # (clean)

for wt in .worktrees/*; do
  (cd "$wt" && git config --get core.sparseCheckout)  # empty each
done
```

**Non-interactive (CI) behaviour**: When `sys.stdin.isatty()` is false or a common CI env var is set, `doctor --fix sparse-checkout` exits non-zero with a one-line remediation pointer rather than prompting (FR-023).

---

## Flow 2 — Merge refuses on legacy-sparse; proceeds after remediation

**Setup**: A mission ready to merge, sparse-checkout still active.

```bash
spec-kitty agent mission merge --mission 017-example --json
```

Expected:

```
✗ Merge aborted: legacy sparse-checkout state detected

  This repository has core.sparseCheckout=true configured, which v3.0+
  spec-kitty does not handle correctly and which has caused silent data
  loss in prior mission merges (Priivacy-ai/spec-kitty#588).

  Fix:
    spec-kitty doctor --fix sparse-checkout

  If you have an intentional sparse configuration and understand the risk,
  you may pass --allow-sparse-checkout to proceed. Use of this override is
  logged at WARNING level.
```

Exit code: non-zero. No commits on the target branch. No MergeState file written.

**Power user with legitimate sparse** (FR-008, FR-009):

```bash
spec-kitty agent mission merge --mission 017-example --allow-sparse-checkout --json
```

Produces a log record (typically on stderr):

```
WARNING  spec_kitty.override.sparse_checkout command=mission-merge mission_slug=017-example mission_id=01KP54ZWEEPCC2VC3YKRX1HT8W actor=kentonium3 at=2026-04-14T05:10:02Z
```

Merge then runs. The commit-layer backstop (FR-011, C-007) remains active regardless; `--allow-sparse-checkout` does not disable it.

---

## Flow 3 — Approve / reject a WP without `--force`

**Setup**: Lane worktree review in progress. `.spec-kitty/review-lock.json` exists in the worktree, no other untracked content.

```bash
# Reviewer has finished review and is ready to approve.
spec-kitty agent tasks move-task WP02 --to approved \
  --mission 017-example \
  --note "Review passed: acceptance criteria met"
```

Expected: transition succeeds. The guard's drift scan filters `.spec-kitty/` (FR-015, C-003); the rest of the worktree is clean.

After the transition:

```bash
ls -la .worktrees/017-example-lane-a/.spec-kitty/
# No such file or directory (review lock released, dir removed when empty) — FR-018
```

**Negative case**: if the reviewer has a genuine uncommitted file alongside the lock, the guard still trips on that file (C-004):

```
Cannot move WP02 to approved

Uncommitted implementation changes in worktree!

Modified files:
  M  src/feature.py

Commit your work first:
  cd .worktrees/017-example-lane-a
  git add src/feature.py
  git commit -m "feat(WP02): finalize review fixes"

Then retry: spec-kitty agent tasks move-task WP02 --to approved
```

(Note the retry suggestion names the caller's actual target lane — `approved` — not a hardcoded `for_review`. FR-017.)

**Reject flow** (FR-019):

```bash
spec-kitty agent tasks move-task WP02 --to planned \
  --mission 017-example \
  --review-feedback-file feedback.md
```

Same filter applies; no `--force` needed when the only untracked content is `.spec-kitty/`.

---

## Flow 4 — `safe_commit` backstop prevents silent data loss

**Setup**: A scenario where `HEAD` has advanced ahead of the working tree (for any reason — external pull, missed refresh, legacy-sparse state that slipped past preflight via `--allow-sparse-checkout`). The next call into `safe_commit` would have historically swept phantom deletions into the commit.

```bash
spec-kitty agent tasks move-task WP03 --to done --mission 017-example
```

Expected when the staging area would contain unexpected paths:

```
✗ Commit aborted: staging area contains unexpected paths

  Requested paths (what safe_commit was told to commit):
    kitty-specs/017-example/status.events.jsonl
    kitty-specs/017-example/status.json

  Unexpected paths staged (would have been committed):
    D  docs/runbooks/vikunja-date-handling.md
    M  scripts/openclaw/agents/felix-admin-habits/AGENTS.md

  This usually means the working tree is behind HEAD. Investigate before
  committing:
    git diff --cached
    git status
    git checkout HEAD -- <unexpected-paths>

  The backstop cannot be bypassed by --force.
```

Exit code: non-zero. No commit produced. The user resolves the staging-area state and retries. The cascade that caused Priivacy-ai/spec-kitty#588's silent revert is closed off at the commit layer (FR-011, FR-012, C-005).

---

## Flow 5 — Recovery for users already hit (documentation-only)

**Setup**: A user whose `main` already contains a phantom-deletion commit from a pre-fix merge. Example from mission 023: commit `84bf7b6` on Kent's `main` silently reverted 243 lines across 4 files from the preceding merge commit `113d734`.

The CHANGELOG entry (FR-021) documents the recipe:

```bash
# Identify the merge commit that originally introduced the content.
git log --merges --oneline -- <affected-file>

# Restore from the merge commit.
git checkout <merge-sha> -- <affected-files...>

# Commit the restoration.
git add <affected-files...>
git commit -m "fix: restore content reverted by phantom-deletion bug (pre-fix merge)"
```

Users should run the remediation (`spec-kitty doctor --fix sparse-checkout`) before invoking another merge to prevent recurrence.

---

## Test-map summary

| Flow | Success criterion | Integration test |
|---|---|---|
| 1 | SC-001 | `tests/integration/sparse_checkout/test_remediation_primary_and_worktrees.py` |
| 2 | SC-002, SC-007 | `tests/integration/sparse_checkout/test_merge_preflight_blocks.py` + `test_merge_with_allow_override.py` |
| 3 | SC-003, SC-004, SC-007 | `tests/integration/review/test_approve_without_force.py` + `test_reject_without_force.py` |
| 4 | SC-005, SC-007 | `tests/integration/git/test_safe_commit_backstop.py` |
| 5 | SC-008 | CHANGELOG review; no code test |

All integration tests run in both "clean 3.x-born repo" and "legacy-sparse repo" fixtures (C-008).

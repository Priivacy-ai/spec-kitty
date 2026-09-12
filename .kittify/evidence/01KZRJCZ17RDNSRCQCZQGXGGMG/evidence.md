All the remaining dirty items were pre-existing at session start (not created or modified by this repair) and are runtime/coordination bookkeeping outside this task's scope — left untouched per instruction not to hand-edit runtime metadata. WP01 ownership fix is confirmed live: `owned_files` now includes `commit_helpers.py`.

## Summary

**Repair applied** (`kitty-specs/worktree-owned-root-3328-01KZRG01/`), entirely through canonical planning surfaces — no code/test edits:

1. Added `src/specify_cli/git/commit_helpers.py` to WP01 `owned_files` in `wps.yaml` and WP01 frontmatter (`tasks/WP01-checkout-ownership-primitive.md`). Confirmed via grep no other WP references or owns that file — zero new overlap.
2. `agent mission finalize-tasks --validate-only` (both before and after commit): `validation_passed`, zero ownership/dependency errors, only the pre-existing unrelated WP06 ADR-glob warning.
3. Real `agent mission finalize-tasks` regenerated `lanes.json` (WP01/`lane-a` `write_scope` now includes `commit_helpers.py`), `tasks.md`, WP prompt files — commit `cbc679341`.
4. `spec-commit` landed the `wps.yaml` ownership edit — commit `867911ad9`.
5. (Housekeeping, required to clear the pre-existing `DIRTY_WORKTREE` guard blocking `record-analysis`) committed two leftover uncommitted Op-evidence records from prior closed invocations — commit `b3560eef5`.
6. Re-ran the analyze template against spec/plan/tasks, persisted via `agent mission record-analysis` — commit `ab497647f`. Verdict: **`ready`**, 1 LOW finding (the repair itself, marked RESOLVED), 0 critical/high.
7. `next --mission worktree-owned-root-3328-01KZRG01 --json`: `mission_state: "implement"`, `wp_id: "WP01"`, `guard_failures: []` — WP01 is planned and implementable with zero guards.

**New planning HEAD SHA**: `ab497647f` (on `fix/worktree-owned-root-3328-v2`), preceded by `867911ad9` (ownership fix) and `cbc679341`/`b3560eef5` (metadata regen / housekeeping).

**Remaining working-tree state**: pre-existing, untouched by this repair — `meta.json` (vcs-lock fields modified before this session started), and untracked `kitty-ops/*.jsonl`, `status.events.jsonl`, `status.json`, `review-cycle-1.md` (runtime/coordination bookkeeping — left alone per "do not hand-edit runtime metadata").

**First next action**: `spec-kitty agent action implement WP01 --agent <name>` — not executed here; planning/repair scope only, no merge-to-lane-a performed.

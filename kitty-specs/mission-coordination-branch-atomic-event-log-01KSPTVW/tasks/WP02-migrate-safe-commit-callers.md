---
work_package_id: WP02
title: Migrate existing safe_commit() callers across the codebase
dependencies:
- WP01
requirement_refs:
- FR-013
- FR-031
- NFR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW
base_commit: fc1aa41f62840ca1fa430e2d8fc372f384fc5421
created_at: '2026-05-28T10:30:25.979225+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-rita:reviewer"
shell_pid: "4471"
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 1 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/safe_commit.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/safe_commit.py
- src/specify_cli/cli/commands/charter/**
- src/specify_cli/upgrade/**
- src/specify_cli/cli/commands/agent/recovery.py
- src/specify_cli/glossary/**
- tests/specify_cli/cli/commands/test_safe_commit_cli.py
- tests/specify_cli/charter/**
- tests/specify_cli/upgrade/**
- tests/specify_cli/glossary/**
- docs/CHANGELOG.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

After WP01 lands, `safe_commit()` requires `destination_ref` as a keyword-only argument. The codebase will not compile until **every** existing caller is migrated — including workflow callers (`implement.py`, `workflow.py`, `emit.py`, `mission.py` finalize-tasks site). This WP performs the **mechanical migration only**: every existing `safe_commit()` call gains `destination_ref=current_branch` (and `worktree_root=repo_root`). The full semantic replacement of workflow callers with `BookkeepingTransaction` happens in WP06.

**Critical clarification (cross-review correction)**: An earlier draft of this WP claimed workflow callers could be "deferred to WP06." That was incorrect: deferring them leaves the codebase uncompilable after WP01 lands. WP02 must touch every call site WP01 broke. WP06 then refactors the workflow ones (which are currently `safe_commit(destination_ref=current_branch)`) to instead go through `BookkeepingTransaction` (whose internal `safe_commit()` call passes `destination_ref=coordination_branch`). WP06 owns the four workflow files; WP02 owns the rest. This split is enforceable because the ownership lists don't overlap.

The public `spec-kitty safe-commit` CLI gains a required `--to-branch` flag with a CLI-only deprecation env var to ease external-script rollout.

## Context

**Spec source**: FR-031 (caller migration), FR-013 (cleanup follow-through), NFR-007 (error code stability)
**Contract**: `contracts/safe_commit_signature.md` § "CLI surface change" describes the deprecation path.
**Predecessor WP**: WP01 — read its DoD before starting; the new signature is what you're migrating to.

The migration is **mostly mechanical**: every existing call site already knows what branch it commits to (it's the current branch). Just thread that value through as `destination_ref`. The risk is missing a call site; the structural enforcement (mypy --strict + the HEAD assertion) catches anything missed but it's better to be exhaustive in this WP.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Same lane as WP01 (sequential within PR 1). The lane allocator will reuse the lane if you opt-in via the existing lane policy.

---

## Subtask T006: Audit every `safe_commit()` call site

**Purpose**: Produce a complete migration manifest before touching any code. Catches surprises (call sites in places you didn't expect).

**Steps**:
1. From the repo root, run:
   ```bash
   grep -rn 'safe_commit(' src/ tests/ --include='*.py' > /tmp/safe-commit-callers.txt
   ```
2. Categorize each hit:
   - **Workflow callers** (`implement.py`, `workflow.py`, `emit.py`, `mission.py` finalize-tasks site) — these four files are owned by **WP06**. WP06's first subtasks include the mechanical `destination_ref=current_branch` migration AS PART of the transaction-refactor work. **WP02 does NOT touch these four files.** This is enforced by `owned_files` non-overlap.
   - **CLI command**: `cli/commands/safe_commit.py` (the user-facing `spec-kitty safe-commit`) — owned by WP02.
   - **Other callers**: charter sync, upgrade migrations, decision-thread tracking, glossary curation, recovery commits — owned by WP02.
   - **Tests**: any test file that calls `safe_commit` directly. Owned by WP02 unless they're test files paired with WP06's workflow files.

3. **Build-coherence note**: PR 1 (WP01 alone) does not ship a buildable codebase — the workflow files still have unmigrated `safe_commit()` calls and fail mypy. The minimum buildable cut is WP01+WP02+WP06 (PR 1 + the workflow file portion of PR 2). The cross-review correctly flagged this. The PR boundaries are not strict shippable boundaries; they're sequencing guidance. The lane allocator assigns separate lanes by dependency; the codebase becomes coherent again at the WP06 merge point.
3. Write the manifest to `kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW/research/safe-commit-caller-manifest.md` (create the `research/` subdirectory if it doesn't exist; the artifact_dirs include it). Format:
   ```markdown
   | File:Line | Category | Current branch source | Migration action |
   ```

**Files**:
- New: `kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW/research/safe-commit-caller-manifest.md`

**Validation**:
- [ ] Manifest exists and covers every grep hit.
- [ ] Each entry is categorized; workflow callers are explicitly marked "DEFERRED TO WP06".
- [ ] Total count of non-workflow callers is recorded for tracking progress in T008.

## Subtask T007: Update `spec-kitty safe-commit` CLI

**Purpose**: The CLI command is the externally visible surface. After WP01, the underlying helper requires `destination_ref`. The CLI must require `--to-branch` (or use a deprecation path).

**Steps**:
1. In `src/specify_cli/cli/commands/safe_commit.py` (or wherever the CLI is registered), add the `--to-branch <ref>` option. Make it required UNLESS the deprecation env var is set.
2. Behavior matrix:
   - `--to-branch X` provided → pass `destination_ref=X` to `safe_commit()`.
   - `--to-branch` missing AND `SPEC_KITTY_INFER_DESTINATION_REF=1` env var set → resolve via existing branch-context resolver (`spec-kitty agent mission branch-context --json` style — use the Python helper directly); print one-line stderr deprecation: `"warning: --to-branch will be required in v3.3; set explicitly or unset SPEC_KITTY_INFER_DESTINATION_REF"`. Pass resolved value as `destination_ref`.
   - `--to-branch` missing AND env var NOT set → exit non-zero with `SAFE_COMMIT_HEAD_MISMATCH` (or a clearer "missing --to-branch" message that names the env var as an escape hatch).
3. The CLI must also resolve and pass `worktree_root` — typically `repo_root` for the CLI's case (the current working directory is the primary checkout).
4. Update the command's help text to describe `--to-branch` and the deprecation env var.

**Files**:
- `src/specify_cli/cli/commands/safe_commit.py`

**Validation**:
- [ ] `spec-kitty safe-commit --help` shows `--to-branch <ref>` as required.
- [ ] Passing `--to-branch main <message> <paths>` works.
- [ ] Omitting `--to-branch` without env var exits non-zero with a clear message.
- [ ] Omitting `--to-branch` WITH `SPEC_KITTY_INFER_DESTINATION_REF=1` emits a stderr deprecation and proceeds.

## Subtask T008: Migrate non-workflow callers

**Purpose**: Update every non-workflow `safe_commit()` call site to pass `destination_ref` explicitly. Most call sites already know the branch (they computed it for protection checks or logging); just thread it through.

**Steps**:
1. Iterate through the manifest from T006, skipping workflow callers.
2. For each non-workflow caller, determine `destination_ref`:
   - If the caller already resolves the current branch (common pattern: `current_branch = get_current_branch(repo_root)`), pass that as `destination_ref`.
   - If the caller is inside an upgrade migration, pass the upgrade target branch.
   - If the caller is inside a charter command, pass the current checkout branch (charter writes are operator-driven, so current branch is correct).
   - If the caller is in a test, use the test fixture's branch (typically `main` in a tmp repo).
3. For each caller, also pass `worktree_root` — typically the same as `repo_root` for non-worktree callers.
4. After migrating, run `mypy --strict <file>` and verify it passes.
5. Update the manifest to mark each entry "migrated".

**Files** (representative; the manifest from T006 is authoritative):
- `src/specify_cli/cli/commands/charter/sync.py`
- `src/specify_cli/cli/commands/charter/interview.py`
- `src/specify_cli/upgrade/migrations/*.py` (any that commit)
- `src/specify_cli/cli/commands/agent/decisions.py`
- `src/specify_cli/cli/commands/agent/recovery.py`
- `src/specify_cli/glossary/cli.py`

**Validation**:
- [ ] `mypy --strict src/` passes (catches any caller missed).
- [ ] Every non-workflow caller in the manifest has been marked migrated.
- [ ] Tests for migrated callers still pass.

## Subtask T009: Integration tests for `safe-commit` CLI

**Purpose**: Verify the CLI's three modes (--to-branch, deprecation env var, refusal) end-to-end.

**Steps**:
1. Create or extend `tests/specify_cli/cli/commands/test_safe_commit_cli.py`:
   - `test_cli_with_to_branch()` — happy path; `--to-branch main` succeeds in a tmp repo on `main`.
   - `test_cli_without_to_branch_fails()` — no `--to-branch`, no env var → CLI exits non-zero with clear message.
   - `test_cli_deprecation_env_var()` — `SPEC_KITTY_INFER_DESTINATION_REF=1`, no `--to-branch` → succeeds with stderr deprecation notice.
   - `test_cli_head_mismatch()` — `--to-branch some-other-branch` while on `main` → exits non-zero with `SAFE_COMMIT_HEAD_MISMATCH`.
2. Use the existing CLI test harness (`CliRunner` from typer's testing module, or whatever pattern the project uses).

**Files**:
- `tests/specify_cli/cli/commands/test_safe_commit_cli.py`

**Validation**:
- [ ] All four CLI tests pass.
- [ ] Deprecation notice is on stderr (not stdout) so it doesn't break scripted parsing of stdout.

## Subtask T010: Update tests for migrated callers; final sweep

**Purpose**: Catch any caller missed by T008. Ensure the entire test suite passes after migration.

**Steps**:
1. Run `pytest tests/` and triage any failures.
2. For any test that fails because it called `safe_commit()` without `destination_ref`, migrate it the same way as production callers (pass the test fixture's branch as `destination_ref`).
3. Run `mypy --strict src/ tests/` and fix any remaining missing-arg errors.
4. Update the manifest one final time: every entry should be marked migrated.
5. Verify zero entries in the manifest remain as "DEFERRED TO WP06" — actually, those should stay deferred; this is the only OK exception. Confirm those entries are still in their unmigrated state (workflow callers ARE intentionally not migrated yet).

**Files**: every test file touched by the previous subtasks; the manifest file.

**Validation**:
- [ ] `pytest tests/` passes (full suite).
- [ ] `mypy --strict src/ tests/` passes with zero errors EXCEPT for the workflow callers deferred to WP06.
- [ ] Manifest is complete and accurate.

---

## Definition of Done

- [ ] All 5 subtasks complete (T006..T010).
- [ ] `pytest tests/` passes.
- [ ] `mypy --strict src/ tests/` reports errors ONLY in workflow files explicitly deferred to WP06.
- [ ] Manifest at `research/safe-commit-caller-manifest.md` is complete.
- [ ] `spec-kitty safe-commit` CLI tests cover all three modes.
- [ ] CHANGELOG entry from WP01 is updated (or this WP adds its own) to note the CLI's `--to-branch` requirement.

After this WP lands, **PR 1 is complete and shippable**. The structural invariant is in place; future callers cannot silently drift.

## Risks

- **Missed callers**: mypy + tests catch them. If something slips through and is exercised at runtime, the HEAD assertion catches it loudly (with a structured error pointing at the missing parameter).
- **Tests in unusual locations**: integration tests under `tests/integration/`, end-to-end tests under `tests/e2e/`. Audit those too.
- **The deprecation env var**: must be documented with a removal timeline (next minor release after PR 1 lands).

## Reviewer guidance

When reviewing this WP, focus on:
1. **Manifest completeness**: does the manifest cover every `grep -rn 'safe_commit('` hit?
2. **Workflow callers are deferred**: confirm `implement.py`, `workflow.py`, `emit.py`, and `mission.py` finalize-tasks site are explicitly marked "DEFERRED TO WP06" in the manifest and that mypy strict still fails there (will be fixed in WP06).
3. **CLI deprecation UX**: is the warning helpful? Does it name the removal timeline?
4. **No new exceptions**: confirm this WP does NOT add new entries to `_PROTECTED_BRANCH_COMMIT_EXCEPTIONS`.
5. **Test coverage**: are all four CLI modes covered? Are migrated non-workflow callers exercised?

## References

- Spec: FR-031 (caller migration), FR-013, NFR-007
- Plan: PR 1 step 2
- Contract: [`contracts/safe_commit_signature.md`](../contracts/safe_commit_signature.md) § "CLI surface change"
- Research: R-002, R-005 in [`research.md`](../research.md)

## Activity Log

- 2026-05-28T10:30:26Z – claude:opus:implementer-ivan:implementer – shell_pid=95548 – Assigned agent via action command
- 2026-05-28T10:43:06Z – claude:opus:implementer-ivan:implementer – shell_pid=95548 – WP02 ready for review: spec-kitty safe-commit CLI migrated to destination_ref signature with --to-branch required + SPEC_KITTY_INFER_DESTINATION_REF=1 deprecation env var; 4 new CLI tests pass; manifest on main covers all 17 production callers. Workflow files (implement.py/workflow.py/emit.py/mission.py) deferred to WP06.
- 2026-05-28T10:44:18Z – claude:opus:reviewer-rita:reviewer – shell_pid=4471 – Started review via action command
- 2026-05-28T10:47:25Z – claude:opus:reviewer-rita:reviewer – shell_pid=4471 – Review passed: CLI migrated with --to-branch required + deprecation env var, 4 new CLI tests + 4 existing tests pass, mypy --strict clean on owned files; workflow files (implement.py/workflow.py/emit.py/mission.py) correctly left for WP06; three caveats accepted as pragmatic and consistent with the bug being fixed.

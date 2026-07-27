---
work_package_id: WP07
title: Governance / Context / Branch Guard Hygiene
dependencies: []
requirement_refs:
- FR-032
- FR-033
- FR-034
- FR-035
- FR-036
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
agent: "claude:opus-4-7:reviewer:reviewer"
shell_pid: "28282"
history:
- at: 2026-04-26T07:36:00Z
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks
authoritative_surface: src/specify_cli/charter/
execution_mode: code_change
mission_id: 01KQ4ARB0P4SFB0KCDMVZ6BXC8
mission_slug: stability-and-hygiene-hardening-2026-04-01KQ4ARB
owned_files:
- src/specify_cli/charter/context.py
- src/specify_cli/charter/compact.py
- src/specify_cli/cli/commands/specify.py
- src/specify_cli/cli/commands/plan.py
- src/specify_cli/cli/commands/tasks.py
- src/specify_cli/cli/commands/_branch_strategy_gate.py
- src/specify_cli/workspace/assert_initialized.py
- src/specify_cli/missions/_legacy_aliases.py
- tests/contract/test_charter_compact_includes_section_anchors.py
- tests/integration/test_fail_loud_uninitialized_repo.py
- tests/integration/test_branch_strategy_gate.py
- tests/integration/test_legacy_feature_alias.py
- tests/integration/test_post_merge_custom_mission_loader.py
tags: []
---

# WP07 — Governance / Context / Branch Guard Hygiene

## Objective

Spec ceremony fails loudly outside an initialized repo. PR-bound missions
do not start on `merge_target_branch` without an explicit gate. Charter
compact mode preserves directive IDs and section anchors. Legacy
`--feature` aliases remain accepted but hidden. Local custom mission
loader post-merge hygiene is audited; either fixed in this WP or scoped
to a precise follow-up.

## Context

These are operator-facing hygiene fixes that prevent silent surprises.
Decisions in `research.md` D13, D14, D15, D16, D17.

## Branch strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Lane workspace**: assigned by `finalize-tasks`. Use
  `spec-kitty agent action implement WP07 --agent <name>`.

## Subtasks

### T039 — Fail-loud uninitialized repo

**Purpose**: Spec / plan / tasks commands never silently fall back to
another repo.

**Steps**:

1. Add `src/specify_cli/workspace/assert_initialized.py:assert_initialized(root: Path) -> None`:
   - Resolves canonical root via WP03's resolver.
   - Asserts `<root>/.kittify/config.yaml` and `<root>/kitty-specs/` exist.
   - On failure, raises `SpecKittyNotInitialized` with the resolved
     root path and an actionable message.
2. Call `assert_initialized()` at the top of `specify`, `plan`, and
   `tasks` Typer commands in `src/specify_cli/cli/commands/`.
3. Remove any code path that silently falls back to a parent / sibling
   initialized repo.
4. Add `tests/integration/test_fail_loud_uninitialized_repo.py`:
   - Build a temp tree without `.kittify/`.
   - Run each of `spec-kitty specify`, `plan`, `tasks` (via
     subprocess or CliRunner) and assert non-zero exit.
   - Assert no files written outside the temp tree (snapshot the file
     listing of a known sibling-initialized repo before / after).

**Validation**:
- Test passes.
- Manual test: `cd /tmp/empty/; spec-kitty specify` exits with the
  structured error.

### T040 — Branch-strategy gate for PR-bound missions

**Purpose**: Don't start a PR-bound mission on `main` without a prompt.

**Steps**:

1. In meta.json schema, add optional `pr_bound: bool` (default false).
2. Add `src/specify_cli/cli/commands/_branch_strategy_gate.py`:
   - On `mission create`, if CWD branch == `merge_target_branch` AND
     `pr_bound is True`, prompt the operator to confirm or to switch
     to a feature branch.
   - Suppress prompt when `--branch-strategy already-confirmed`.
3. Wire the gate into `mission create` in
   `src/specify_cli/cli/commands/specify.py` (or wherever
   `mission create` lives).
4. Add `tests/integration/test_branch_strategy_gate.py`:
   - PR-bound mission, on `main`, no flag → prompt fires (assert via
     CliRunner stdin/stdout).
   - PR-bound mission, on `main`, `--branch-strategy already-confirmed`
     → no prompt, mission created.
   - Non-PR-bound mission on `main` → no prompt (preserves existing
     flow).

**Validation**:
- Test passes.
- Existing non-PR-bound flows continue without prompt.

### T041 — Charter compact mode preserves directive IDs + section anchors

**Purpose**: Compact view does not shed required governance content.

**Steps**:

1. In `src/specify_cli/charter/compact.py` (or the equivalent compact
   renderer in `src/specify_cli/charter/context.py`), update the
   compact view to include:
   - Every directive ID (e.g., `DIRECTIVE_003`) verbatim.
   - Every tactic ID.
   - A "Section Anchors" block listing every charter section heading
     that bootstrap mode would include.
2. The body prose for each directive may be collapsed in compact
   mode — the IDs and anchors must not.
3. Add `tests/contract/test_charter_compact_includes_section_anchors.py`:
   - Load each fixture charter under
     `tests/fixtures/charters/`.
   - Render bootstrap and compact views.
   - Assert: `set(directive_ids(compact)) == set(directive_ids(bootstrap))`,
     `set(tactic_ids(compact)) == set(tactic_ids(bootstrap))`,
     `set(section_anchors(compact)) == set(section_anchors(bootstrap))`.

**Validation**:
- Test passes for all fixture charters.
- Smoke check: compact view token count is still meaningfully smaller
  than bootstrap (e.g., < 50% — measure with token estimator).

### T042 — Hide legacy `--feature` aliases

**Purpose**: Legacy alias remains accepted; help output shows only
`--mission`.

**Steps**:

1. Add `src/specify_cli/missions/_legacy_aliases.py` exporting a
   helper to attach `--feature` as a hidden Typer option that mirrors
   `--mission`.
2. For each Typer command that previously accepted `--feature`, mark
   the option as `hidden=True` and ensure both flags reach the same
   handler argument.
3. Add `tests/integration/test_legacy_feature_alias.py`:
   - For each command, run with `--feature <slug>`; assert it works.
   - Run `<command> --help`; assert `--feature` does NOT appear in
     output but `--mission` does.

**Validation**:
- Test passes for the canonical command set.

### T043 — Local custom mission loader post-merge audit

**Purpose**: Resolve issue #801. Either fix in this WP or document a
precise follow-up.

**Steps**:

1. Read the post-merge code path that handles the local custom mission
   loader (likely in `src/specify_cli/merge/` and
   `src/specify_cli/missions/`).
2. Verdict criteria:
   - **Fixed**: Cleanup is incomplete on `main`. Fix it; add
     `tests/integration/test_post_merge_custom_mission_loader.py`
     that asserts a custom mission loader does not leak after merge.
   - **Verified-already-fixed**: Cleanup is complete on `main`. Add
     the same regression test that would have failed pre-fix and pass.
   - **Deferred-with-followup**: Cleanup is partial and the remainder
     is out of scope. Document the gap in
     `research.md` (extend D17) and file a narrow follow-up issue.
3. Record the verdict and evidence in WP08's `issue-matrix.md`.

**Validation**:
- The verdict is one of the three with a referenceable artifact.
- If `fixed` or `verified-already-fixed`, the regression test passes.

## Definition of Done

- All five subtasks complete with listed validation passing.
- `pytest tests/contract/test_charter_compact_includes_section_anchors.py`
  green.
- `pytest tests/integration/ -k 'fail_loud or branch_strategy_gate or legacy_feature_alias or post_merge_custom_mission_loader'`
  green.
- T043 verdict recorded in WP08's matrix.

## Risks

- T039's fail-loud may break scripted / CI invocations that ran in a
  parent-init context. Document the `--repo-root` hint and migration
  in `docs/migration/` if needed.
- T041 compact-view fix must not bloat the compact view back to
  bootstrap size. Measure token count delta and document.
- T040 prompt behavior must be deterministic in tests; use CliRunner
  with `input=` rather than tty hacks.

## Reviewer guidance

1. T039: run `spec-kitty specify ...` from a non-init directory;
   should fail loud. Run from a sibling-init directory; should ALSO
   fail loud (no fallback).
2. T040: the gate must accept the suppression flag; without it, the
   prompt must appear. Check both stdin paths in the test.
3. T041: open a fixture charter, render both modes, eyeball the
   directive ID list. The set comparisons in the test are the
   contract; the eyeball check is just a sanity step.
4. T043: the verdict must be one of three; "we'll fix this later" is
   not a verdict, that maps to `deferred-with-followup` with an open
   issue.

## Activity Log

- 2026-04-26T09:32:49Z – claude:opus-4-7:implementer:implementer – shell_pid=23967 – Started implementation via action command
- 2026-04-26T09:47:02Z – claude:opus-4-7:implementer:implementer – shell_pid=23967 – WP07 ready: T039 fail-loud assert_initialized; T040 PR-bound branch-strategy gate with already-confirmed bypass; T041 compact charter preserves directive/tactic IDs + section anchors; T042 charter.py --feature now hidden, terminology-guards green; T043 verdict verified-already-fixed (RuntimeContractRegistry snapshot/restore) with regression test pinned
- 2026-04-26T09:47:39Z – claude:opus-4-7:reviewer:reviewer – shell_pid=28282 – Started review via action command
- 2026-04-26T09:50:50Z – claude:opus-4-7:reviewer:reviewer – shell_pid=28282 – Review passed: 5/5 subtasks (4 fixed + T043 verified-already-fixed). Terminology-guards test GREEN; charter compact preserves directive IDs and section anchors; assert_initialized wired into lifecycle.{specify,plan,tasks}; PR-bound branch-strategy gate fires correctly. Out-of-owned-files edits limited to lifecycle.py, agent/mission.py, charter.py, charter/context.py — each justified per WP reviewer guidance. Hard gates 313 passed, 1 skipped.

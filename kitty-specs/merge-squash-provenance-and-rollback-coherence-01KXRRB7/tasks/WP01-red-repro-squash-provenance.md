---
work_package_id: WP01
title: 'Red-first repro: squash clobbers target-newer provenance (#2709)'
dependencies: []
requirement_refs:
- FR-001
tracker_refs:
- '2709'
planning_base_branch: fix/red-handling-policy-and-drg-regression-marks
merge_target_branch: fix/red-handling-policy-and-drg-regression-marks
branch_strategy: Planning artifacts for this mission were generated on fix/red-handling-policy-and-drg-regression-marks. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/red-handling-policy-and-drg-regression-marks unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-merge-squash-provenance-and-rollback-coherence-01KXRRB7
base_commit: 20d5ec9c46146a47fd987af1ceaf6ccf0772f9ba
created_at: '2026-07-17T21:18:42.387322+00:00'
subtasks:
- T001
- T002
phase: Phase 1 - Red-first (#2709 chain)
assignee: ''
agent: "claude"
shell_pid: '3350592'
shell_pid_created_at: '1784323111.43'
history:
- timestamp: '2026-07-17T20:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/regression/
create_intent:
- tests/regression/test_issue_2709_squash_provenance.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/regression/test_issue_2709_squash_provenance.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Red-first repro: squash clobbers target-newer provenance (#2709)

## Objective
Author a committed **failing** reproduction that witnesses #2709: the supported squash
merge overwrites target-newer `meta.json` acceptance/VCS fields and `traces/*.md` with older
mission-branch copies. RED on the mission base **for the right reason** (first failing
assertion is a provenance field, not a fixture error — SC-001). This is the root of the
#2709 chain; author no production fix here.

## Red-first ATDD (this WP is test-only)
- File: `tests/regression/test_issue_2709_squash_provenance.py`, `pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]`.
- Entry point: the real `_run_lane_based_merge` (`from specify_cli.cli.commands.merge import _run_lane_based_merge`), strategy `MergeStrategy.SQUASH`.
- Harness: reuse `tests/specify_cli/cli/commands/test_merge_coord_topology_1772.py` helpers (`_init_git_repo`, `_bootstrap_coord_mission`, `_write_meta`, `_write_manifest`, `_file_on_branch`, `_real_merge_external_mocks`, `_git`).

## Acceptance criteria (FR-001, SC-001, US1-S1, US2-S1)
1. **Binding both-sides divergence:** `meta.json` is modified on **both** the coord branch
   (older acceptance v1 at T1) **and** target `main` (newer acceptance v2 at T2), so
   `git merge --squash -X theirs` genuinely conflicts. Use `mission_metadata.record_acceptance`
   / `set_vcs_lock` per branch; monkeypatch `mission_metadata._now_iso` for deterministic
   T1 < T2. (Without both-sides divergence git trivially keeps target → green-on-base, proves nothing.)
2. Assert on `git show main:kitty-specs/<slug>/meta.json` that target-newer
   `accepted_at==T2`, `accepted_by`, `accepted_from_commit`, `acceptance_mode`, `accept_commit`,
   `len(acceptance_history)==2`, `vcs`/`vcs_locked_at` all survive — **RED today**.
3. A second assertion covers a target-newer `traces/*.md` section surviving — **RED today**.
4. **RED-for-the-right-reason:** the first failing assertion must be a provenance field, not setup.

## Validation
- `PWHEADLESS=1 uv run pytest tests/regression/test_issue_2709_squash_provenance.py -n0 -q` → expect FAIL on the contract assertion.
- Confirm the test is GREEN if run against a hypothetical fixed tree only (do not fix here).

## Ownership
Owns ONLY `tests/regression/test_issue_2709_squash_provenance.py`. Import the 1772 harness
helpers **read-only**; add any per-branch-acceptance helpers **inside this test module** (do
NOT edit `test_merge_coord_topology_1772.py` in place — WP02 also uses it, and in-place edits
create an ownership collision). Do not touch production `src/`.

## Notes
Rebase-first (C-003); re-resolve any cited symbol. No new resolvers/path grammars — reuse harness primitives.

## Activity Log

- 2026-07-18T05:48:54Z – claude – shell_pid=3350592 – Moved to for_review
- 2026-07-18T05:56:31Z – claude – shell_pid=3350592 – reviewer-renata APPROVE: non-vacuous both-sides-divergence red; real -X theirs; scope-clean.

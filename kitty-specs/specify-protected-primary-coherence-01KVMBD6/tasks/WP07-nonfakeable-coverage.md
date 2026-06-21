---
work_package_id: WP07
title: Non-fakeable acceptance & regression coverage
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-006
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: fix/specify-protected-primary-coherence
merge_target_branch: fix/specify-protected-primary-coherence
branch_strategy: Planning artifacts for this mission were generated on fix/specify-protected-primary-coherence. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/specify-protected-primary-coherence unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
phase: Phase 5 - Coverage
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3208371"
history:
- timestamp: '2026-06-21T06:45:34Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_protected_primary_spec_commit.py
- tests/git/test_protection_config_honoring.py
execution_mode: code_change
mission_id: 01KVMBD6HTBP3A9Y5T4EQ80RA9
owned_files:
- tests/integration/test_protected_primary_spec_commit.py
- tests/git/test_protection_config_honoring.py
- tests/mission_runtime/test_read_path_create_window_invariant.py
role: implementer
tags: []
wp_code: WP07
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Objective

Prove the fix with assertions that **fail if the materialization is removed** (the anti-fakeable core).
Cover SC-001..005 and NFR-001..004 + FR-006. Reuse the existing `tests/git/protected_target_fixtures.py::ProtectedTargetRepo`
(hermetic `tmp_path`, no remote, no network) — these are parallel-safe; do NOT request an `-n0` lane.

## Context & Constraints

- No new pytest markers, no new CI job (reuse `integration`/`git_repo`/`regression`/`unit`/`timing`).
- Precedent for the e2e shape: `tests/specify_cli/cli/commands/agent/test_sc6_planning_placement_e2e.py`.
- The NEGATIVE assertions are the point: a test that only asserts "exit 0" is fakeable.

## Subtasks & Detailed Guidance

### Subtask T022 — e2e kentonium3 repro + NEGATIVE assertions (SC-001)
- `tests/integration/test_protected_primary_spec_commit.py` (markers `integration`, `git_repo`, `regression`):
  on a `main`-protected `ProtectedTargetRepo`, run the full sanctioned flow (branch-context → create →
  author spec → new spec-commit entrypoint). Assert: spec.md is on `kitty/mission-<slug>`; the primary tree
  is clean; `.worktrees/<slug>-<mid8>-coord/` was created **by the command** (not pre-seeded); **zero**
  `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`; **zero** manual git. Add a variant that stubs the materializer
  and asserts the test FAILS (proving the assertion is load-bearing).
- **Files**: `tests/integration/test_protected_primary_spec_commit.py`.

### Subtask T023 — 3 sibling-site repros (record-analysis = WP02; accept/acceptance = WP04)
- Each sibling on a protected primary now materializes-then-retries. Add e2e assertions mirroring T022 for
  each — **including the same negative variant** (stub the materializer ⇒ the test FAILS); an exit-0 +
  path-exists check is fakeable (Renata). Parametrize one negative fixture across all four sites.
- Extend the NFR-003 boundary-read spy (WP03 T013) to cover at least one **sibling** path
  (`assert_not_protected_branch`-routed), so a per-call re-read at `commit_helpers.py:527` cannot hide green.
- **Files**: same module (parametrized) or sibling.

### Subtask T024 — US2 config-honoring (SC-002)
- `tests/git/test_protection_config_honoring.py`: with `protection.protected_branches: []` the spec commit
  lands directly on `main` (no worktree); with the primary protected it routes to the worktree. No code change.
- **Files**: `tests/git/test_protection_config_honoring.py`.

### Subtask T025 — FR-006 hatch + extend #1718 invariant (NFR-001)
- Hatch active ⇒ `is_protected` False end-to-end (commit lands directly).
- EXTEND `tests/mission_runtime/test_read_path_create_window_invariant.py`: during create→first-write the
  read resolves to primary; materialization triggers only at the commit boundary (do NOT fork a new file).
- **Files**: `tests/git/test_protection_config_honoring.py`, `tests/mission_runtime/test_read_path_create_window_invariant.py`.

### Subtask T026 — NFR-004 byte-identical + NFR-002 bound
- NFR-004 (CONCRETE): assert `ProtectionPolicy.resolve(repo_root).protected_branches` for a no-config repo
  equals the pre-change `protected_branches()` output (`{main, master}` ∪ remote-default) — exact set equality,
  not just "behavior unchanged".
- NFR-002: materialization completes within the bound (< 2 s warm, 0 network) — assert observed or gate with
  `@pytest.mark.timing` (do not wall-clock in the parallel shard).
- **Files**: `tests/git/test_protection_config_honoring.py`.

## Branch Strategy
- Planning base / merge target: `fix/specify-protected-primary-coherence`. Work in this WP's lane worktree.

## Definition of Done
- e2e + sibling + config-honoring + hatch + #1718 + NFR-004/002 coverage green; the negative-assertion
  variant fails when materialization is stubbed. ruff + mypy clean.

## Risks & Reviewer Guidance
- Reviewer: confirm the e2e creates the worktree via the COMMAND (not the fixture) and asserts the spec is on
  the coord branch — the load-bearing anti-fakeable checks. Confirm parallel-safety (no `-n0`).

## Activity Log

- 2026-06-21T10:49:38Z – claude:sonnet:python-pedro:implementer – shell_pid=3181803 – Assigned agent via action command
- 2026-06-21T11:13:27Z – claude:sonnet:python-pedro:implementer – shell_pid=3181803 – WP07 (lane-g): non-fakeable coverage — e2e + 3 siblings + config-honoring + hatch + #1718 + NFR-003/004; negative variants RED-verified; 27 passed
- 2026-06-21T11:13:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=3208371 – Started review via action command
- 2026-06-21T11:21:45Z – user – shell_pid=3208371 – Review passed cycle-2 (reviewer-renata): negative variants mutation-verified RED; B1/N2 fixed; 27 green

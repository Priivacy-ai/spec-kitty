---
work_package_id: WP01
title: Session reaper + mask retirement + pollution assertion
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-004
- FR-006
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: fix/session-reaper-and-tmp-leak-hygiene
merge_target_branch: fix/session-reaper-and-tmp-leak-hygiene
branch_strategy: Planning artifacts for this mission were generated on fix/session-reaper-and-tmp-leak-hygiene. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/session-reaper-and-tmp-leak-hygiene unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude"
shell_pid: "802476"
history:
- 'Created by planner for #1842 tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/test_session_reaper.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/conftest.py
- .gitignore
- tests/architectural/test_session_reaper.py
role: implementer
tags: []
task_type: implement
---

# WP01 – Session reaper + mask retirement + pollution assertion

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001/002/004, NFR-001/002, C-001/002) + `plan.md` (IC-01) + `tests/e2e/conftest.py` (`capture_source_pollution_baseline`/`assert_no_source_pollution` — reuse the *concept*, not the deep inventory).

## Objective
Add a controller-gated `pytest_sessionfinish` **snapshot-delta** reaper to root `tests/conftest.py` that self-heals all test-created REPO_ROOT + `/tmp` residue, retires the `.gitignore` `test-feature-*` masks, and makes a leak regression visible.

## Changes
- **T006** — `pytest_sessionstart`: snapshot a **narrow name-pattern list** (NOT a deep `rglob` mtime inventory — C-001): existing `kitty-specs/test-feature-*` + `*-123-test-feature` + `*golden-path-demo*` dirs, `git branch --list 'kitty/mission-test-feature-*' 'kitty/*golden-path*'`, `.worktrees/*` entries. Stash on `session.config` (or a module global keyed to the session).
- **T007** — `pytest_sessionfinish`, **controller-gated** (`session.config.workerinput is None` — mirror `conftest.py`'s existing master check): reap only the **delta** (present at finish, absent at start) matching those patterns — `rmtree` the dirs, `git branch -D` the branches, and for worktrees `git worktree prune` THEN `rmtree` any `.worktrees/*` absent from `git worktree list --porcelain` (git-unregistered husks). Never touch pre-existing entries (NFR-002).
- **T008** — `/tmp` sweep of the current run only: import WP02's shared temp-namespace root and `rmtree` this run's prompt residue under it, plus `/tmp/spec-kitty-test-homes/<run_uid>/` (N1 — the `_worker_home_base` root; key on the current run's uid, not a blanket wipe).
- **T009** — remove `.gitignore` lines 143-144 (`kitty-specs/test-feature-*`, `kitty-specs/*-123-test-feature`); add a **reap-then-assert** pollution check that reds if the reaped delta was non-empty (so a leak surfaces instead of hiding under the mask).
- **T010** — `tests/architectural/test_session_reaper.py`: seed a `test-feature-*` dir + branch + a git-unregistered `.worktrees/` husk → the reaper removes exactly those; a pre-existing tracked mission + real branch + registered worktree are NOT touched (both directions, mutation-checkable); the pollution assertion reds on a seeded leak, green otherwise.

## Red-first / DoD
- [ ] Reaper controller-gated (workers never delete shared REPO_ROOT); snapshot-delta proven to preserve pre-existing artifacts.
- [ ] Seeded `test-feature-*` dir/branch/unregistered-worktree reaped; pre-existing NOT touched (test proves both).
- [ ] `.gitignore:143-144` removed; pollution assertion reds on a seeded leak.
- [ ] `/tmp` sweep uses WP02's shared namespace root (imported, not hand-copied) + removes the run's `spec-kitty-test-homes/<run_uid>/`.
- [ ] `PWHEADLESS=1 uv run pytest tests/architectural/test_session_reaper.py -q` green; a representative full-suite slice leaves REPO_ROOT + `/tmp` clean of test residue.
- [ ] `ruff` + `mypy --strict` clean; no new suppressions.

## Commit
`git add -A && git commit -m "fix(#1842): controller-gated session reaper + retire test-feature gitignore masks"`

## Reviewer Guidance
Confirm the controller gate (a worker process must NOT reap). Confirm snapshot-delta never deletes a pre-existing tracked mission/branch/worktree (seed one and prove). Confirm git-unregistered `.worktrees/` husks are reaped (prune can't see them). Confirm the reaper imports WP02's shared namespace constant (no drift). Confirm the snapshot is name-pattern, not a deep `rglob` inventory.

## Activity Log

- 2026-07-06T20:06:12Z – claude – shell_pid=802476 – Assigned agent via action command

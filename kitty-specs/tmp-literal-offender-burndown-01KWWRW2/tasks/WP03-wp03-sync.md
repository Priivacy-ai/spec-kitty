---
work_package_id: WP03
title: '/tmp burn-down: sync'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: fix/tmp-literal-offender-burndown
merge_target_branch: fix/tmp-literal-offender-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/tmp-literal-offender-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/tmp-literal-offender-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T0301
agent: "claude"
shell_pid: "1000467"
history:
- 'Created by planner for #1842 burn-down tasks phase'
agent_profile: python-pedro
authoritative_surface: tests/sync/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/sync/conftest.py
- tests/sync/test_daemon_owner_record.py
- tests/sync/test_daemon_singleton_reaper_consolidation.py
- tests/sync/test_dossier_pipeline.py
- tests/sync/test_dossier_timezone_defaults_unit.py
- tests/sync/test_events.py
- tests/sync/test_git_metadata.py
- tests/sync/test_lifecycle_readiness.py
- tests/sync/test_sync_boundary_preflight.py
- tests/sync/test_sync_doctor.py
- tests/sync/test_sync_logged_out_recovery.py
- tests/sync/test_sync_status_boundary_check.py
- tests/sync/tracker/test_origin_models.py
role: implementer
tags: []
task_type: implement
---

# WP03 – /tmp burn-down: sync

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, Sonnet-5). Read `spec.md` (FR-001/002/005/006/007, NFR-001, C-001) + `plan.md` ("Per-file method").

## Objective
Convert the 13 baselined test files below OFF literal `/tmp` — genuine write-leaks to `tmp_path`/fixtures, arbitrary path-literals to non-`/tmp` sentinels — preserving each test's exact behavior. **Do NOT edit `tmp_ratchet_baseline.txt`** (WP08 owns it; a converted file left baselined is simply skipped by the ratchet, so the gate stays green).

## Files (13)
- `tests/sync/conftest.py`
- `tests/sync/test_daemon_owner_record.py`
- `tests/sync/test_daemon_singleton_reaper_consolidation.py`
- `tests/sync/test_dossier_pipeline.py`
- `tests/sync/test_dossier_timezone_defaults_unit.py`
- `tests/sync/test_events.py`
- `tests/sync/test_git_metadata.py`
- `tests/sync/test_lifecycle_readiness.py`
- `tests/sync/test_sync_boundary_preflight.py`
- `tests/sync/test_sync_doctor.py`
- `tests/sync/test_sync_logged_out_recovery.py`
- `tests/sync/test_sync_status_boundary_check.py`
- `tests/sync/tracker/test_origin_models.py`

## Per-file method
For EACH file, for EACH `/tmp/` occurrence:
1. **Classify**: **A** = the test creates filesystem state under `/tmp` (`mkdir`/`open`/`write_text`/`makedirs`/`touch`/`mkdtemp`) → route through the pytest **`tmp_path`** fixture (or a fixture with teardown). **B** = `/tmp/...` is an arbitrary absolute path used in a mock / test-data / assertion that never touches disk → replace with a non-`/tmp` absolute **sentinel** (e.g. `/nonexistent/...` or a `tmp_path`-derived string) that preserves the exact assertion/mock identity.
2. **Preserve intent (C-001 / NFR-001)**: an absolute-path-rejection test stays an absolute-path test; a Windows `C:\...` sibling keeps cross-platform coverage; if the literal appears in an assertion *message/expected string*, update source AND expected together so the assertion still matches. **Never** xfail/skip/delete/loosen a test to pass the gate.
3. **Real isolation, not evasion (FR-007)**: for category A, the fix MUST adopt `tmp_path`/a teardown fixture and leave zero residue. **Forbidden**: `/tmp/`→`/dev/shm/`/`/scratch/`/`/var/tmp/`, or an uncleaned `mkdtemp()`/`gettempdir()` with no teardown.
4. Run that file's tests green; `grep -n '/tmp/' <file>` → 0.

## DoD
- [ ] `grep -rn '/tmp/' <all your files>` → 0.
- [ ] Category-A files adopt `tmp_path`/fixtures (grep shows `tmp_path`/fixture usage where a write was); no `/dev/shm`/`/scratch`/uncleaned-`mkdtemp` evasion.
- [ ] Every touched file's tests pass with original assertions intact (`PWHEADLESS=1 uv run pytest <files> -q`).
- [ ] `ruff check` + `mypy --strict` clean on touched files; no new suppressions.
- [ ] `tmp_ratchet_baseline.txt` UNCHANGED by you.

## Commit
`git add <your files> && git commit -m "test(sync): convert WP03 tests off literal /tmp (tmp_path/sentinels) — refs #1842"`

## Report back
Per-file: A/B classification + what changed; the pytest counts; ruff+mypy; confirm 0 `/tmp/` remain and the baseline is untouched; lane commit SHA. If any file genuinely cannot be converted (e.g. it tests literal `/tmp` handling itself), STOP and report it (candidate to stay baselined with a rationale, C-003).

## Activity Log

- 2026-07-06T23:18:03Z – claude – shell_pid=1000467 – Assigned agent via action command
- 2026-07-06T23:33:51Z – claude – shell_pid=1000467 – Moved to for_review
- 2026-07-06T23:51:16Z – user – shell_pid=1000467 – Moved to approved

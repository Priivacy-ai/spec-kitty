---
work_package_id: WP04
title: 'Second-layer Windows surface: ci-windows.yml static windows_critical list propagation (FR-008)'
dependencies:
- WP03
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-topology-shrink-01KWQAVX
base_commit: aa998ede7e31927286e78e7819757e03c2f2c604
created_at: '2026-07-04T21:00:00+00:00'
subtasks:
- T012
phase: Phase 4 - Second-layer surfaces
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1158946"
history:
- at: '2026-07-04T21:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-windows.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-windows.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Second-layer Windows surface

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Propagate any **windows-marked** test file that WP03's shard carve relocated into `ci-windows.yml`'s static `windows_critical` list (`:24-42`) — the **only** real second-layer surface per the corrected FR-008. This closes the Windows split-brain edge case: a carved test file also listed in `windows_critical` must be updated in lockstep or FR-003c reds.

**FR-008 correction (do NOT edit these)**: `scripts/ci/quality_gate_decision.py` holds no job→group data; `drift-detector.yml` and `release.yml` carry no shard/ignore/job names. Editing any of them is out-of-scope drift.

## Subtasks & Detailed Guidance

### Subtask T012 – Static `windows_critical` list propagation
- Diff WP03's carve against the current `ci-windows.yml:24-42` static list. For each windows-marked test file whose path moved (or whose owning root was carved into a new shard), update the static list entry so it still points at a live test file.
- Assert `test_every_filter_glob_is_live` (FR-003c — covers all 4 workflows incl. `ci-windows.yml`) stays green: no dead `windows_critical` glob, no split-brain (C-002).
- If WP03 relocated NO windows-marked files, this is a verified no-op: record the justification AND the green glob-live invariant (the invariant proves the list is coherent — the DoD stays non-fakeable).

## Campsite cleaning (standing rule; ride the WP's normal review)

YAML file — keep it coherent, no dead anchors. Do NOT touch `ci-quality.yml` (WP03), `quality_gate_decision.py`, `drift-detector.yml`, or `release.yml`.

## Definition of Done (non-fakeable — every anchor is a green test)

- **`test_every_filter_glob_is_live` GREEN** over `ci-windows.yml` (every `windows_critical` entry maps to a live file; no dead glob) — recorded run output.
- Every windows-marked file relocated by WP03 is present in the static list (or a recorded no-op justification if none moved), with C-002 no-split-brain preserved.

## Risks / Reviewer Guidance

- A relocated windows file dropped from the static list → the glob-live/coherence invariant reds; update in the same landing.
- Reviewer confirms scope stayed on `ci-windows.yml` — the FR-008 correction rules out the other three files.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T21:00:00Z – system – Prompt created.
- 2026-07-05T01:18:21Z – claude:opus:python-pedro:implementer – shell_pid=1149952 – Assigned agent via action command
- 2026-07-05T01:40:00Z – claude:opus:python-pedro:implementer – T012 VERIFIED NO-OP. Diffed WP03's carve (b4cb334e3) — it changed only `.github/workflows/ci-quality.yml` (1 file, 261+/61-). Every `tests/` reference in that diff is a shard `--ignore` exclusion or a `paths:` shard root (composite groups + fast-matrix split), NOT a test-file rename/move on disk. No windows-marked test file path was relocated. All 19 `windows_critical` static entries in `ci-windows.yml:24-42` were checked against disk and are LIVE (tests/conftest.py, tests/auth/secure_storage/test_file_fallback_windows_root.py, tests/cli/test_agent_status_messaging.py, tests/cli/test_migrate_cmd_messaging.py, tests/core/test_worktree_symlink_fallback.py, tests/kernel/test_paths_unified_windows_root.py, tests/lanes/test_acceptance_matrix.py, tests/mission/test_active_mission_handle_windows.py, tests/paths/test_windows_migrate.py, tests/policy/test_hook_installer_execution.py, tests/regressions/test_issue_101_utf8_startup.py, tests/regressions/test_issue_105_hook_python_lookup.py, tests/regressions/test_issue_71_dashboard_empty.py, tests/review/test_baseline.py, tests/runtime/test_home_unit.py, tests/specify_cli/cli/commands/test_charter_generate_autotrack.py, tests/sync/test_daemon_windows_paths.py, tests/sync/test_issue_586_windows_import.py, tests/tracker/test_credentials_windows_paths.py). No `ci-windows.yml` edit required. C-002 no-split-brain preserved. Coherence invariant GREEN (non-fakeable DoD): `PWHEADLESS=1 uv run pytest tests/architectural/test_workflow_coherence.py -v -k "glob_is_live or filter_glob"` → `tests/architectural/test_workflow_coherence.py::test_every_filter_glob_is_live PASSED [100%]` / `1 passed, 15 deselected`. `test_every_filter_glob_is_live` iterates `gc.WORKFLOW_FILES` (includes `ci-windows.yml`, per `_gate_coverage.py:78`), so the pass proves every `windows_critical` glob maps to a live tracked file. Scope stayed strictly on `ci-windows.yml`; `ci-quality.yml`/`quality_gate_decision.py`/`drift-detector.yml`/`release.yml` untouched per the FR-008 correction.
- 2026-07-05T01:23:11Z – claude:opus:python-pedro:implementer – shell_pid=1149952 – Verified no-op: WP03 relocated shards not windows-marked file paths; test_every_filter_glob_is_live green over ci-windows.yml
- 2026-07-05T01:23:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=1158946 – Started review via action command
- 2026-07-05T01:26:32Z – user – shell_pid=1158946 – Review passed: verified no-op — WP03 carve (b4cb334e3) touched only ci-quality.yml, zero renames/deletions across the whole lane diff, so no windows-marked test file was relocated; all 19 windows_critical test entries (+pyproject/pytest.ini) LIVE on disk; test_every_filter_glob_is_live PASSED (ran it: 28.14s), covers ci-windows.yml via gc.WORKFLOW_FILES; ci-windows.yml + quality_gate_decision.py/drift-detector.yml/release.yml untouched (no WP04 commit). C-002 no-split-brain preserved.

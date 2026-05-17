---
work_package_id: WP03
title: Sync status and doctor truthfulness
dependencies:
- WP01
- WP02
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-013
- NFR-001
- NFR-002
- C-001
- C-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
phase: Phase 2 - Status
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "75062"
history:
- timestamp: '2026-05-17T16:42:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/cli/commands/doctor.py
- tests/sync/test_sync_status_boundary_check.py
role: implementer
tags: []
---

# Work Package Prompt: WP03 — Sync status and doctor truthfulness

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Extend the `sync status` command to surface the full identity boundary state and make `sync status --check` return non-zero whenever the boundary is incoherent (foreground vs daemon mismatch, legacy rows in active scope, orphan daemons). Add `doctor` orphan listing + retirement.

Done means:
- `sync status` prints the FR-008 fields:
  - Foreground: CLI version, executable path, server URL, auth principal/team/scope.
  - Active scoped queue: DB path, event count, body-upload count.
  - Legacy queue: DB path, event count, body-upload count.
  - Daemon owner record: PID, port, version, executable path, source path, server URL, auth scope, queue DB path.
  - Diagnostics: list of mismatched fields between foreground and daemon (D-3 fields).
  - Orphan daemon count (and optional list).
- `sync status --check` returns non-zero exit code when ANY of:
  - foreground/daemon disagree on any D-3 field;
  - legacy DB has ≥1 row in any migration-table for the active scope (use `detect_legacy_rows_for_scope` from WP01);
  - ≥1 orphan daemon (use `is_orphan` / `list_orphan_records` from WP02).
- When status detects that setup-plan body uploads from the current mission are in legacy, the diagnostic line includes "setup-plan stranded mission slug X" (FR-013). Detection heuristic: a legacy body_upload_queue row whose payload references a mission slug matching the active mission context (or any mission slug found in any active scoped queue — pick whichever is cleaner; the goal is operator visibility).
- `doctor` (search for existing `doctor` command file under `src/specify_cli/cli/commands/`) gains an orphan-daemons subsection that lists orphans and prints a copy-pasteable retirement command (`rm <path>` or `spec-kitty agent doctor retire-daemon --pid <pid>` if that command already exists; otherwise just print the path).
- `tests/sync/test_sync_status_boundary_check.py` covers:
  - Healthy state → `--check` exits 0.
  - Stale daemon version (mock daemon owner record with old version) → `--check` exits non-zero, message names `package_version`.
  - Legacy body-upload backlog for active scope → `--check` exits non-zero, message names the legacy DB path and FR-013 tag.
  - Orphan daemon (dead PID) → `--check` exits non-zero, message names orphan count.
- `mypy --strict src/specify_cli/cli/commands/sync/` passes.

## Context & Constraints

- Spec: FR-008, FR-009, FR-010, FR-013, C-001.
- Depends on WP01 (`detect_legacy_rows_for_scope`) and WP02 (`read_owner_record`, `mismatched_fields`, `is_orphan`).
- Existing status command: locate via `grep -rn "def status" src/specify_cli/cli/commands/sync/` (most likely in `status.py`). Mirror its existing Rich console pattern; do not introduce a new output framework.

## Subtasks

### T012 — Extend `sync status` output
- Add the FR-008 fields under a clear "Identity Boundary" section. Use the existing Rich Panel/Table style.

### T013 — `--check` exit-code logic
- Implement the three-condition gate. Return non-zero with a structured stderr message naming the failing condition(s).

### T014 — Doctor orphan listing
- Add to the existing `doctor` command (if present) or add a `sync status --check` subsection. Prefer extending `doctor` if it exists.

### T015 — FR-013 stranded tag
- In the legacy-row-count diagnostic, if the active mission context can be resolved, annotate with `"setup-plan stranded mission slug X"`. Best-effort; if mission context is not derivable from the current cwd, omit the tag.

### T016 — Tests
- Use `pytest.fixture(tmp_path)` and `monkeypatch.setenv("HOME", str(tmp_path))`.
- Use the click/typer testing runner (consult existing tests in `tests/sync/` for the pattern).
- Construct fake daemon owner records via `write_owner_record(DaemonOwnerRecord(...))` (from WP02) rather than starting a real daemon.

## Branch Strategy

Planning base: `main`. Final merge target: `main`.

## Definition of Done

- [ ] `sync status` shows all FR-008 fields
- [ ] `sync status --check` returns non-zero on the three FR-009 conditions
- [ ] FR-013 stranded-mission tag in status output
- [ ] Doctor lists orphan daemons (or status surfaces equivalent)
- [ ] 4 test scenarios in T016 pass
- [ ] `mypy --strict src/specify_cli/cli/commands/sync/` passes
- [ ] No new deps

## Risks

- Status output is consumed by other tests; renaming sections may break golden-file tests. Mitigated by inserting the new section without renaming existing sections.

## Reviewer Guidance

- Confirm `--check` returns exit 0 in healthy state.
- Confirm each of the four scenarios in T016 trips the gate with a clear message.
- Spot-check `doctor` (or status) output for orphan listing.

## Activity Log

- 2026-05-17T17:11:16Z – claude:opus-4-7:python-pedro:implementer – shell_pid=70501 – Started implementation via action command
- 2026-05-17T17:22:26Z – claude:opus-4-7:python-pedro:implementer – shell_pid=70501 – Ready for review: sync status + doctor truthfulness + 4 scenarios
- 2026-05-17T17:22:53Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=75062 – Started review via action command
- 2026-05-17T17:26:07Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=75062 – Review passed: status surfaces full boundary; --check returns non-zero on incoherence; orphan listing in doctor; 5 scenarios green; mypy clean.

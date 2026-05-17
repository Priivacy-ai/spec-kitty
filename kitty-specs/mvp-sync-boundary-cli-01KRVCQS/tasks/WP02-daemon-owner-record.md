---
work_package_id: WP02
title: Daemon owner record and ownership semantics
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-010
- NFR-001
- NFR-002
- C-002
- C-004
- C-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
phase: Phase 1 - Daemon
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "61161"
history:
- timestamp: '2026-05-17T16:42:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/sync/owner.py
- src/specify_cli/sync/daemon.py
- tests/sync/test_daemon_owner_record.py
role: implementer
tags: []
---

# Work Package Prompt: WP02 — Daemon owner record and ownership semantics

## ⚡ Do This First: Load Agent Profile

```text
/ad-hoc-profile-load python-pedro
```

## Review Feedback

*(empty)*

---

## Objectives & Success Criteria

Add a `DaemonOwnerRecord` (per [data-model.md](../data-model.md)) that the sync daemon writes atomically on start, exposes via the health endpoint, and the foreground reads to refuse mismatched sync actions. Add orphan-detection helpers.

Done means:
- New module `src/specify_cli/sync/owner.py`:
  - `@dataclass(frozen=True) class DaemonOwnerRecord` with the D-2 fields (pid, port, token, package_version, executable_path, source_checkout_path, server_url, auth_principal, auth_team, auth_scope, queue_db_path, started_at).
  - `write_owner_record(record)` — atomic write via temp file + `os.replace`, target path `<sync_root>/daemon/owner.json`.
  - `read_owner_record()` → `DaemonOwnerRecord | None`.
  - `redact_token(record)` → dict (for health endpoint).
  - `compute_foreground_identity()` → dict of the comparable fields from the foreground perspective.
  - `mismatched_fields(daemon_record, foreground_identity)` → list of mismatched field names from {`package_version`, `executable_path`, `server_url`, `auth_scope`, `queue_db_path`} (D-3).
  - `is_orphan(record)` → bool (PID not alive OR executable path missing).
  - `list_orphan_records()` → list of stale owner records (if multi-owner registry exists; otherwise a thin wrapper).
- `src/specify_cli/sync/daemon.py` writes the owner record atomically when the daemon binds its port. On clean shutdown, removes the file (file removal is best-effort; orphan detection covers crashes).
- Daemon health endpoint includes `owner: <redacted-record-dict>` in its JSON response.
- `tests/sync/test_daemon_owner_record.py` covers:
  - Write+read round-trip (atomic write does not leave temp file behind on success or failure).
  - Mismatch detection across each of the five D-3 fields.
  - Orphan detection when PID is dead (use a real but already-exited subprocess so PID is stable but not alive).
  - Orphan detection when executable path no longer exists.
  - Health endpoint excludes `token`.
- `mypy --strict src/specify_cli/sync/owner.py src/specify_cli/sync/daemon.py` passes.

## Context & Constraints

- Spec: `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/spec.md` (FR-005..FR-007, FR-010, C-002, C-006).
- Data model: `kitty-specs/mvp-sync-boundary-cli-01KRVCQS/data-model.md` (record shape; mismatch fields).
- Existing daemon code: `src/specify_cli/sync/daemon.py` — note `_sync_root()` line 58, `_daemon_root()` line 71, `_write_daemon_file()` line 195, `handle_health()` line 385.
- Reuse `_is_process_alive()` line 204 for orphan detection.
- C-002: tests MUST NOT kill live operator daemon processes. Use controlled subprocesses you spawn yourself.
- C-006: file-locking — `daemon.lock` already exists for the daemon process; owner.json write uses `os.replace` for atomicity, no extra lock needed.

## Subtasks

### T006 — `owner.py` module
- Create the new file with all the symbols above. Use `dataclasses.asdict` for dict conversion; `tempfile.NamedTemporaryFile(delete=False, dir=…)` plus `os.replace` for atomic write.

### T007 — Wire `daemon.py`
- After `_find_free_port` succeeds and the daemon HTTP server is ready, build the `DaemonOwnerRecord` from process state + `compute_foreground_identity()` (the daemon IS the foreground for this purpose at start time) + auth fields read from credentials/session.
- Call `write_owner_record(record)` before serving traffic.
- Add a shutdown hook (atexit / signal handler) that removes the owner record on clean exit.

### T008 — Health endpoint
- Modify `handle_health` to include `"owner": redact_token(read_owner_record())` in its JSON response when an owner record exists.

### T009 — Foreground coherence check
- Add `check_daemon_owner_match() -> tuple[bool, list[str]]` in `owner.py`. Returns `(True, [])` if no daemon record exists OR all D-3 fields match; otherwise `(False, [mismatched_field_names])`.
- Document the function in its docstring as the canonical pre-action check.

### T010 — Orphan detection
- `is_orphan(record)` and `list_orphan_records()` per data-model.md. For now, the registry is the single `owner.json` file; if it points to a dead PID or missing executable, it is an orphan. (Future multi-daemon-process registry is out of scope for this mission.)

### T011 — Tests
- Create `tests/sync/test_daemon_owner_record.py`. Use `monkeypatch.setenv("HOME", str(tmp_path))`. For orphan tests, spawn a `subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(0)"])` and `wait()` for it, then use its `.pid` as a known-dead PID. For missing-executable tests, copy `sys.executable` to a temp file, point the record at it, then delete the temp file before checking.
- Assert atomic-write leaves no temp file when the destination is replaced.

## Branch Strategy

Planning base: `main`. Final merge target: `main`. Worktree per lane.

## Definition of Done

- [ ] `src/specify_cli/sync/owner.py` created
- [ ] `DaemonOwnerRecord` dataclass with D-2 fields
- [ ] Atomic write/read helpers
- [ ] Mismatch + orphan detection helpers
- [ ] Daemon writes record on start; removes on clean shutdown
- [ ] Health endpoint surfaces redacted record
- [ ] Tests cover write/read round-trip, mismatch on each D-3 field, orphan via dead PID, orphan via missing executable
- [ ] `mypy --strict src/specify_cli/sync/owner.py src/specify_cli/sync/daemon.py` passes
- [ ] No new pyproject deps

## Reviewer Guidance

- Verify atomic write pattern (temp file + `os.replace`, not direct truncate-write).
- Verify token never appears in the health response.
- Confirm tests do not invoke `os.kill` or otherwise touch operator processes.

## Activity Log

- 2026-05-17T16:58:32Z – claude:opus-4-7:python-pedro:implementer – shell_pid=61161 – Started implementation via action command
- 2026-05-17T17:07:41Z – claude:opus-4-7:python-pedro:implementer – shell_pid=61161 – Ready for review: DaemonOwnerRecord + atomic write + mismatch/orphan helpers + tests

---
work_package_id: WP04
title: Daemon health identity + self-retirement
dependencies: []
requirement_refs:
- C-001
- FR-007
- FR-010
- FR-011
- NFR-005
tracker_refs: []
planning_base_branch: fix/sync-daemon-orphan-cleanup
merge_target_branch: fix/sync-daemon-orphan-cleanup
branch_strategy: Planning artifacts for this mission were generated on fix/sync-daemon-orphan-cleanup. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-daemon-orphan-cleanup unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Daemon lifecycle
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "19999"
history:
- at: '2026-06-30T11:18:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/daemon.py
create_intent:
- tests/sync/test_daemon_health_identity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/daemon.py
- tests/sync/test_daemon_self_retirement.py
- tests/sync/test_daemon_health_identity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Daemon health identity + self-retirement

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile named in the frontmatter **before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is set, run `spec-kitty agent profile list` and pick the best match for `task_type: implement` on `authoritative_surface: src/specify_cli/sync/daemon.py`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks (```python`, ```bash`).

---

## Objective

Make the running sync daemon (`sync/daemon.py`) (1) advertise its **family/identity** on `/api/health` so scanners can confirm it from the self-report (FR-001 defense-in-depth), (2) keep startup's reuse-or-spawn from creating a **redundant** daemon after stale same-scope cleanup (FR-007), and (3) **self-retire** when superseded or idle, governed by a **named, test-patchable constant** (FR-010/011).

## Context & Constraints

Read before editing:
- [contracts/health-payload.md](../contracts/health-payload.md) (adds `daemon_family`), [data-model.md](../data-model.md) self-retirement state machine, [research.md](../research.md) DD-03; [spec.md](../spec.md) FR-007, FR-010, FR-011, C-001.

Current code (`sync/daemon.py`):
- `handle_health` (`:487-520`) — builds the health payload; already includes `protocol_version`, `package_version`, redacted `owner`.
- Scope marker `DAEMON_SCOPE_ARG_PREFIX` (`:815`), `_daemon_scope_root()` (`:818-830`).
- Startup reuse/spawn: `ensure_sync_daemon_running` (`:1000-1073`), `_reuse_or_cleanup_existing_daemon` (`:1165-1197`), `_reap_same_executable_orphans` (`:1143-1162`).
- State file (recorded singleton) `_parse_daemon_file`/`_write_daemon_file` (`:270-304`).
- Existing self-retirement tick + tests: `tests/sync/test_daemon_self_retirement.py` (extend it). `_write_state` helper (`:41-47` of that test).

**Negative scope**: do NOT change `owner.py`/`orphan_sweep.py`/`classification.py`. Do NOT add auth or non-loopback exposure to `/api/health` (keep it `127.0.0.1`-only, unauthenticated — Sonar loopback exception). The actual orphan reaping at startup is WP02's reaper; this WP only ensures the *spawn decision* does not add a redundant daemon and that the daemon retires itself.

## Branch Strategy

- **Strategy**: lane-per-WP (from `lanes.json`)
- **Planning base branch**: `fix/sync-daemon-orphan-cleanup`
- **Merge target branch**: `fix/sync-daemon-orphan-cleanup`

> No dependencies — root lane, parallel-safe with WP01. Codes against the health-payload contract, not against WP01's module.

## Subtasks & Detailed Guidance

### Subtask T016 – `daemon_family` + scope on `/api/health`

- **Purpose**: Let a scanner confirm family/scope from the self-report.
- **Files**: `src/specify_cli/sync/daemon.py` (`handle_health`).
- **Steps**:
  1. Add `payload["daemon_family"] = "sync"`.
  2. Surface `singleton_scope_id` (the resolved `_daemon_scope_root()`) so the self-report carries scope (either top-level or inside `owner`). Keep the redacted-token contract intact (`redact_token`).
- **Notes**: Additive only — existing keys unchanged (back-compat). WP01's classifier reads `daemon_family` defensively, so this is the producer side.

### Subtask T017 – No redundant spawn after stale cleanup (FR-007)

- **Purpose**: Once stale same-scope daemons are cleaned, startup reuses the healthy singleton rather than spawning another.
- **Files**: `src/specify_cli/sync/daemon.py`.
- **Steps**:
  1. Trace `ensure_sync_daemon_running` → `_reuse_or_cleanup_existing_daemon`: confirm that when a healthy recorded singleton exists it is reused (existing behavior) and that the WP02 reaper having cleaned stale non-singleton daemons does not trigger a new spawn.
  2. If a gap exists (e.g., a stale daemon on the singleton port blocks reuse), ensure the cleanup-then-reuse ordering yields exactly one daemon.
- **Notes**: Mostly verification + a focused test; only change code if the ordering can produce a second daemon.

### Subtask T018 – Named idle-retirement constant (FR-011)

- **Purpose**: A single, test-patchable knob.
- **Files**: `src/specify_cli/sync/daemon.py`.
- **Steps**:
  1. Add `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS = 900` (module constant, with a comment citing FR-011 + DD-03 default rationale).
  2. Route the idle-retirement tick through this constant (no magic numbers).
- **Notes**: Tests patch it to a low value (e.g. 0.1 s) for determinism.

### Subtask T019 – Self-retirement logic (FR-010/011)

- **Purpose**: Superseded or idle daemons exit; busy daemons never do.
- **Files**: `src/specify_cli/sync/daemon.py`.
- **Steps**:
  1. **Superseded**: if the recorded singleton (state file pid/port) is no longer this process, and `sync.is_running` is false with no queued work → retire promptly (do not wait the full idle window).
  2. **General idle**: if no auth/no work for `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS` → retire.
  3. **Guard**: never retire while sync work is in flight (FR-010).
- **Notes**: Reuse the existing tick structure in the daemon loop; keep the decision in a small testable helper (`_should_self_retire(...) -> bool`).

### Subtask T020 – Tests

- **Purpose**: Prove retirement + the health field.
- **Files**: `tests/sync/test_daemon_self_retirement.py` (extend), `tests/sync/test_daemon_health_identity.py` (new).
- **Steps**:
  1. In the self-retirement suite: patch `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS` low; assert a superseded/idle daemon exits and a busy one does not. Reuse `_write_state`.
  2. New health-identity test: stand up the handler (or a real subprocess via the existing harness) and assert `/api/health` returns `daemon_family == "sync"` and surfaces scope.
- **Notes**: Real-port pieces run serially (`-n0`); `skipif(sys.platform == "win32")` for socket-dependent assertions.

## Test Strategy

- `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_daemon_self_retirement.py tests/sync/test_daemon_health_identity.py -n0 -q`.
- `.venv/bin/ruff check src/specify_cli/sync/daemon.py tests/sync/test_daemon_self_retirement.py tests/sync/test_daemon_health_identity.py` + `.venv/bin/mypy --strict src/specify_cli/sync/daemon.py` — zero issues.

## Risks & Mitigations

- **Retiring a busy daemon**: the FR-010 in-flight guard is mandatory; test the busy-no-retire path explicitly.
- **Flaky timing**: drive retirement off the patchable constant, never wall-clock sleeps in tests.
- **Health back-compat**: only add keys; never remove/rename existing ones.

## Review Guidance

- Verify `/api/health` gains `daemon_family` (and scope) additively, loopback-only, token still redacted.
- Verify `SYNC_DAEMON_IDLE_RETIREMENT_SECONDS` is a named constant and the tick uses it (no magic numbers).
- Verify the in-flight-work guard prevents retirement (FR-010).
- Verify startup yields exactly one daemon after stale cleanup (FR-007).

## Activity Log

- 2026-06-30T11:18:31Z – system – Prompt created.
- 2026-06-30T11:49:51Z – claude:sonnet:python-pedro:implementer – shell_pid=13469 – Assigned agent via action command
- 2026-06-30T12:02:10Z – claude:sonnet:python-pedro:implementer – shell_pid=13469 – health daemon_family + singleton_scope_id (T016); no-redundant-spawn confirmed (T017); SYNC_DAEMON_IDLE_RETIREMENT_SECONDS=900 named constant (T018); _should_self_retire() pure helper, superseded/idle/busy coverage (T019/FR-010); serial tests green 33/33; ruff+mypy clean (T020)
- 2026-06-30T12:05:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=12481 – Started review via action command
- 2026-06-30T12:13:20Z – user – shell_pid=12481 – Moved to planned
- 2026-06-30T12:14:23Z – claude:sonnet:python-pedro:implementer – shell_pid=16576 – Started implementation via action command
- 2026-06-30T12:19:27Z – claude:sonnet:python-pedro:implementer – shell_pid=16576 – Cycle 1 fixes: stub-handler subclass resolves call-overload; all # type: ignore removed; mypy+ruff clean on daemon.py AND both test files; pytest -n0 green (33/33)
- 2026-06-30T12:20:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=19999 – Started review via action command
- 2026-06-30T12:23:52Z – user – shell_pid=19999 – Cycle 1 re-review passed: mypy --strict/ruff/pytest clean on all 3 files; all type:ignore removed; logic invariants intact

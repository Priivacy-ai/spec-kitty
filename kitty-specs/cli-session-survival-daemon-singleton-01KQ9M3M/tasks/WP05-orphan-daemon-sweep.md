---
work_package_id: WP05
title: Orphan daemon sweep
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T09:17:32+00:00'
subtasks:
- T019
- T020
- T021
- T022
shell_pid: "55938"
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/sync/orphan_sweep.py
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- src/specify_cli/sync/orphan_sweep.py
- tests/sync/test_orphan_sweep.py
priority: P1
status: planned
tags: []
agent_profile: python-pedro
role: implementer
agent: "claude:sonnet:reviewer-renata:reviewer"
---

# WP05 — Orphan daemon sweep

## ⚡ Do This First: Load Agent Profile

Load the assigned agent profile via `/ad-hoc-profile-load <agent_profile>` before any other tool call.

## Objective

Build `src/specify_cli/sync/orphan_sweep.py`. Two public functions: `enumerate_orphans()` scans ports 9400-9450, probes `/api/health`, classifies as Spec Kitty daemons by `protocol_version`+`package_version` keys, and excludes the singleton (the port recorded in `DAEMON_STATE_FILE`). `sweep_orphans()` terminates the rest via escalating shutdown (HTTP → SIGTERM → SIGKILL). The user-triggered surface for this is `auth doctor --reset` (WP06).

## Context

When the daemon-singleton invariant has already been violated (older CLI versions racing, crashes, or reorganized state), orphan daemons accumulate on adjacent ports in the reserved range. `auth doctor` should surface them; `auth doctor --reset` should clean them up without forcing the user to learn `lsof` or `psutil`. WP05 is the underlying mechanism; WP06 is the user surface.

**Key spec references**:
- FR-009: detect orphan daemons in the reserved port range and terminate them on explicit user request.

**Key planning references**:
- `contracts/daemon-singleton.md` §"Orphan identification" and §"Orphan sweep".
- `research.md` D7 (orphan identification rule), D8 (termination strategy).

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP05`. Independent of WP01/02/03/04 — runs in its own lane.

To start work:
```bash
spec-kitty implement WP05
```

## Subtasks

### T019 — `orphan_sweep.py` skeleton with dataclasses

**Purpose**: Stand up the new module with the public API surface and the two frozen dataclasses.

**Files to create**: `src/specify_cli/sync/orphan_sweep.py`.

**Steps**:
1. Module docstring stating purpose and the consumer (WP06's `auth doctor --reset`).
2. Define `@dataclass(frozen=True) class OrphanDaemon`:
   ```python
   pid: int | None
   port: int
   package_version: str | None
   protocol_version: int | None
   ```
3. Define `@dataclass(frozen=True) class SweepReport`:
   ```python
   swept: list[OrphanDaemon]
   failed: list[tuple[OrphanDaemon, str]]  # (orphan, reason)
   duration_s: float
   ```
4. Define stub functions:
   ```python
   def enumerate_orphans() -> list[OrphanDaemon]: ...
   def sweep_orphans(orphans: list[OrphanDaemon], *, timeout_s: float = 5.0) -> SweepReport: ...
   ```
   Bodies raise `NotImplementedError`.
5. Public re-exports in `__all__`.

**Validation**: `python -c "from specify_cli.sync.orphan_sweep import enumerate_orphans, sweep_orphans, OrphanDaemon, SweepReport"` succeeds.

### T020 — `enumerate_orphans()` — port scan + identity probe

**Purpose**: Scan the reserved port range, probe `/api/health`, classify Spec Kitty daemons, exclude the singleton.

**Steps**:
1. Read the singleton port from `DAEMON_STATE_FILE` via the existing `_parse_daemon_file` helper. Capture `current_port` (or `None` if file missing).
2. For each `port in range(DAEMON_PORT_START, DAEMON_PORT_START + DAEMON_PORT_MAX_ATTEMPTS)`:
   - Quick connect-test: `socket.socket().connect_ex(("127.0.0.1", port))` with `settimeout(0.05)`. If non-zero: skip (port closed).
   - HTTP probe: `_fetch_health_payload(f"http://127.0.0.1:{port}/api/health", timeout=0.5)` (existing helper).
   - If response is `None` or doesn't include both `protocol_version` and `package_version`: skip (not a Spec Kitty daemon).
   - If `port == current_port`: skip (singleton).
   - PID lookup: iterate `psutil.net_connections(kind="tcp")` filtered by `laddr.port == port` and `status == "LISTEN"`; first match's PID. May be `None` on AccessDenied.
   - Append `OrphanDaemon(pid=pid, port=port, package_version=resp.get("package_version"), protocol_version=resp.get("protocol_version"))`.
3. Return the list (may be empty).

**Files**: `src/specify_cli/sync/orphan_sweep.py`.

**Validation**: T022 spawns adjacent daemons and asserts the result.

**Edge cases**:
- 50-port scan with all closed ports: ≤ 50 × 50 ms = 2.5 s worst case (NFR-006 budget).
- Non-Spec-Kitty service responding with 200 + a `version` key but no `protocol_version`: NOT classified as orphan.

### T021 — `sweep_orphans()` — escalating shutdown

**Purpose**: Per-orphan, attempt graceful shutdown then escalate. Bounded total runtime via `timeout_s` parameter.

**Steps**:
1. For each orphan in input list:
   1. **HTTP shutdown** (best-effort): build `POST http://127.0.0.1:{port}/api/shutdown` with empty body (no token; will return 403 — that's expected). Wait up to 1 s. If the port stops listening: record swept; continue.
   2. **SIGTERM via psutil**: if `orphan.pid` is known, `psutil.Process(orphan.pid).terminate()`. Wait up to 1 s for port to close.
   3. **SIGKILL via psutil**: `psutil.Process(orphan.pid).kill()`. Wait up to 1 s.
   4. **State-file cleanup**: locate any state file pointing at the orphan port and remove it (best-effort).
   5. If port is still listening after all steps: append to `SweepReport.failed` with reason "port still listening after escalation".
2. Compute `duration_s` via `time.monotonic()` deltas.
3. Return `SweepReport`.

**Files**: `src/specify_cli/sync/orphan_sweep.py`.

**Validation**: T022 spawns a real daemon on an adjacent port and confirms `sweep_orphans` terminates it.

**Edge cases**:
- `psutil.AccessDenied` (e.g., daemon owned by another OS user): record in `failed` with reason "AccessDenied". Sweep continues with remaining orphans.
- `psutil.NoSuchProcess` (orphan died between enumerate and sweep): record as swept (it's gone).
- `orphan.pid is None`: skip the SIGTERM/SIGKILL steps; rely on HTTP shutdown attempt.

### T022 — `tests/sync/test_orphan_sweep.py` — 7 cases

**Purpose**: Cover every branch in `contracts/daemon-singleton.md` §"Test contract".

**Steps**: implement these tests:
1. `test_enumerate_finds_singleton_only` — single daemon on 9400; state file points at 9400; `enumerate_orphans()` returns `[]`.
2. `test_enumerate_finds_orphan` — daemons on 9400 and 9401; state file points at 9400; result is one orphan on 9401.
3. `test_enumerate_skips_non_spec_kitty` — plain `http.server.HTTPServer` on 9402 returning 200 without our keys; not in result.
4. `test_enumerate_skips_closed_ports` — no listener on 9402; not in result.
5. `test_sweep_terminates_orphan` — orphan running; after `sweep_orphans()`, port is closed and the report's `swept` list contains it.
6. `test_sweep_does_not_touch_singleton` — singleton + orphan; only the orphan terminates. Singleton's process is alive after.
7. `test_sweep_records_failure_on_access_denied` — patch `psutil.Process.terminate` to raise `psutil.AccessDenied`; orphan recorded in `failed`.

Use real subprocess-spawned daemons for tests 5/6 (otherwise we can't actually verify port closure). Use `subprocess.Popen([sys.executable, "-c", spawn_script])` and clean up via `proc.terminate()` in a fixture finally block.

**Files**: `tests/sync/test_orphan_sweep.py`.

**Validation**: `pytest tests/sync/test_orphan_sweep.py -v` passes; total runtime ≤ 15 s.

## Definition of Done

- All 4 subtasks complete.
- `mypy --strict` zero errors on `sync/orphan_sweep.py`.
- `ruff check` clean.
- Coverage ≥ 90 % on `sync/orphan_sweep.py`.
- 7 tests in `tests/sync/test_orphan_sweep.py` pass.
- `enumerate_orphans()` 50-port scan completes in ≤ 3 s on the maintainer's reference machine (NFR-006 budget).

## Risks

- **R4** — sweep terminates a non-Spec-Kitty process. Counter-design: identity probe requires both `protocol_version` and `package_version` keys. Anything else is left alone. Test asserts this with a bare `http.server.HTTPServer` returning 200 without our keys.
- **CI port collision**: tests use the live 9400-9450 range; if CI runs them in parallel with another spec-kitty test, ports may collide. Counter: tests use `tmp_path`-scoped fixtures and sequential execution (mark with `pytest.mark.serial` if available).

## Reviewer Guidance

Verify:
1. `enumerate_orphans()` excludes the singleton port (record from state file).
2. `enumerate_orphans()` requires BOTH `protocol_version` AND `package_version` to classify.
3. `sweep_orphans()` escalates HTTP → SIGTERM → SIGKILL with a 1 s wait at each step.
4. `psutil.AccessDenied` is caught and recorded in `SweepReport.failed`, not raised.
5. State-file cleanup is best-effort (no exception if the file is missing).

## Activity Log

- 2026-04-28T10:28:25Z – claude:sonnet:python-pedro:implementer – shell_pid=49283 – Started implementation via action command
- 2026-04-28T10:37:26Z – claude:sonnet:python-pedro:implementer – shell_pid=49283 – Ready for review: orphan sweep module + 8 tests, mypy strict + ruff clean
- 2026-04-28T10:38:19Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=55938 – Started review via action command
- 2026-04-28T10:42:27Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=55938 – Review passed: R4 invariant enforced (both protocol_version + package_version required); singleton excluded; HTTP→terminate→kill escalation with 1s waits; AccessDenied/NoSuchProcess caught and recorded; 50-port scan well under 3s; all 7 contract tests + 1 perf test pass; mypy/ruff/1441 sync tests clean.

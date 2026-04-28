---
work_package_id: WP03
title: Concurrency and multiprocess incident regression tests
dependencies:
- WP01
- WP02
requirement_refs:
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-04-28T09:17:32+00:00'
subtasks:
- T012
- T013
- T014
history:
- at: '2026-04-28T09:17:32Z'
  actor: claude
  action: created
authoritative_surface: tests/auth/concurrency/
execution_mode: code_change
mission_slug: cli-session-survival-daemon-singleton-01KQ9M3M
owned_files:
- tests/auth/concurrency/conftest.py
- tests/auth/concurrency/test_machine_refresh_lock.py
- tests/auth/concurrency/test_stale_grant_preservation.py
- tests/auth/concurrency/test_incident_regression.py
priority: P1
status: planned
tags: []
agent_profile: python-pedro
role: implementer
agent: claude
---

# WP03 — Concurrency and multiprocess incident regression tests

## ⚡ Do This First: Load Agent Profile

Load the assigned agent profile via `/ad-hoc-profile-load <agent_profile>` before any other tool call.

## Objective

Author the concurrency-test surface that verifies WP01+WP02 behavior under cross-process load. Three test files: a same-process concurrent-refresh test (one network call shared between callers), a deterministic stale-grant scenario test (rotate-then-rejection ⇒ session preserved + no clear), and the multiprocess incident regression (two real `subprocess` workers driving the rotate-then-stale-grant ordering against a fake refresh server, bounded ≤ 30 s wall-clock per NFR-005). This is the verification spine of the mission — without it, "the bug is fixed" cannot be asserted.

## Context

The incident is by definition cross-process. In-process tests in `test_token_manager.py` (WP02) cover the logic. WP03 covers the *deployment shape* of the bug: two CLIs in two temp checkouts sharing one auth root. The test must spawn real subprocesses and run end-to-end through the lock primitive (WP01) and the transaction (WP02). The acceptance criterion in `spec.md` Scenario 2 requires this to pass deterministically.

**Key spec references**:
- Scenario 2 (rotate-then-stale-grant) in `spec.md` §"User Scenarios & Acceptance Tests".
- NFR-005: multiprocess regression ≤ 30 s wall-clock on CI.
- SC-002 in `spec.md` §"Success Criteria".

**Key planning references**:
- `research.md` D10 (test design — subprocess + file barriers, no `time.sleep` ordering).
- `quickstart.md` "Reproduce the incident manually" — this WP automates the manual procedure.

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP03`. Depends on WP01 and WP02; the resolver may rebase across both before opening the worktree.

To start work:
```bash
spec-kitty implement WP03
```

## Subtasks

### T012 — `tests/auth/concurrency/conftest.py` — fixtures

**Purpose**: Build the harness that the rest of WP03 reuses. Two essential fixtures: a `tmp_path`-rooted auth-store env override (so tests don't touch `~/.spec-kitty/`), and a fake refresh server that workers can hit without network access.

**Files to create**: `tests/auth/concurrency/conftest.py`, `tests/auth/concurrency/__init__.py`.

**Steps**:
1. `__init__.py` — empty marker so pytest discovers the test directory.
2. Define `auth_store_root(tmp_path, monkeypatch)` fixture:
   - Compute `auth_root = tmp_path / "auth"`; `auth_root.mkdir(parents=True)`.
   - Monkeypatch `Path.home` (or the relevant resolver) to return `tmp_path` so `~/.spec-kitty/auth/refresh.lock` resolves under `tmp_path`.
   - Yield `auth_root`.
3. Define `fake_refresh_server` fixture:
   - Start a `http.server.HTTPServer` thread bound to `127.0.0.1:0`; capture the assigned port.
   - The handler accepts `POST /token` with form-encoded body; uses a per-test request-counter file (`tmp_path / "refresh_counter.txt"`) to decide the response:
     - First call: return rotated tokens (200 with new access + refresh + session_id).
     - Subsequent calls with the OLD refresh token: return `400 {"error":"invalid_grant"}`.
     - Subsequent calls with the NEW refresh token: return another rotation (idempotent).
   - Yield `(server_url, counter_path)`.
   - Teardown: `server.shutdown()`.
4. Define `seed_session(auth_store_root)` fixture: writes a `StoredSession` to `auth_store_root / "session.json"` (using the existing `SecureStorage` interface) so workers find a valid initial session at startup.

**Validation**: a no-op `test_fixtures_smoke.py::test_fixtures_load` that imports both fixtures and asserts they instantiate cleanly.

### T013 — `test_machine_refresh_lock.py` and `test_stale_grant_preservation.py`

**Purpose**: Two deterministic single-process tests that exercise the cross-process lock and the stale-grant reconciler. These run inside one pytest process (using `asyncio.gather` across two `TokenManager` instances) — no subprocess. They are fast (< 5 s each) and form the first line of regression defence.

**Files to create**:
- `tests/auth/concurrency/test_machine_refresh_lock.py`
- `tests/auth/concurrency/test_stale_grant_preservation.py`

**Steps**:

**`test_machine_refresh_lock.py`**:
1. `test_concurrent_refresh_one_network_call` — two `TokenManager` instances pointed at the same `auth_store_root`; both await `refresh_if_needed()` concurrently via `asyncio.gather`; assert the fake refresh server's request counter is exactly `1`; assert both managers end up holding the rotated token.
2. `test_concurrent_refresh_serializes_through_machine_lock` — same setup, but instrument the lock acquire path to record the order of `__aenter__` calls; assert they are not interleaved (one fully completes before the other begins).

**`test_stale_grant_preservation.py`**:
1. `test_stale_rejection_preserves_session` — two `TokenManager` instances; A rotates first; then B (still holding old refresh token in memory) calls `refresh_if_needed()`; the fake server returns `invalid_grant` for B's old token; assert B's `_session` is now the rotated session (matching what A wrote), NOT `None`; assert `auth_store_root / "session.json"` still exists and contains A's rotated material.
2. `test_current_rejection_clears_with_message` — A's session has been server-revoked; the fake server returns `invalid_grant` for A's current refresh token; assert A's `_session` becomes `None`; assert `RefreshTokenExpiredError` is raised; assert the `caplog` records a single user-readable line containing "spec-kitty auth login".

**Validation**: `pytest tests/auth/concurrency/test_machine_refresh_lock.py tests/auth/concurrency/test_stale_grant_preservation.py -v` passes deterministically across 50 consecutive runs. (Use `pytest-repeat` or a manual loop in CI to confirm stability.)

### T014 — `test_incident_regression.py` — multiprocess subprocess-based

**Purpose**: Reproduce the original incident at the deployment shape: two real Python subprocesses, each acting as a "CLI from a temp checkout", sharing one `tmp_path`-rooted auth store, driving the rotate-then-stale-grant ordering through file-system barriers. This is the canonical regression test for SC-002 and `spec.md` Scenario 2.

**Files to create**: `tests/auth/concurrency/test_incident_regression.py`.

**Steps**:
1. Author a `worker_a_script` and `worker_b_script` as inline strings, each invoked via `subprocess.Popen([sys.executable, "-c", script], env=...)`.
2. Pre-arrange:
   - `auth_root = tmp_path / "auth"`, populated with a starter session whose access token expires in 1 s.
   - `barrier_dir = tmp_path / "barriers"`.
   - Fake refresh server (from T012) running on a known port.
3. **Worker A** script:
   - Wait for access-token expiry (1 s sleep).
   - Call `await TokenManager.refresh_if_needed()` (rotates token A→B via the fake server).
   - Touch `barrier_dir / "rotated.flag"`.
   - Exit 0.
4. **Worker B** script:
   - Load the `TokenManager` from disk BEFORE the rotation (its in-memory `_session` carries the OLD refresh token A).
   - `while not (barrier_dir / "rotated.flag").exists(): time.sleep(0.1)` — wait for A to rotate.
   - Call `await TokenManager.refresh_if_needed()`.
   - Exit 0 (success path: stale-grant preserved) or 1 (failure: session was cleared).
5. Test orchestrator:
   - Spawn A then B in that order.
   - `wait_for(processes_finish, timeout=30.0)` — NFR-005 ceiling.
   - Assert both exit 0.
   - Assert `auth_root / "session.json"` exists and contains the rotated session.
   - Assert the fake refresh server saw exactly two requests (A's rotation + B's stale-grant attempt).
6. **Skip on Windows**: `pytest.mark.skipif(sys.platform == "win32", reason="subprocess + file barriers tested on POSIX; Windows path covered by WP01 platform test")`.

**Files**: `tests/auth/concurrency/test_incident_regression.py`.

**Validation**: `pytest tests/auth/concurrency/test_incident_regression.py -v` passes in ≤ 30 s.

**Edge cases**:
- If Worker B starts BEFORE Worker A finishes loading the session: that's a different scenario (concurrent refresh, not stale grant); not what this test verifies. The barrier guarantees ordering.
- If the fake server doesn't see exactly two requests: indicates either lock-contention behavior or a regression in the reconciler. Test fails loudly.

## Definition of Done

- All 3 subtasks complete.
- `pytest tests/auth/concurrency -v` passes deterministically.
- T013 stable across 50 consecutive runs.
- T014 passes in < 30 s on the maintainer's reference machine.
- `mypy --strict` zero errors.
- `ruff check` clean.

## Risks

- **R5** — multiprocess test flake on slow CI. Counter: file-barrier sequencing only, no `time.sleep`-based ordering, hard 30 s cap.
- **Subprocess stability**: each worker imports `specify_cli` fresh; if test environment doesn't have the editable install, workers fail. Counter: assert `pip show spec-kitty-cli` succeeds in the test fixture or use `PYTHONPATH=src`.

## Reviewer Guidance

Verify:
1. The fake refresh server is bound to `127.0.0.1:0` (auto-assigned port) — never a fixed port that could collide on CI.
2. T014 uses **file barriers** for ordering, never `time.sleep`.
3. T014's 30 s timeout is enforced via `wait_for`, not via a soft sleep.
4. No worker script writes outside `tmp_path`.
5. The fake server's `invalid_grant` response shape matches the SaaS's actual response shape (same JSON keys).

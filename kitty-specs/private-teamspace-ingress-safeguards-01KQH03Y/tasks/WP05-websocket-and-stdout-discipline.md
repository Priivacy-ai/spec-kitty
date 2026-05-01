---
work_package_id: WP05
title: Websocket Client Strict Resolver + Stdout Discipline + Strict-JSON Regression
dependencies:
- WP01
- WP02
- WP04
requirement_refs:
- FR-002
- FR-004
- FR-006
- FR-009
- FR-010
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
created_at: '2026-05-01T06:33:00+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: "codex:gpt-5:reviewer-renata:reviewer"
shell_pid: "58823"
history:
- date: '2026-05-01'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/client.py
- tests/sync/test_client_integration.py
- tests/sync/test_strict_json_stdout.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Three concerns, all centered on `src/specify_cli/sync/client.py`:

1. **Websocket ws-token provisioning** uses the strict resolver via `sync/_team.resolve_private_team_id_for_ingress` so it never posts a shared team id to `/api/v1/ws-token` (FR-006, AC-005).
2. **Stdout discipline (FR-009 / AC-006 / NFR-003)**: the six existing `print()` calls in this file go through `logging` instead, so strict-JSON command output (`spec-kitty agent mission create --json`) is never corrupted by sync diagnostics.
3. **Strict-JSON regression test**: a new end-to-end test asserts that `spec-kitty agent mission create … --json` produces stdout parseable by `json.loads(...)` even when sync would otherwise fail.

This WP also installs a small invariant test that any new `print()` in `src/specify_cli/sync/client.py` fails CI. (The invariant is intentionally scoped to `client.py`; other sync-package files contain legitimate prints for interactive CLI commands and are out of scope.)

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP05 --agent <name>`; do not guess the worktree path

## Context

### Why this exists

During the specify and plan phases of this mission the SaaS-rejection error printed itself **directly into the stdout** of strict-JSON commands:

```
{"result": "success", "mission_id": "...", ...}
❌ Connection failed: Forbidden: Direct sync ingress must target Private Teamspace.
```

That second line is from `src/specify_cli/sync/client.py:146` (and similar prints at lines 141, 178, 184, 186, 193). Any consumer that runs `json.loads(stdout)` blows up with `Extra data`. Routing those messages to `logging.warning` (default Python logger handler writes to stderr) is the spec-mandated fix.

The websocket-target side of the same file resolves a team id today via `session.default_team_id`. WP04 introduced the shared `resolve_private_team_id_for_ingress` helper; this WP wires the websocket call site to it.

### Existing code surface

- `src/specify_cli/sync/client.py:101..113` — current ws-token target resolution. Replace.
- `src/specify_cli/sync/client.py:141, 146, 178, 184, 186, 193` — six `print()` calls. Convert.
- `src/specify_cli/sync/_team.py` — delivered in WP04; reuse `resolve_private_team_id_for_ingress`.

### Spec references

- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md` — FR-002, FR-004, FR-006, FR-009, FR-010, NFR-003, AC-005, AC-006
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md` §4 (helper) and §5 (stdout discipline)
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/research.md` R-01, R-02

## Scope guardrail (binding)

This WP MUST NOT:

- Add `print()` to **any** file in `src/specify_cli/sync/`.
- Change the websocket protocol shape (heartbeat, reconnect, ping intervals).
- Touch `auth/`, `_team.py`, or other call sites — those are owned by WP01–WP04.
- Add `rich.print` as a substitute for `print` (writes to stdout by default — same bug).

This WP MUST:

- Use `logging.getLogger(__name__)` consistently with `sync/background.py`'s pattern.
- Preserve ws connect/disconnect/listen behavior end-to-end.
- Keep `mypy --strict` green for `client.py`.
- Make the strict-JSON regression test deterministic (no flake).

## Subtasks

### T020 — Update `sync/client.py` ws-token provisioning to use the shared helper

**Purpose**: Same change as WP04, applied to the websocket-token call site.

**Steps**:

1. Read `src/specify_cli/sync/client.py:80..130` to understand the current ws-token request flow.
2. Replace the team-id resolution (around line 101) with the **sync** helper call (no `await` — the helper is sync; calling it inline from inside this async websocket function is fine, the resolver does not yield to the event loop):

   ```python
   from specify_cli.sync._team import resolve_private_team_id_for_ingress

   team_id = resolve_private_team_id_for_ingress(
       self._token_manager,  # or the equivalent attribute name in this file
       endpoint="/api/v1/ws-token",
   )
   if team_id is None:
       # Already logged inside the helper. Skip provisioning entirely.
       self.connected = False
       self.status = ConnectionStatus.OFFLINE
       return  # do not raise; the local command must still succeed (FR-010)
   ```

3. Use `team_id` as the value posted in the `/api/v1/ws-token` request body (replace the existing `session.default_team_id` reference).
4. Confirm: no remaining reference to `session.default_team_id` in `client.py` for ingress purposes.

**Files**:

- `src/specify_cli/sync/client.py` — modify the ws-token resolution and provisioning calls.

**Validation**:

- [ ] `grep -n "default_team_id" src/specify_cli/sync/client.py` returns zero ingress-relevant matches.
- [ ] `mypy --strict` passes.

---

### T021 — Replace 6 `print()` calls in `sync/client.py` with `logger` calls

**Purpose**: Stop emitting `❌ Connection failed: …`, `❌ Token refresh failed: …`, `✅ Connected to sync server`, and the WebSocket-rejected message to stdout. Route each to the appropriate `logger.{warning,error,info}` level so they go to stderr / structured logs.

**Steps**:

1. At the top of `src/specify_cli/sync/client.py`, ensure:

   ```python
   import logging

   logger = logging.getLogger(__name__)
   ```

   (Match the convention in `src/specify_cli/sync/background.py` exactly.)

2. Convert each call:

   | Line | Current | Replacement |
   |------|---------|-------------|
   | 141 | `print(f"❌ Token refresh failed: {exc}")` | `logger.error("Token refresh failed: %s", exc)` |
   | 146 | `print(f"❌ Connection failed: {exc}")` | `logger.warning("Sync WebSocket connection failed: %s", exc)` |
   | 178 | `print("✅ Connected to sync server")` | `logger.info("Connected to sync server")` |
   | 184 | `print("❌ WebSocket rejected token. Please re-authenticate.")` | `logger.warning("WebSocket rejected token; user should re-authenticate")` |
   | 186 | `print(f"❌ Connection failed: HTTP {e.response.status_code}")` | `logger.warning("Sync WebSocket connection failed: HTTP %s", e.response.status_code)` |
   | 193 | `print(f"❌ Connection failed: {e}")` | `logger.warning("Sync WebSocket connection failed: %s", e)` |

   - Use `%s` formatting (lazy, recommended by `logging`), not f-strings, in the message argument. Pass exception objects as additional arguments.
   - Drop the leading emoji decorations — they are not part of the contract and would be visually awkward in structured logs.

3. After conversion, the file must contain **zero** `print()` calls. Run:

   ```bash
   grep -n '\bprint\s*(' src/specify_cli/sync/client.py
   ```

   The result must be empty.

**Files**:

- `src/specify_cli/sync/client.py` — six line-level changes plus the logger import.

**Validation**:

- [ ] `grep -n '\bprint\s*(' src/specify_cli/sync/client.py` returns no matches.
- [ ] `mypy --strict` and `ruff check` pass.
- [ ] No behavior change other than where the messages are written.

---

### T022 — Tests for ws-token rehydrate paths in `test_client_integration.py`

**Purpose**: Cover the websocket call site analogous to T018 for batch.

**Steps**:

1. Add to `tests/sync/test_client_integration.py`:

   ```python
   @pytest.mark.asyncio
   @respx.mock
   async def test_ws_token_rehydrates_when_session_lacks_private(token_manager_with_shared_only_session):
       """AC-002 + AC-005: shared-only session triggers /api/v1/me rehydrate;
       on success, /api/v1/ws-token receives the private id."""
       me_route = respx.get("https://saas/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={
                   "email": "u@example.com",
                   "teams": [{"id": "t-private", "is_private_teamspace": True}],
               },
           )
       )
       wstoken_route = respx.post("https://saas/api/v1/ws-token").mock(
           return_value=httpx.Response(
               200,
               json={"ws_url": "wss://saas/ws", "ws_token": "ws-tok"},
           )
       )

       await connect_sync_client(token_manager_with_shared_only_session)  # existing helper

       assert me_route.call_count == 1
       assert wstoken_route.call_count == 1
       assert wstoken_route.calls[0].request.read().decode() == '{"team_id": "t-private"}' or "t-private" in wstoken_route.calls[0].request.read().decode()


   @pytest.mark.asyncio
   @respx.mock
   async def test_ws_token_skipped_when_no_private_team_after_rehydrate(token_manager_with_shared_only_session, caplog):
       """AC-005: shared-only session, rehydrate returns no private => no ws-token POST."""
       respx.get("https://saas/api/v1/me").mock(
           return_value=httpx.Response(
               200,
               json={"email": "u@example.com", "teams": [{"id": "t-shared", "is_private_teamspace": False}]},
           )
       )
       wstoken_route = respx.post("https://saas/api/v1/ws-token").mock(
           return_value=httpx.Response(200, json={})
       )

       await connect_sync_client(token_manager_with_shared_only_session)

       assert wstoken_route.call_count == 0
       assert any(
           rec.getMessage().startswith("direct ingress skipped") and "/api/v1/ws-token" in rec.getMessage()
           for rec in caplog.records
       )


   @pytest.mark.asyncio
   @respx.mock
   async def test_ws_token_healthy_session_no_rehydrate(token_manager_with_private_session):
       """Scenario 1 regression: healthy session => no /api/v1/me call."""
       me_route = respx.get("https://saas/api/v1/me").mock(return_value=httpx.Response(200, json={}))
       wstoken_route = respx.post("https://saas/api/v1/ws-token").mock(
           return_value=httpx.Response(200, json={"ws_url": "wss://saas/ws", "ws_token": "ws-tok"})
       )

       await connect_sync_client(token_manager_with_private_session)

       assert me_route.call_count == 0
       assert wstoken_route.call_count == 1
   ```

2. The `connect_sync_client(...)` helper should be the existing test helper that drives `client.py`'s connect flow. If none exists, drive it via `await client.connect()` directly.
3. The exact body shape of the `/api/v1/ws-token` POST is whatever the current implementation already sends — preserve it; just assert the team-id field carries the private id.

**Files**:

- `tests/sync/test_client_integration.py` — add 3 test functions.

**Validation**:

- [ ] All three tests pass.
- [ ] No pre-existing tests in this file regress.

---

### T023 — Strict-JSON regression test (`tests/sync/test_strict_json_stdout.py`)

**Purpose**: End-to-end proof of AC-006 / NFR-003: a `--json` CLI command remains strict-JSON parseable on stdout when the daemon would otherwise print sync diagnostics.

**Steps**:

1. Create `tests/sync/test_strict_json_stdout.py`:

   ```python
   """End-to-end strict-JSON contract tests for --json CLI output.

   These tests subprocess-invoke the actual `spec-kitty` CLI with sync forced into
   the failure path. They assert that:
     - stdout is exactly one JSON object (parseable by json.loads),
     - the structured 'direct ingress skipped' diagnostic appears on stderr.

   Spec: kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md AC-006, NFR-003.
   """

   from __future__ import annotations

   import json
   import os
   import subprocess
   import sys

   import pytest


   def _run_cli(args: list[str], env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
       env = os.environ.copy()
       env["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"
       if env_overrides:
           env.update(env_overrides)
       return subprocess.run(
           [sys.executable, "-m", "specify_cli", *args],
           env=env,
           capture_output=True,
           text=True,
           check=False,
       )


   def test_mission_create_json_strict_when_sync_would_print_diagnostic(tmp_path, isolated_shared_only_session):
       """spec-kitty agent mission create --json must yield stdout parseable by json.loads
       even when the sync daemon's WebSocket connection fails."""
       result = _run_cli(
           [
               "agent",
               "mission",
               "create",
               "wp05-strict-json-smoke",
               "--friendly-name",
               "WP05 Smoke",
               "--purpose-tldr",
               "Smoke",
               "--purpose-context",
               "Strict-JSON contract regression test.",
               "--json",
           ],
           env_overrides=isolated_shared_only_session,
       )
       assert result.returncode == 0, f"Local command should succeed; stderr={result.stderr!r}"

       # Strict-JSON contract: exactly one JSON object on stdout
       parsed = json.loads(result.stdout)
       assert parsed.get("result") == "success"

       # Structured diagnostic must appear on stderr (not stdout)
       assert "direct ingress skipped" in result.stderr or "direct_ingress_missing_private_team" in result.stderr
       assert "❌ Connection failed" not in result.stdout
       assert "Connection failed" not in result.stdout
   ```

2. Implement the `isolated_shared_only_session` fixture in `tests/sync/conftest.py` (or local conftest). It must:
   - Point `SPEC_KITTY_HOME` (or whatever env var the CLI uses to locate auth state) at a temp directory
   - Pre-populate that directory with a `StoredSession` whose `teams` list has only shared teams
   - Point the SaaS base URL at a local `respx`-driven mock server, OR use a simulator harness that intercepts before the network
   - Return the env dict to overlay on the subprocess environment

3. The test asserts:
   - Exit code 0 (FR-010 — local command succeeds)
   - `json.loads(stdout)` succeeds (NFR-003)
   - Stderr contains the structured-warning category
   - Stdout contains no `Connection failed` text

**Files**:

- `tests/sync/test_strict_json_stdout.py` (new file).
- `tests/sync/conftest.py` — fixture only if the existing one does not already provide this.

**Validation**:

- [ ] Test passes locally and in CI.
- [ ] Test does not require network access.
- [ ] Test is deterministic (same outcome on every run).

---

### T024 — Invariant test: no `print()` in `sync/client.py`

**Purpose**: Lock down FR-009 for the precise file whose `print()` calls leaked into agent-command stdout. Any future contributor who adds `print()` to `src/specify_cli/sync/client.py` fails CI.

**Scope note**: This invariant is **scoped to `client.py` only**, not the whole sync package. Other sync modules (`diagnose.py`, `config.py`, `project_identity.py`, `batch.py`, `queue.py`, `emitter.py`) contain legitimate `print`/`console.print` calls for interactive CLI command surfaces (e.g., `spec-kitty sync diagnose` runs as the user's foreground command, not as background sync during a `--json` agent command). Widening the invariant to those files would require an unrelated mass cleanup that is out of scope for this mission.

**Steps**:

1. Add to `tests/sync/test_strict_json_stdout.py` (same file — keeps the discipline tests together):

   ```python
   def test_no_print_calls_in_sync_client():
       """FR-009 invariant: src/specify_cli/sync/client.py must not call print().

       client.py is the precise file whose prints can leak into agent-command stdout
       (the websocket connect path runs alongside any agent invocation when sync is
       enabled). All client.py diagnostics MUST go through logging.

       Other sync-package files contain legitimate print() calls for interactive
       CLI command surfaces and are intentionally out of this invariant's scope.
       """
       import pathlib
       import re

       client_path = (
           pathlib.Path(__file__).resolve().parents[2]
           / "src" / "specify_cli" / "sync" / "client.py"
       )
       assert client_path.is_file(), f"sync/client.py not found at {client_path}"

       offenders: list[tuple[int, str]] = []
       pattern = re.compile(r"\bprint\s*\(")
       for lineno, line in enumerate(client_path.read_text().splitlines(), start=1):
           stripped = line.strip()
           if stripped.startswith("#"):
               continue
           if pattern.search(line):
               offenders.append((lineno, line.strip()))

       assert not offenders, (
           "print() calls detected in src/specify_cli/sync/client.py — route through logging instead.\n"
           + "\n".join(f"  client.py:{ln}  {src}" for ln, src in offenders)
       )
   ```

2. The path resolution assumes the test file lives at `tests/sync/test_strict_json_stdout.py` and that the source is reachable as `src/specify_cli/sync/client.py`. Adjust the `parents[2]` index if the project layout differs.
3. Pattern `\bprint\s*\(` matches both `print(...)` and `rich.print(...)` — both write to stdout by default.

**Files**:

- `tests/sync/test_strict_json_stdout.py` — add 1 test function.

**Validation**:

- [ ] Test passes after T021's print-to-logger conversion.
- [ ] Adding any `print()` to `src/specify_cli/sync/` causes the test to fail with the exact line numbers.

---

## Definition of Done

- [ ] `sync/client.py` ws-token provisioning uses `resolve_private_team_id_for_ingress`.
- [ ] Six `print()` calls in `sync/client.py` are now `logger.*` calls.
- [ ] `grep -n '\bprint\s*(' src/specify_cli/sync/` returns zero matches.
- [ ] `tests/sync/test_client_integration.py` has 3 new tests, all green.
- [ ] `tests/sync/test_strict_json_stdout.py` exists with `test_mission_create_json_strict_*` and `test_no_print_calls_in_sync_client`, both green.
- [ ] `mypy --strict` and `ruff check` green for the touched files.
- [ ] Coverage on new code ≥ 90%.

## Risks & reviewer guidance

| Risk | Mitigation |
|------|------------|
| `tests/sync/test_strict_json_stdout.py` flakes because the subprocess inherits the developer's real auth session | The fixture `isolated_shared_only_session` MUST point env vars at a temp directory and pre-populate it; do not rely on real auth state |
| Subprocess invocation discovers a different `spec-kitty` (system install, etc.) | Use `sys.executable -m specify_cli` so the test always runs the editable install in-tree |
| Future contributor adds a `rich.print(...)` call | T024's regex matches `\bprint\s*\(`, which catches `rich.print(...)` too. Reviewer should confirm this regression is also blocked. |
| `logger.info("Connected …")` is silent under default log levels | Acceptable — operators who want it can lift the log level. The previous `print` was loud but on the wrong stream; logging is the contract (FR-009). |
| Subprocess test is slow | One test taking ~1–2 s in CI is acceptable; document in the test docstring. |

**Reviewer should verify**:

- The strict-JSON test runs the subprocess with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and a fixture that injects a shared-only session with no real network access.
- No `rich.print` substitutes were introduced.
- The invariant test (T024) actually fails when the implementation forgets to convert one of the six prints.

---

## Implementation command (after dependencies satisfied)

```bash
spec-kitty agent action implement WP05 --agent <name>
```

This WP depends on **WP01** (`require_private_team_id`), **WP02** (`rehydrate_membership_if_needed`), and **WP04** (`sync/_team.resolve_private_team_id_for_ingress`).

## Activity Log

- 2026-05-01T11:12:14Z – claude:sonnet:python-pedro:implementer – shell_pid=41984 – Started implementation via action command
- 2026-05-01T11:28:35Z – claude:sonnet:python-pedro:implementer – shell_pid=41984 – Ready for review: ws-token strict resolver + 6 prints→logger + 3 ws tests + strict-JSON regression + no-print invariant for client.py.
- 2026-05-01T11:29:09Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=50931 – Started review via action command
- 2026-05-01T11:33:13Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=50931 – Moved to planned
- 2026-05-01T11:33:28Z – claude:sonnet:python-pedro:implementer – shell_pid=52949 – Started implementation via action command
- 2026-05-01T11:38:49Z – claude:sonnet:python-pedro:implementer – shell_pid=52949 – Cycle 1 fix: strict-JSON test now exercises mission create --json with sync enabled and isolated home/cache; subprocess uses sys.executable -m to resolve in-tree package.
- 2026-05-01T11:39:23Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=53590 – Started review via action command
- 2026-05-01T11:45:46Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=53590 – Moved to planned
- 2026-05-01T11:46:58Z – claude:sonnet:python-pedro:implementer – shell_pid=55436 – Started implementation via action command
- 2026-05-01T11:59:18Z – claude:sonnet:python-pedro:implementer – shell_pid=55436 – Cycle 2 fix: subprocess test now forces PYTHONPATH=worktree/src for in-tree package, seeds shared-only StoredSession in isolated SPEC_KITTY_HOME so sync attempts and fails with structured stderr warning, asserts strict-JSON stdout + 'direct ingress skipped' on stderr.
- 2026-05-01T11:59:44Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=58823 – Started review via action command
- 2026-05-01T12:05:08Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=58823 – Review passed: ws-token provisioning now uses the strict Private Teamspace resolver, sync/client.py emits diagnostics via logging instead of stdout, and the WP05 regression tests pass.

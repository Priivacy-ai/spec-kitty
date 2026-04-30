---
work_package_id: WP04
title: Auth Doctor --server Flag
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-017
planning_base_branch: auth-tranche-2-5-cli-contract-consumption
merge_target_branch: auth-tranche-2-5-cli-contract-consumption
branch_strategy: Planning artifacts for this feature were generated on auth-tranche-2-5-cli-contract-consumption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into auth-tranche-2-5-cli-contract-consumption unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
agent: "claude:claude-sonnet-4-6:reviewer:reviewer"
shell_pid: "37871"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_auth_doctor.py
- src/specify_cli/cli/commands/auth.py
- tests/auth/test_auth_doctor_report.py
- tests/auth/test_auth_doctor_offline.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add `auth doctor --server` as an explicit opt-in network path. When invoked, it refreshes the access token if needed, then calls `GET /api/v1/session-status`, and reports `active` vs `needs re-authentication`.

**The default `spec-kitty auth doctor` (no flags) must remain 100% offline and pass all existing offline tests without modification.**

---

## Context

**Repository root**: `/Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty`

**Read before editing**:
- `src/specify_cli/cli/commands/_auth_doctor.py` — full module; particularly `doctor_impl` and `assemble_report`
- `src/specify_cli/cli/commands/auth.py` — the `doctor` typer command (around line 101)

**Key constraint**: `_auth_doctor.py` module docstring explicitly states `C-007`: never makes outbound calls. After this WP, C-007 still holds for the default path. The `--server` flag is the explicit opt-in signal.

**Server contract** (reference: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/session-status.yaml`):
- `GET /api/v1/session-status` — requires valid, unexpired access token as Bearer.
- 200: `{"session_id": "...", "status": "active", "current_generation": N, ...}` — session is live.
- 401: generic error body — expired, revoked, or invalid token. Body does NOT disclose revocation reason.
- The CLI must never expose `token_family_id`, `is_revoked`, or `revocation_reason` (they are absent from the response; `additionalProperties: false`).

**`session_id`** from the 200 response is safe to display (it is not a secret).

**Async concern**: `doctor_impl` is called synchronously from the typer command. To call `_check_server_session()` (async), use `asyncio.run()`. Verify that `doctor_impl` is not itself called from within a running event loop (check `auth.py`'s doctor command — it does not use `asyncio.run()` currently, so adding it here is safe). If there is any risk of being called inside an event loop (e.g., in tests), add a guard: `asyncio.get_event_loop().is_running()` → use `anyio` or a thread.

---

## Branch Strategy

- **Planning base branch**: `auth-tranche-2-5-cli-contract-consumption`
- **Merge target**: `auth-tranche-2-5-cli-contract-consumption`
- **Start command**: `spec-kitty agent action implement WP04 --agent claude`

---

## Subtask T014 — Add `ServerSessionStatus` Dataclass

**File**: `src/specify_cli/cli/commands/_auth_doctor.py`

**Purpose**: Typed container for the result of the server-side session check. Frozen for safety.

**Add near the top of the dataclass section** (after `DoctorReport`):

```python
@dataclass(frozen=True)
class ServerSessionStatus:
    """Result of an opt-in server-side session check (auth doctor --server).

    ``active=True`` means the server confirms the session is live.
    ``session_id`` is safe to display (not a secret).
    ``error`` is a brief human-readable failure reason; never contains
    raw tokens, token_family_id, is_revoked, or revocation_reason.
    """

    active: bool
    session_id: str | None = None
    error: str | None = None
```

Add `ServerSessionStatus` to `__all__`.

**Validation**:
- [ ] `ServerSessionStatus(active=True, session_id="abc")` constructs without error.
- [ ] `ServerSessionStatus(active=False, error="re-authenticate")` constructs without error.
- [ ] The dataclass is frozen (mutation raises `FrozenInstanceError`).

---

## Subtask T015 — Add `_check_server_session()` Async Function

**File**: `src/specify_cli/cli/commands/_auth_doctor.py`

**Purpose**: Perform the refresh-then-check-status sequence. Returns `ServerSessionStatus`. Never raises; maps all failures to `active=False` with a brief error message.

**Implementation**:

```python
async def _check_server_session() -> ServerSessionStatus:
    """Refresh token if needed, then GET /api/v1/session-status.

    Returns ServerSessionStatus. Never raises — all errors map to
    active=False with a brief, non-sensitive error description.
    """
    from specify_cli.auth import get_token_manager  # noqa: PLC0415 (avoid circular at module level)
    from specify_cli.auth.config import get_saas_base_url  # noqa: PLC0415
    import httpx  # noqa: PLC0415

    tm = get_token_manager()
    try:
        access_token = await tm.get_access_token()
    except Exception as exc:
        return ServerSessionStatus(active=False, error=f"Could not obtain access token: {type(exc).__name__}")

    try:
        saas_url = get_saas_base_url()
    except Exception:
        return ServerSessionStatus(active=False, error="SaaS URL not configured")

    url = f"{saas_url}/api/v1/session-status"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError as exc:
        return ServerSessionStatus(active=False, error=f"Network error: {type(exc).__name__}")
    except Exception:
        return ServerSessionStatus(active=False, error="Unexpected error during server check")

    if response.status_code == 200:
        try:
            body = response.json()
            session_id = body.get("session_id")
            return ServerSessionStatus(active=True, session_id=session_id)
        except ValueError:
            return ServerSessionStatus(active=False, error="Invalid response from server")

    if response.status_code == 401:
        return ServerSessionStatus(active=False, error="re-authenticate")

    return ServerSessionStatus(active=False, error=f"Server returned HTTP {response.status_code}")
```

**Security review checklist**:
- [ ] `access_token` is not logged or included in any `ServerSessionStatus.error` string.
- [ ] `ServerSessionStatus.error` for 401 says "re-authenticate" — does not disclose is_revoked, revocation_reason.
- [ ] `session_id` from the response is the only field included from the 200 body.

---

## Subtask T016 — Extend `doctor_impl` with `server: bool = False`

**File**: `src/specify_cli/cli/commands/_auth_doctor.py`

**Purpose**: Gate the server-check behind `server=True`. The default path (server=False) is identical to the current behavior.

**Change to `doctor_impl` signature**:

```python
def doctor_impl(
    *,
    json_output: bool,
    reset: bool,
    unstick_lock: bool,
    stuck_threshold: float,
    server: bool = False,   # ADD THIS
) -> int:
```

**Add at the end of `doctor_impl`**, after the existing `reset` and `unstick_lock` blocks and before the final `render_report` / JSON output:

```python
    server_status: ServerSessionStatus | None = None
    if server:
        server_status = asyncio.run(_check_server_session())
```

**Render the server section** in the non-JSON path:
```python
    if server and server_status is not None:
        console.print("[bold]Server Session[/bold]")
        if server_status.active:
            sid = server_status.session_id or "(unknown)"
            console.print(f"  Status:  [green]active[/green] (session: {sid})")
        else:
            reason = server_status.error or "unknown"
            if reason == "re-authenticate":
                console.print(
                    "  Status:  [red]invalid[/red] — "
                    "Run [bold]spec-kitty auth login[/bold] to re-authenticate."
                )
            else:
                console.print(f"  Status:  [yellow]check failed[/yellow] — {reason}")
        console.print()
```

**For JSON output**, include `server_status` in the payload when present:
```python
    if json_output:
        payload = json.loads(render_report_json(report))
        if server_status is not None:
            payload["server_session"] = {
                "active": server_status.active,
                "session_id": server_status.session_id,
                "error": server_status.error,
            }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return compute_exit_code(report.findings)
```

**Validation**:
- [ ] `doctor_impl(json_output=False, reset=False, unstick_lock=False, stuck_threshold=60.0)` (no `server` arg) still works (default `server=False`).
- [ ] `doctor_impl(..., server=False)` makes zero outbound HTTP calls.
- [ ] `doctor_impl(..., server=True)` calls `asyncio.run(_check_server_session())`.

---

## Subtask T017 — Add Default Doctor Hint

**File**: `src/specify_cli/cli/commands/_auth_doctor.py`

**Purpose**: When the user runs default `auth doctor` (server=False), append a one-line hint at the end of the Findings section.

**Location**: In `render_report`, at the very end of the function, add:

```python
    # Always present in offline mode — encourage server-aware check.
    console.print()
    console.print(
        "[dim]Run [bold]spec-kitty auth doctor --server[/bold] "
        "to verify server session status.[/dim]"
    )
```

This hint appears regardless of whether there are findings, so users know the option exists.

**Note**: Do NOT add the hint when rendering inside `doctor_impl(..., server=True)` (it would be circular). The simplest approach: add a `show_server_hint: bool = True` parameter to `render_report`, defaulting to True. When `server=True` in `doctor_impl`, pass `show_server_hint=False`.

**Validation**:
- [ ] Default `spec-kitty auth doctor` output ends with the hint line.
- [ ] `spec-kitty auth doctor --server` output does NOT show the hint.

---

## Subtask T018 — Wire `--server` Flag in `auth.py`

**File**: `src/specify_cli/cli/commands/auth.py`

**Purpose**: Add the typer option and pass it through to `doctor_impl`.

**Current `doctor` command** (around line 101):
```python
@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", ...),
    reset: bool = typer.Option(False, "--reset", ...),
    unstick_lock: bool = typer.Option(False, "--unstick-lock", ...),
    stuck_threshold: float = typer.Option(60.0, "--stuck-threshold", ...),
) -> None:
```

**Add**:
```python
    server: bool = typer.Option(
        False,
        "--server",
        help="Check live server session status (makes outbound call).",
    ),
```

**Pass to `doctor_impl`**:
```python
    exit_code = doctor_impl(
        json_output=json_output,
        reset=reset,
        unstick_lock=unstick_lock,
        stuck_threshold=stuck_threshold,
        server=server,  # ADD
    )
```

**Validation**:
- [ ] `spec-kitty auth doctor --help` shows `--server` option.
- [ ] `spec-kitty auth doctor` (no flag) passes `server=False` to `doctor_impl`.

---

## Subtask T019 — Add `--server` Tests; Verify Offline Tests Unchanged

**Files**:
- `tests/auth/test_auth_doctor_report.py` — add server-status section tests
- `tests/auth/test_auth_doctor_offline.py` — run to confirm unchanged

**New tests in `test_auth_doctor_report.py`**:

```python
@pytest.mark.asyncio
async def test_check_server_session_active(mock_token_manager, mock_httpx):
    """GET /api/v1/session-status 200 → ServerSessionStatus(active=True, session_id='abc')."""
    # Arrange: mock get_access_token() to return "tok", mock GET to return 200 + {"session_id": "abc", "status": "active"}
    # Act: result = await _check_server_session()
    # Assert: result.active is True, result.session_id == "abc"

@pytest.mark.asyncio
async def test_check_server_session_401(mock_token_manager, mock_httpx):
    """GET /api/v1/session-status 401 → ServerSessionStatus(active=False, error='re-authenticate')."""
    # Assert: result.error == "re-authenticate"
    # Assert: result.error does not contain any token content

@pytest.mark.asyncio
async def test_check_server_session_network_error(mock_token_manager, mock_httpx):
    """Network error → ServerSessionStatus(active=False, error contains type name)."""
    # Assert: result.active is False, result.error is a brief message

def test_doctor_impl_server_false_no_outbound_call(monkeypatch):
    """server=False must not call asyncio.run or _check_server_session."""
    # Monkeypatch asyncio.run to assert it is not called
    # Call doctor_impl(..., server=False)
    # Assert asyncio.run was not called

def test_doctor_impl_server_true_renders_active(monkeypatch):
    """server=True + active session → output contains 'active'."""
    # Monkeypatch _check_server_session to return ServerSessionStatus(active=True, session_id="s1")
    # Call doctor_impl(..., server=True) and capture output
    # Assert output contains "active" and "s1"

def test_doctor_impl_server_true_renders_reauthenticate(monkeypatch):
    """server=True + 401 → output contains 're-authenticate' guidance."""
```

**Verify offline tests** (read-only run, no changes to the file):
```bash
uv run pytest tests/auth/test_auth_doctor_offline.py -v
```

All existing offline tests must pass without modification.

**Validation**:
- [ ] `uv run pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_offline.py -v` passes.
- [ ] No test in `test_auth_doctor_offline.py` was modified.
- [ ] Access token value does not appear in any `ServerSessionStatus.error` string tested.

---

## Definition of Done

- [ ] `ServerSessionStatus` dataclass in `_auth_doctor.py`.
- [ ] `_check_server_session()` async function: refresh + GET + map 200/401/error.
- [ ] `doctor_impl` accepts `server: bool = False`; server-check runs only when True.
- [ ] Default doctor output includes hint line.
- [ ] `auth.py` doctor command has `--server` option wired to `doctor_impl`.
- [ ] `uv run pytest tests/auth/test_auth_doctor_report.py tests/auth/test_auth_doctor_offline.py -v` passes.
- [ ] No modification to files outside `owned_files`.

## Risks

| Risk | Mitigation |
|------|-----------|
| `asyncio.run()` inside running event loop (e.g., pytest-asyncio) | In tests, call `_check_server_session()` directly (it's async); monkeypatch it in sync tests |
| Access token in error messages | All error strings use `type(exc).__name__`, never exc args or token values |
| `additionalProperties: false` means session_id is always present on 200 | Use `.get("session_id")` defensively; test with missing key |
| Default doctor tests assert no outbound calls | `server=False` path never calls `asyncio.run` or `_check_server_session` |

## Activity Log

- 2026-04-30T13:47:24Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=34402 – Started implementation via action command
- 2026-04-30T13:52:48Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=34402 – Ready for review: implemented auth doctor --server flag with ServerSessionStatus dataclass, _check_server_session async function, server=False default keeps C-007 offline invariant, all 30 tests pass
- 2026-04-30T13:53:17Z – claude:claude-sonnet-4-6:reviewer:reviewer – shell_pid=37871 – Started review via action command
- 2026-04-30T13:55:01Z – claude:claude-sonnet-4-6:reviewer:reviewer – shell_pid=37871 – Review passed: ServerSessionStatus frozen dataclass present with correct fields; _check_server_session async function implements refresh-then-check sequence with correct 200/401/network-error mapping; doctor_impl has server=False default maintaining C-007 offline invariant; default output includes --server hint; hint suppressed when --server used; --server flag wired in auth.py; no raw tokens or forbidden fields in any output; WP04 commit touches exactly the 3 owned files; test_auth_doctor_offline.py unchanged (identical MD5); all 25 tests pass including 14 new WP04 server tests

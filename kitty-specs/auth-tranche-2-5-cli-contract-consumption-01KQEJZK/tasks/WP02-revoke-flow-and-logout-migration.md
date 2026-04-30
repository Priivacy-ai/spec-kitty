---
work_package_id: WP02
title: RevokeFlow and Logout Migration
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-011
- FR-016
planning_base_branch: auth-tranche-2-5-cli-contract-consumption
merge_target_branch: auth-tranche-2-5-cli-contract-consumption
branch_strategy: Planning artifacts for this feature were generated on auth-tranche-2-5-cli-contract-consumption. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into auth-tranche-2-5-cli-contract-consumption unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T008
- T020
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "12879"
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/flows/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/flows/revoke.py
- src/specify_cli/cli/commands/_auth_logout.py
- tests/auth/test_revoke_flow.py
- tests/cli/commands/test_auth_logout.py
- tests/auth/integration/test_logout_e2e.py
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

Replace the retired `/api/v1/logout` bearer call with RFC 7009-compliant `/oauth/revoke`. Create a `RevokeFlow` class in `auth/flows/revoke.py` that models the three possible revocation outcomes, rewrite `logout_impl` to use it, and update all tests.

---

## Context

**Repository root**: `/Users/robert/spec-kitty-dev/spec-kitty-20260430-084609-5Y0VM4/spec-kitty`

**Current state** (before this WP):
- `_auth_logout.py` POSTs to `POST /api/v1/logout` with `Authorization: Bearer <access_token>` and no body. This endpoint is retired.
- The `_call_server_logout()` helper is the entire server-call surface to remove.
- Local cleanup (`tm.clear_session()`) is already unconditional — keep it that way.

**Target state**:
- `auth/flows/revoke.py` owns the HTTP call to `POST /oauth/revoke`.
- `RevokeOutcome` enum expresses: `REVOKED`, `SERVER_FAILURE`, `NETWORK_ERROR`, `NO_REFRESH_TOKEN`.
- `logout_impl` calls `RevokeFlow().revoke(session)` and maps the outcome to three distinct output messages.
- Exit code is 0 in all outcomes where local cleanup succeeds.

**Server contract** (reference: `spec-kitty-saas/kitty-specs/saas-cli-token-family-and-revocation-01KQATJN/contracts/revoke.yaml`):
- `POST /oauth/revoke` — no `Authorization` header; token possession is authorization.
- Body: `token=<refresh_token>&token_type_hint=refresh_token` (form-encoded).
- 200 + `{"revoked": true}` for any syntactically valid token (including already-revoked).
- 5xx = genuine server error. Never report as revoked.
- 429 = throttle — treat as `SERVER_FAILURE`.

**Security invariant**: The spent refresh token must never appear in any log line, error message, console output, or exception string.

---

## Branch Strategy

- **Planning base branch**: `auth-tranche-2-5-cli-contract-consumption`
- **Merge target**: `auth-tranche-2-5-cli-contract-consumption`
- **Start command**: `spec-kitty agent action implement WP02 --agent claude`

---

## Subtask T005 — Create `auth/flows/revoke.py`

**File**: `src/specify_cli/auth/flows/revoke.py` (new file)

**Purpose**: Own the RFC 7009 HTTP call. The `RevokeFlow` class is injectable for tests and mirrors the `TokenRefreshFlow` pattern.

**Implementation**:

```python
"""RevokeFlow — RFC 7009 token revocation for spec-kitty auth logout."""
from __future__ import annotations

import logging
from enum import StrEnum

import httpx

from ..config import get_saas_base_url
from ..session import StoredSession

log = logging.getLogger(__name__)

_HTTP_TIMEOUT_SECONDS = 10.0


class RevokeOutcome(StrEnum):
    REVOKED = "revoked"
    """Server confirmed revocation: 200 + {"revoked": true}."""

    SERVER_FAILURE = "server_failure"
    """Server returned 4xx/5xx or unexpected body. NOT revoked."""

    NETWORK_ERROR = "network_error"
    """Transport-level failure (DNS, connect, timeout)."""

    NO_REFRESH_TOKEN = "no_refresh_token"
    """Session has no refresh token; revocation not attempted."""


class RevokeFlow:
    """RFC 7009-compliant token revocation."""

    async def revoke(self, session: StoredSession) -> RevokeOutcome:
        """POST /oauth/revoke with the session's refresh token.

        Never raises. Returns RevokeOutcome so the caller can produce
        accurate output without re-implementing status logic.
        """
        if not session.refresh_token:
            return RevokeOutcome.NO_REFRESH_TOKEN

        saas_url = get_saas_base_url()
        url = f"{saas_url}/oauth/revoke"
        data = {
            "token": session.refresh_token,
            "token_type_hint": "refresh_token",
        }

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(url, data=data)
        except httpx.RequestError as exc:
            log.warning("Revoke network error: %s", type(exc).__name__)
            return RevokeOutcome.NETWORK_ERROR
        except Exception as exc:  # noqa: BLE001
            log.warning("Revoke unexpected error: %s", type(exc).__name__)
            return RevokeOutcome.SERVER_FAILURE

        if response.status_code == 200:
            try:
                body = response.json()
                if body.get("revoked") is True:
                    return RevokeOutcome.REVOKED
            except ValueError:
                pass
            # 200 but unexpected body
            log.warning("Revoke 200 but unexpected body shape")
            return RevokeOutcome.SERVER_FAILURE

        log.warning("Revoke HTTP %d", response.status_code)
        return RevokeOutcome.SERVER_FAILURE


__all__ = ["RevokeFlow", "RevokeOutcome"]
```

**Validation**:
- [ ] `from specify_cli.auth.flows.revoke import RevokeFlow, RevokeOutcome` works.
- [ ] `RevokeOutcome` members: `REVOKED`, `SERVER_FAILURE`, `NETWORK_ERROR`, `NO_REFRESH_TOKEN`.
- [ ] No refresh token content appears in any log call.

---

## Subtask T006 — Rewrite `_auth_logout.py`

**File**: `src/specify_cli/cli/commands/_auth_logout.py`

**Purpose**: Wire `RevokeFlow` into logout, map outcomes to the three required output states, remove `_call_server_logout` entirely.

**Output mapping** (all states):

| Outcome | Console message (informational line) | Exit |
|---------|-------------------------------------|------|
| `REVOKED` | `[green]✓ Server revocation confirmed.[/green]` | 0 |
| `SERVER_FAILURE` | `[yellow]! Server revocation not confirmed (server error). Local credentials will still be deleted.[/yellow]` | 0 |
| `NETWORK_ERROR` | `[yellow]! Server revocation not confirmed (network error). Local credentials will still be deleted.[/yellow]` | 0 |
| `NO_REFRESH_TOKEN` | `[yellow]! Server revocation could not be attempted (no refresh token). Local credentials will still be deleted.[/yellow]` | 0 |
| Local cleanup failure | `[red]✗ Local credentials could not be deleted: {ErrorType}. You may need to delete them manually.[/red]` | **1** |

The final `[green]+ Logged out.[/green]` line runs only when `tm.clear_session()` succeeds.

**Steps**:

1. Remove the `_call_server_logout` function entirely.
2. Add imports: `from specify_cli.auth.flows.revoke import RevokeFlow, RevokeOutcome` and `import typer`.
3. Rewrite `logout_impl`:

```python
async def logout_impl(*, force: bool) -> None:
    tm = get_token_manager()
    session = tm.get_current_session()

    if session is None:
        console.print("[dim]i[/dim] Not logged in.")
        return

    if force:
        console.print("[dim]Skipping server revocation (--force).[/dim]")
    else:
        try:
            saas_url = get_saas_base_url()  # noqa: F841 — validates config
        except ConfigurationError as exc:
            console.print(
                f"[yellow]! Cannot reach SaaS (config error): {exc}. "
                f"Proceeding with local logout only.[/yellow]"
            )
        else:
            outcome = await RevokeFlow().revoke(session)
            _print_revoke_outcome(outcome)

    try:
        tm.clear_session()
    except Exception as exc:
        console.print(
            f"[red]✗ Local credentials could not be deleted: {type(exc).__name__}. "
            f"You may need to delete them manually.[/red]"
        )
        raise typer.Exit(code=1)

    console.print("[green]+ Logged out.[/green]")


def _print_revoke_outcome(outcome: RevokeOutcome) -> None:
    if outcome is RevokeOutcome.REVOKED:
        console.print("[green]✓ Server revocation confirmed.[/green]")
    elif outcome is RevokeOutcome.NO_REFRESH_TOKEN:
        console.print(
            "[yellow]! Server revocation could not be attempted "
            "(no refresh token). Local credentials will still be deleted.[/yellow]"
        )
    elif outcome is RevokeOutcome.NETWORK_ERROR:
        console.print(
            "[yellow]! Server revocation not confirmed (network error). "
            "Local credentials will still be deleted.[/yellow]"
        )
    else:  # SERVER_FAILURE
        console.print(
            "[yellow]! Server revocation not confirmed (server error). "
            "Local credentials will still be deleted.[/yellow]"
        )
```

**`typer.Exit(code=1)` propagation**: `logout_impl` is called via `asyncio.run(logout_impl(...))` in auth.py. `typer.Exit` is an `Exception` subclass; it propagates out of `asyncio.run()` and is caught by typer's command runner, which exits with the given code. No changes to `auth.py` are required.

**Validation**:
- [ ] `_call_server_logout` is gone — no reference to `/api/v1/logout` remains.
- [ ] `tm.clear_session()` is called after the revoke call in all non-`force` paths.
- [ ] `tm.clear_session()` is called in the `force=True` path.
- [ ] `tm.clear_session()` raises → output contains "could not be deleted" and exit code is 1.
- [ ] `tm.clear_session()` succeeds → exit code 0 in all revoke outcomes.

---

## Subtask T007 — Write `tests/auth/test_revoke_flow.py`

**File**: `tests/auth/test_revoke_flow.py` (new file)

**Purpose**: Unit-test `RevokeFlow.revoke()` at the httpx seam.

**Test cases to cover**:

```python
# Fixture: a minimal StoredSession with refresh_token="rfs.sessionid.secret"

@pytest.mark.asyncio
async def test_revoke_200_revoked_true(mock_httpx_post):
    """200 + {"revoked": true} → REVOKED."""

@pytest.mark.asyncio
async def test_revoke_200_unexpected_body(mock_httpx_post):
    """200 + {"status": "ok"} → SERVER_FAILURE (body doesn't match contract)."""

@pytest.mark.asyncio
async def test_revoke_500(mock_httpx_post):
    """5xx → SERVER_FAILURE (never REVOKED)."""

@pytest.mark.asyncio
async def test_revoke_429(mock_httpx_post):
    """429 throttle → SERVER_FAILURE."""

@pytest.mark.asyncio
async def test_revoke_network_error(mock_httpx_post):
    """httpx.ConnectError → NETWORK_ERROR."""

@pytest.mark.asyncio
async def test_revoke_no_refresh_token(session_without_refresh_token):
    """Empty refresh_token → NO_REFRESH_TOKEN, no HTTP call made."""

@pytest.mark.asyncio
async def test_revoke_request_shape(mock_httpx_post):
    """Verify: URL is /oauth/revoke, body has token= and token_type_hint=refresh_token,
    NO Authorization header."""
```

**Mock pattern** (match existing auth test style in `tests/cli/commands/test_auth_logout.py`):
```python
with patch("specify_cli.auth.flows.revoke.httpx.AsyncClient") as mock_client:
    mock_client.return_value.__aenter__.return_value.post = AsyncMock(...)
```

**Validation**:
- [ ] `uv run pytest tests/auth/test_revoke_flow.py -v` passes all cases.
- [ ] The request shape test verifies no `Authorization` header is sent.
- [ ] The body shape test verifies `token_type_hint=refresh_token` is in the POST body.

---

## Subtask T008 — Update `tests/cli/commands/test_auth_logout.py`

**File**: `tests/cli/commands/test_auth_logout.py`

**Purpose**: Remove all assertions on `POST /api/v1/logout`; add assertions for `POST /oauth/revoke` behavior through the CLI runner.

**Changes**:

1. Find every occurrence of `/api/v1/logout` — remove or replace.
2. Update the happy-path test: mock `RevokeFlow.revoke` to return `RevokeOutcome.REVOKED`; assert output contains "Server revocation confirmed".
3. Update the server-failure test: mock `RevokeFlow.revoke` to return `RevokeOutcome.SERVER_FAILURE`; assert output contains "not confirmed" and "still be deleted"; assert exit code 0.
4. Update the network-error test: mock to return `RevokeOutcome.NETWORK_ERROR`.
5. Add a no-refresh-token test: mock to return `RevokeOutcome.NO_REFRESH_TOKEN`; assert output contains "could not be attempted".
6. Add a **local-cleanup-failure test**: mock `tm.clear_session` to raise `OSError("disk full")`; assert output contains "could not be deleted"; assert exit code 1.
7. The `--force` test should still pass (skips revoke call entirely).
8. The "not logged in" test should still pass.

**Mock approach**: Patch `specify_cli.cli.commands._auth_logout.RevokeFlow.revoke` as an `AsyncMock` returning the desired `RevokeOutcome`. For the cleanup-failure test, patch `clear_session` on the token manager returned by `get_token_manager`.

**Validation**:
- [ ] `uv run pytest tests/cli/commands/test_auth_logout.py -v` passes.
- [ ] `grep -r "api/v1/logout" tests/` returns nothing.
- [ ] All four revoke outcome states are covered by at least one test.
- [ ] Local cleanup failure test asserts exit code 1 and error message containing "could not be deleted".

---

---

## Subtask T020 — Update `tests/auth/integration/test_logout_e2e.py`

**File**: `tests/auth/integration/test_logout_e2e.py`

**Purpose**: The e2e logout test exercises the full CLI runner path including the server call. Update it now so that WP02 is independently approvable — leaving it broken until WP05 would block focused integration test runs.

**Steps**:

1. Read the test file to understand the current mock seam and assertion pattern.
2. Update server-call assertions:
   - Old: `POST /api/v1/logout` with `Authorization: Bearer <token>`, no body.
   - New: `POST /oauth/revoke` with form body `token=<refresh_token>&token_type_hint=refresh_token`, **no** `Authorization` header.
3. Update output assertions to match the new messages:
   - Mock 200 + `{"revoked": true}` → assert output contains "Server revocation confirmed"
   - Mock 5xx → assert output contains "not confirmed" and exit code 0
4. The local-cleanup assertion (credentials deleted) remains unchanged.
5. If the test covers `--force`, confirm it still skips the server call.

**Validation**:
- [ ] `uv run pytest tests/auth/integration/test_logout_e2e.py -v` passes.
- [ ] No assertion in the file references `/api/v1/logout` after this change.
- [ ] `grep "api/v1/logout" tests/auth/integration/test_logout_e2e.py` returns no results.

---

## Definition of Done

- [ ] `src/specify_cli/auth/flows/revoke.py` exists with `RevokeFlow` and `RevokeOutcome`.
- [ ] `_auth_logout.py` uses `RevokeFlow`; `_call_server_logout` removed; `tm.clear_session()` wrapped in try/except with exit 1 on failure.
- [ ] No reference to `/api/v1/logout` remains in source or tests.
- [ ] `uv run pytest tests/auth/test_revoke_flow.py tests/cli/commands/test_auth_logout.py tests/auth/integration/test_logout_e2e.py -v` passes.
- [ ] Local cleanup failure test in `test_auth_logout.py` asserts exit code 1.
- [ ] No modification to files outside `owned_files`.

## Risks

| Risk | Mitigation |
|------|-----------|
| 5xx reported as REVOKED | Explicit `body.get("revoked") is True` check; any other path is SERVER_FAILURE |
| Refresh token in log output | `log.warning` calls use `type(exc).__name__`, never token content |
| `typer.Exit` not caught by asyncio.run caller | typer catches `typer.Exit` at the command boundary; it propagates through asyncio.run correctly |
| `clear_session()` currently never raises | Wrap it anyway — the contract is "if it raises, exit 1"; defensive future-proofing |
| Test patches wrong symbol | Patch `specify_cli.cli.commands._auth_logout.RevokeFlow` (where it is used, not where it is defined) |
| Integration test mock seam differs | Read the test file before editing; match the existing httpx or subprocess mock pattern |

## Activity Log

- 2026-04-30T13:13:48Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=12879 – Started implementation via action command

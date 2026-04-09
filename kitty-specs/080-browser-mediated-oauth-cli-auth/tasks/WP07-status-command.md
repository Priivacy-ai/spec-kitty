---
work_package_id: WP07
title: Status Command (`auth status`)
dependencies:
- WP01
- WP04
requirement_refs:
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
history: []
authoritative_surface: src/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_auth_status.py
- tests/cli/commands/test_auth_status.py
status: pending
tags: []
agent: "claude:opus-4-6:python-implementer:implementer"
shell_pid: "63419"
---

# WP07: Status Command (`auth status`)

**Objective**: Implement the `_auth_status.py` module that the dispatch shell
in `cli/commands/auth.py` (owned by WP04) imports lazily. The status command
displays the authenticated user, teams, access token expiry, refresh token
expiry, storage backend, session ID, and last-used time.

**Context**: WP04's dispatch shell imports `_auth_status.status_impl` lazily
when `spec-kitty auth status` is invoked. This WP provides that module.

**WP07 owns ONLY** `_auth_status.py` and its test file. WP07 does NOT touch
`cli/commands/auth.py` (owned by WP04).

**Acceptance Criteria**:
- [ ] `from specify_cli.cli.commands._auth_status import status_impl` works after this WP
- [ ] When authenticated: prints user, teams (with default marker), access token expiry, refresh token expiry, storage backend, session ID, last_used_at
- [ ] When not authenticated: prints "Not authenticated" and a recovery message
- [ ] Access token expiry is displayed in human-readable form: "59 minutes remaining", "2 hours remaining", "expired"
- [ ] Refresh token expiry is shown in days: "expires in 87 days"
- [ ] Storage backend is shown as "macOS Keychain", "Windows Credential Manager", "Secret Service", or "File fallback (encrypted)"
- [ ] Exit code is 0 in both authenticated and not-authenticated cases (status is informational)
- [ ] All unit + CliRunner tests pass

---

## Subtask Guidance

### T037: Create `cli/commands/_auth_status.py` with status_impl

**Purpose**: The implementation function that the dispatch shell calls.

**Steps**:

1. Create `src/specify_cli/cli/commands/_auth_status.py`:
   ```python
   """Implementation of `spec-kitty auth status`. Owned by WP07."""
   from __future__ import annotations
   from datetime import datetime, timezone
   from rich.console import Console
   from specify_cli.auth import get_token_manager
   from specify_cli.auth.session import StoredSession

   console = Console()


   def status_impl() -> None:
       """Print the current authentication status."""
       tm = get_token_manager()
       session = tm.get_current_session()

       if session is None:
           console.print("[red]✗ Not authenticated[/red]")
           console.print("  Run [bold]spec-kitty auth login[/bold] to authenticate.")
           return

       if session.is_refresh_token_expired():
           console.print("[red]✗ Session expired (refresh token expired)[/red]")
           console.print("  Run [bold]spec-kitty auth login[/bold] to re-authenticate.")
           return

       console.print("[green]✓ Authenticated[/green]")
       console.print()
       console.print(f"  User:           {session.email}")
       if session.name and session.name != session.email:
           console.print(f"  Name:           {session.name}")
       console.print(f"  User ID:        {session.user_id}")
       console.print()

       _print_teams(session)
       console.print()

       _print_token_expiry(session)
       console.print()

       _print_storage_backend(session)
       console.print(f"  Session ID:     {session.session_id}")
       console.print(f"  Last used:      {_format_iso(session.last_used_at)}")
       console.print(f"  Auth method:    {session.auth_method}")


   def _print_teams(session: StoredSession) -> None:
       if not session.teams:
           console.print("  Teams:          (none)")
           return
       console.print("  Teams:")
       for team in session.teams:
           is_default = team.id == session.default_team_id
           marker = " [dim](default)[/dim]" if is_default else ""
           console.print(f"    • {team.name} ({team.role}){marker}")


   def _print_token_expiry(session: StoredSession) -> None:
       now = datetime.now(timezone.utc)
       access_remaining = (session.access_token_expires_at - now).total_seconds()
       console.print(f"  Access token:   {format_duration(access_remaining)}")
       # Refresh token: per C-012 the CLI reads the expiry verbatim from the
       # SaaS response (landed 2026-04-09). The None branch is retained only
       # as a defensive fallback for replayed/legacy sessions stored before
       # the amendment landed; new sessions always carry a concrete datetime.
       if session.refresh_token_expires_at is None:
           console.print(
               "  Refresh token:  [dim]server-managed (legacy session — "
               "re-login to populate refresh expiry)[/dim]"
           )
       else:
           refresh_remaining = (session.refresh_token_expires_at - now).total_seconds()
           console.print(f"  Refresh token:  {format_duration(refresh_remaining)}")


   def _print_storage_backend(session: StoredSession) -> None:
       label = format_storage_backend(session.storage_backend)
       console.print(f"  Storage:        {label}")


   def _format_iso(dt: datetime) -> str:
       return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
   ```

2. The functions `format_duration` and `format_storage_backend` are defined
   in T038 and T039 respectively. Add them to `_auth_status.py` directly
   (no separate utility module).

**Files**: `src/specify_cli/cli/commands/_auth_status.py` (~120 lines initially, grows in T038/T039)

**Validation**:
- [ ] Module imports cleanly
- [ ] Status output matches the format in the spec §2.4

---

### T038: Add human-readable duration formatter

**Purpose**: Convert seconds-until-expiry into a human-readable string.

**Steps**:

1. Add to `src/specify_cli/cli/commands/_auth_status.py`:
   ```python
   def format_duration(seconds: float) -> str:
       """Convert seconds to a human-readable duration string.

       Examples:
           format_duration(-100) -> "expired"
           format_duration(45) -> "expires in 45 seconds"
           format_duration(120) -> "expires in 2 minutes"
           format_duration(3600) -> "expires in 1 hour"
           format_duration(7200) -> "expires in 2 hours"
           format_duration(86400) -> "expires in 1 day"
           format_duration(86400 * 87) -> "expires in 87 days"
       """
       if seconds <= 0:
           return "[red]expired[/red]"
       if seconds < 60:
           return f"expires in {int(seconds)} seconds"
       if seconds < 3600:
           minutes = int(seconds // 60)
           return f"expires in {minutes} minute{'s' if minutes != 1 else ''}"
       if seconds < 86400:
           hours = int(seconds // 3600)
           return f"expires in {hours} hour{'s' if hours != 1 else ''}"
       days = int(seconds // 86400)
       return f"expires in {days} day{'s' if days != 1 else ''}"
   ```

**Files**: included in `_auth_status.py`

**Validation**:
- [ ] `format_duration(-1) == "[red]expired[/red]"`
- [ ] `format_duration(45) == "expires in 45 seconds"`
- [ ] `format_duration(120) == "expires in 2 minutes"`
- [ ] `format_duration(3600) == "expires in 1 hour"`
- [ ] `format_duration(86400 * 87) == "expires in 87 days"`

---

### T039: Add storage backend display formatter

**Purpose**: Map the StorageBackend literal to a human-readable label.

**Steps**:

1. Add to `src/specify_cli/cli/commands/_auth_status.py`:
   ```python
   _STORAGE_LABELS = {
       "keychain": "macOS Keychain",
       "credential_manager": "Windows Credential Manager",
       "secret_service": "Linux Secret Service",
       "file": "File fallback (encrypted at rest)",
   }


   def format_storage_backend(backend: str) -> str:
       """Convert a StorageBackend literal to a user-facing label."""
       return _STORAGE_LABELS.get(backend, f"Unknown ({backend})")
   ```

**Files**: included in `_auth_status.py`

**Validation**:
- [ ] All four backend values map to user-friendly labels
- [ ] Unknown value falls through to "Unknown (X)"

---

### T040: Write unit + CliRunner tests for status

**Purpose**: Coverage of the status command across all session states.

**Steps**:

1. Create `tests/cli/commands/test_auth_status.py`:
   ```python
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import patch, MagicMock
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app
   from specify_cli.cli.commands._auth_status import (
       format_duration,
       format_storage_backend,
   )
   from specify_cli.auth import reset_token_manager
   from specify_cli.auth.session import StoredSession, Team

   runner = CliRunner()


   def _make_session(
       access_remaining: int = 3600,
       refresh_remaining_days: int = 87,
   ) -> StoredSession:
       now = datetime.now(timezone.utc)
       return StoredSession(
           user_id="u_alice",
           email="alice@example.com",
           name="Alice Developer",
           teams=[
               Team(id="tm_acme", name="Acme Corp", role="admin"),
               Team(id="tm_widgets", name="Widgets Inc", role="member"),
           ],
           default_team_id="tm_acme",
           access_token="at_xyz",
           refresh_token="rt_xyz",
           session_id="sess_xyz",
           issued_at=now,
           access_token_expires_at=now + timedelta(seconds=access_remaining),
           refresh_token_expires_at=now + timedelta(days=refresh_remaining_days),
           scope="offline_access",
           storage_backend="keychain",
           last_used_at=now,
           auth_method="authorization_code",
       )


   @pytest.fixture(autouse=True)
   def _isolate(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       yield
       reset_token_manager()


   class TestFormatDuration:
       def test_expired(self):
           assert "expired" in format_duration(-100)
       def test_seconds(self):
           assert format_duration(45) == "expires in 45 seconds"
       def test_minute_singular(self):
           assert format_duration(60) == "expires in 1 minute"
       def test_minutes_plural(self):
           assert format_duration(120) == "expires in 2 minutes"
       def test_hour_singular(self):
           assert format_duration(3600) == "expires in 1 hour"
       def test_hours_plural(self):
           assert format_duration(7200) == "expires in 2 hours"
       def test_day_singular(self):
           assert format_duration(86400) == "expires in 1 day"
       def test_days_plural(self):
           assert format_duration(86400 * 87) == "expires in 87 days"


   class TestFormatStorageBackend:
       def test_keychain(self):
           assert format_storage_backend("keychain") == "macOS Keychain"
       def test_credential_manager(self):
           assert format_storage_backend("credential_manager") == "Windows Credential Manager"
       def test_secret_service(self):
           assert format_storage_backend("secret_service") == "Linux Secret Service"
       def test_file(self):
           assert "File fallback" in format_storage_backend("file")
       def test_unknown(self):
           assert "Unknown" in format_storage_backend("???")


   class TestStatusCommand:

       def test_not_authenticated(self):
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = None
               mock_storage.backend_name = "file"
               reset_token_manager()
               result = runner.invoke(app, ["status"])
           assert result.exit_code == 0
           assert "Not authenticated" in result.stdout

       def test_authenticated(self):
           session = _make_session()
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = session
               mock_storage.backend_name = "keychain"
               reset_token_manager()
               result = runner.invoke(app, ["status"])
           assert result.exit_code == 0
           assert "Authenticated" in result.stdout
           assert "alice@example.com" in result.stdout
           assert "Acme Corp" in result.stdout
           assert "Widgets Inc" in result.stdout
           assert "default" in result.stdout  # default team marker

       def test_authenticated_with_token_expiry_display(self):
           session = _make_session(access_remaining=600, refresh_remaining_days=87)
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = session
               mock_storage.backend_name = "file"
               reset_token_manager()
               result = runner.invoke(app, ["status"])
           assert result.exit_code == 0
           assert "minutes" in result.stdout  # 600 seconds = 10 minutes
           assert "87 days" in result.stdout

       def test_refresh_token_expired(self):
           session = _make_session(access_remaining=-100, refresh_remaining_days=-1)
           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
               mock_storage = mock_se.return_value
               mock_storage.read.return_value = session
               mock_storage.backend_name = "file"
               reset_token_manager()
               result = runner.invoke(app, ["status"])
           assert result.exit_code == 0
           assert "expired" in result.stdout.lower()
           assert "spec-kitty auth login" in result.stdout
   ```

**Files**: `tests/cli/commands/test_auth_status.py` (~250 lines)

**Validation**:
- [ ] All test cases pass
- [ ] CliRunner is used (passes WP11 T063 audit)
- [ ] All status display branches covered

---

## Definition of Done

- [ ] All 4 subtasks completed
- [ ] All unit tests pass
- [ ] Status output includes user, teams, access expiry, refresh expiry, storage backend, session ID, last_used_at, auth method
- [ ] Default team marked with "(default)"
- [ ] Expired tokens shown as "expired" in red
- [ ] Storage backend shown with friendly label
- [ ] No tokens leaked in output (only the last few characters of any token if any — preferably none)

## Reviewer Guidance

- Verify the status command does NOT print the actual access_token or refresh_token values
- Verify CliRunner is used in tests
- Verify the format_duration tests cover all branches (seconds, minutes, hours, days, expired)
- Verify the storage backend labels are user-friendly (not raw enum values)

## Risks & Edge Cases

- **Risk**: Refresh token expired but the session is still loaded. **Mitigation**: explicit branch checks `is_refresh_token_expired()` and prints expired message.
- **Risk**: User has no teams. **Mitigation**: print "(none)" instead of crashing.
- **Edge case**: `last_used_at` is far in the past. **Mitigation**: format as ISO date — user can interpret.

## Activity Log

- 2026-04-09T19:20:15Z – claude:opus-4-6:python-implementer:implementer – shell_pid=63419 – Started implementation via action command

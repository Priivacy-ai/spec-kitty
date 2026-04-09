---
work_package_id: WP11
title: Integration Tests, Concurrency Tests, Staging Validation
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
requirement_refs:
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T057
- T058
- T059
- T060
- T061
- T062
- T063
- T064
history: []
authoritative_surface: tests/auth/integration/
execution_mode: code_change
owned_files:
- tests/auth/integration/**
- tests/auth/concurrency/**
- tests/auth/stress/**
status: pending
tags: []
agent: "claude:opus-4-6:python-implementer:implementer"
shell_pid: "52903"
---

# WP11: Integration Tests, Concurrency Tests, Staging Validation

**Objective**: End-to-end integration tests via `CliRunner` against the real
`spec-kitty` Typer `app`. Concurrency tests for single-flight refresh under
load. Stress tests for file storage atomicity. Audit subtasks that grep for
forbidden patterns. This is the final gate before mission merge.

**Context**: The previous run wrote 45 integration tests but they all called
flow classes directly (e.g., `await AuthorizationCodeFlow().login()`) instead
of going through the CLI entry point. Every test passed even though the CLI
commands were stubs. This WP exists to prevent that exact failure mode by
forcing tests to use `CliRunner` or `subprocess` and adding a grep audit
that fails the WP if the rule is violated.

**CRITICAL**: Every test in `tests/auth/integration/` MUST use either
`CliRunner` (against `specify_cli.cli.commands.auth.app` or
`specify_cli.__main__.app`) or `subprocess.run(['spec-kitty', ...])`. Tests
that import flow classes WITHOUT also importing CliRunner are flagged by
T063 audit and the WP is rejected.

**Acceptance Criteria**:
- [ ] `tests/auth/integration/test_browser_login_e2e.py` exercises the full
      `spec-kitty auth login` path via CliRunner with mocked SaaS HTTP
- [ ] `tests/auth/integration/test_headless_login_e2e.py` exercises
      `spec-kitty auth login --headless` via CliRunner
- [ ] `tests/auth/integration/test_logout_e2e.py` exercises `spec-kitty auth logout`
- [ ] `tests/auth/integration/test_status_e2e.py` exercises `spec-kitty auth status`
- [ ] `tests/auth/integration/test_transport_rewired.py` verifies that
      `sync/client.py` HTTP requests go through TokenManager (not via
      legacy CredentialStore)
- [ ] `tests/auth/concurrency/test_single_flight_refresh.py` runs 10+
      concurrent `get_access_token()` calls and asserts exactly 1 refresh
- [ ] `tests/auth/stress/test_file_storage_concurrent.py` runs concurrent
      writes to the file fallback and asserts no corruption
- [ ] T063 GREP AUDIT passes (no integration tests use flow classes without CliRunner)
- [ ] T064 GREP AUDIT passes (no test references CredentialStore or AuthClient)
- [ ] All tests pass

---

## Subtask Guidance

### T057: Create `test_browser_login_e2e.py` (CliRunner + mock SaaS)

**Purpose**: End-to-end test of the browser login command via the real Typer app.

**Steps**:

1. Create `tests/auth/integration/__init__.py` (empty).
2. Create `tests/auth/integration/test_browser_login_e2e.py`:
   ```python
   """E2E browser login test using CliRunner against the real Typer app."""
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, MagicMock, patch
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app
   from specify_cli.auth import reset_token_manager
   from specify_cli.auth.session import StoredSession, Team

   runner = CliRunner()

   _SAAS = "https://saas.test"


   class _MockResponse:
       def __init__(self, status_code: int, json_body: dict):
           self.status_code = status_code
           self._json = json_body
           self.text = str(json_body)
       def json(self):
           return self._json


   def _token_response():
       return {
           "access_token": "at_xyz",
           "refresh_token": "rt_xyz",
           "expires_in": 3600,
           "scope": "offline_access",
           "session_id": "sess_xyz",
       }


   def _me_response():
       return {
           "user_id": "u_alice",
           "email": "alice@example.com",
           "name": "Alice Developer",
           "teams": [{"id": "tm_acme", "name": "Acme Corp", "role": "admin"}],
           "default_team_id": "tm_acme",
       }


   @pytest.fixture(autouse=True)
   def _isolate(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", _SAAS)
       reset_token_manager()
       yield
       reset_token_manager()


   class TestBrowserLoginE2E:

       def test_full_browser_login_via_clirunner(self):
           """Verify the full browser login path via the real CLI command."""
           # Mock CallbackServer to return a callback immediately
           async def fake_wait_for_callback(self):
               return {"code": "auth_code_123", "state": self._expected_state_for_test}
           # We need to inject the state — use a side effect on start()
           captured_state = []
           orig_validate = None

           # Mock browser launcher
           with patch("specify_cli.auth.loopback.browser_launcher.BrowserLauncher.launch", return_value=True):
               # Mock the callback server
               with patch("specify_cli.auth.loopback.callback_server.CallbackServer") as mock_cs_cls:
                   mock_cs = mock_cs_cls.return_value
                   mock_cs.start.return_value = "http://127.0.0.1:28888/callback"
                   mock_cs.stop = MagicMock()
                   # Make wait_for_callback return the expected state
                   async def wait():
                       # Capture the state from the StateManager via the flow
                       return {"code": "auth_code_123", "state": _captured_state["state"]}
                   mock_cs.wait_for_callback = wait

                   # Mock state manager to capture the generated state
                   _captured_state = {}
                   from specify_cli.auth.loopback.state_manager import StateManager as RealStateManager
                   orig_generate = RealStateManager.generate
                   def patched_generate(self):
                       state = orig_generate(self)
                       _captured_state["state"] = state.state
                       return state
                   with patch.object(RealStateManager, "generate", patched_generate):

                       # Mock httpx for the token exchange + user info
                       async def mock_post(url, data=None, headers=None, json=None):
                           if url.endswith("/oauth/token"):
                               return _MockResponse(200, _token_response())
                           raise AssertionError(f"Unexpected POST: {url}")

                       async def mock_get(url, headers=None):
                           if url.endswith("/api/v1/me"):
                               return _MockResponse(200, _me_response())
                           raise AssertionError(f"Unexpected GET: {url}")

                       with patch("httpx.AsyncClient") as mock_client:
                           instance = mock_client.return_value.__aenter__.return_value
                           instance.post = mock_post
                           instance.get = mock_get

                           # Mock storage to capture the stored session
                           captured = {}
                           with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
                               mock_storage = mock_se.return_value
                               mock_storage.read.return_value = None
                               def fake_write(s):
                                   captured["session"] = s
                               mock_storage.write = fake_write
                               mock_storage.delete = lambda: None
                               mock_storage.backend_name = "file"
                               reset_token_manager()

                               result = runner.invoke(app, ["login"])

           assert result.exit_code == 0, f"stdout: {result.stdout}"
           assert "Authenticated" in result.stdout
           assert "alice@example.com" in result.stdout
           assert captured["session"].user_id == "u_alice"
   ```

3. This test is complex because it has to mock the loopback callback server,
   the browser launcher, the SaaS HTTP layer, and the secure storage. The
   complexity is the price of "go through the real CLI command path".

4. Crucially, both `CliRunner` and `AuthorizationCodeFlow` (via the dispatch
   shell) are exercised. The test imports `CliRunner` so it passes the T063
   audit.

**Files**: `tests/auth/integration/__init__.py` (empty), `tests/auth/integration/test_browser_login_e2e.py` (~150 lines)

**Validation**:
- [ ] Test passes
- [ ] CliRunner is imported and used

---

### T058: Create `test_headless_login_e2e.py`

**Purpose**: Same as T057 but for the device flow path.

**Steps**:

1. Create `tests/auth/integration/test_headless_login_e2e.py`:
   ```python
   """E2E headless device flow login test via CliRunner."""
   import pytest
   from unittest.mock import patch, MagicMock
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app
   from specify_cli.auth import reset_token_manager

   runner = CliRunner()
   _SAAS = "https://saas.test"


   class _MockResponse:
       def __init__(self, status_code, json_body):
           self.status_code = status_code
           self._json = json_body
           self.text = str(json_body)
       def json(self):
           return self._json


   @pytest.fixture(autouse=True)
   def _isolate(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", _SAAS)
       reset_token_manager()
       yield
       reset_token_manager()


   class TestHeadlessLoginE2E:
       def test_full_device_flow_via_clirunner(self):
           device_response = {
               "device_code": "dc_xyz",
               "user_code": "ABCD-1234",
               "verification_uri": f"{_SAAS}/device",
               "expires_in": 900,
               "interval": 0,  # 0s for fast tests
           }
           token_response = {
               "access_token": "at_xyz",
               "refresh_token": "rt_xyz",
               "expires_in": 3600,
               "scope": "offline_access",
               "session_id": "sess_xyz",
           }
           me_response = {
               "user_id": "u_alice",
               "email": "alice@example.com",
               "name": "Alice",
               "teams": [{"id": "tm_acme", "name": "Acme", "role": "admin"}],
               "default_team_id": "tm_acme",
           }

           async def mock_post(url, data=None, headers=None, json=None):
               if url.endswith("/oauth/device"):
                   return _MockResponse(200, device_response)
               if url.endswith("/oauth/token"):
                   return _MockResponse(200, token_response)
               raise AssertionError(f"Unexpected POST: {url}")

           async def mock_get(url, headers=None):
               if url.endswith("/api/v1/me"):
                   return _MockResponse(200, me_response)
               raise AssertionError(f"Unexpected GET: {url}")

           captured = {}
           with patch("httpx.AsyncClient") as mock_client:
               instance = mock_client.return_value.__aenter__.return_value
               instance.post = mock_post
               instance.get = mock_get
               with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment") as mock_se:
                   mock_storage = mock_se.return_value
                   mock_storage.read.return_value = None
                   mock_storage.write = lambda s: captured.setdefault("session", s)
                   mock_storage.delete = lambda: None
                   mock_storage.backend_name = "file"
                   reset_token_manager()
                   result = runner.invoke(app, ["login", "--headless"])

           assert result.exit_code == 0, f"stdout: {result.stdout}"
           assert "alice@example.com" in result.stdout
           assert captured["session"].auth_method == "device_code"
   ```

**Files**: `tests/auth/integration/test_headless_login_e2e.py` (~120 lines)

**Validation**:
- [ ] Test passes
- [ ] CliRunner is imported and used
- [ ] StoredSession.auth_method == "device_code"

---

### T059: Create `test_logout_e2e.py` and `test_status_e2e.py`

**Purpose**: Same pattern for logout and status commands.

**Steps**:

1. Create `tests/auth/integration/test_logout_e2e.py`:
   - Use CliRunner to invoke `["logout"]`
   - Mock storage to return a fake session
   - Mock httpx for the /api/v1/logout call (200 OK)
   - Assert exit code 0 and "Logged out" in stdout
   - Assert storage.delete was called

2. Create `tests/auth/integration/test_status_e2e.py`:
   - Use CliRunner to invoke `["status"]`
   - Mock storage to return a fake session with known fields
   - Assert exit code 0 and stdout contains user, teams, expiry display

**Files**: `tests/auth/integration/test_logout_e2e.py` (~80 lines), `tests/auth/integration/test_status_e2e.py` (~80 lines)

**Validation**:
- [ ] Both tests pass
- [ ] Both tests use CliRunner

---

### T060: Create `test_transport_rewired.py`

**Purpose**: Verify that `sync/client.py` actually uses TokenManager (not the
old AuthClient). This is a structural test that catches dead-code regressions.

**Steps**:

1. Create `tests/auth/integration/test_transport_rewired.py`:
   ```python
   """Verify the legacy transport files are rewired to TokenManager."""
   import inspect
   import pytest
   from specify_cli.auth import get_token_manager


   def test_sync_client_imports_get_token_manager():
       """sync/client.py must import get_token_manager from specify_cli.auth."""
       import specify_cli.sync.client as client_mod
       source = inspect.getsource(client_mod)
       assert "get_token_manager" in source or "from specify_cli.auth" in source

   def test_sync_client_does_not_import_legacy_auth():
       """sync/client.py must not import AuthClient or CredentialStore."""
       import specify_cli.sync.client as client_mod
       source = inspect.getsource(client_mod)
       assert "AuthClient" not in source
       assert "CredentialStore" not in source

   def test_tracker_saas_client_rewired():
       """tracker/saas_client.py must be rewired similarly."""
       import specify_cli.tracker.saas_client as t
       source = inspect.getsource(t)
       assert "AuthClient" not in source
       assert "CredentialStore" not in source

   def test_legacy_sync_auth_module_does_not_exist():
       """src/specify_cli/sync/auth.py must be deleted (WP10)."""
       with pytest.raises(ImportError):
           import specify_cli.sync.auth  # noqa: F401

   def test_get_token_manager_callers():
       """At least 5 production files outside auth/ must call get_token_manager."""
       import subprocess
       result = subprocess.run(
           ["grep", "-rn", "get_token_manager", "src/specify_cli/", "--include=*.py"],
           capture_output=True, text=True,
       )
       lines = [
           line for line in result.stdout.splitlines()
           if not line.startswith("src/specify_cli/auth/")
       ]
       assert len(lines) >= 5, (
           f"Expected ≥5 production callers of get_token_manager outside auth/, "
           f"found {len(lines)}:\n" + "\n".join(lines)
       )
   ```

2. This test catches regressions where someone reverts the rewire and
   reintroduces dead code.

**Files**: `tests/auth/integration/test_transport_rewired.py` (~80 lines)

**Validation**:
- [ ] All 5 tests pass
- [ ] The "≥5 callers" assertion mirrors WP08's T046 grep audit

---

### T061: Create `test_single_flight_refresh.py`

**Purpose**: Concurrency test that 10+ concurrent `get_access_token()` calls
result in exactly 1 refresh network call.

**Steps**:

1. Create `tests/auth/concurrency/__init__.py` (empty).
2. Create `tests/auth/concurrency/test_single_flight_refresh.py`:
   ```python
   """Concurrency test: 10+ concurrent get_access_token() = 1 refresh."""
   import asyncio
   import pytest
   from datetime import datetime, timedelta, timezone
   from unittest.mock import AsyncMock, MagicMock, patch
   from specify_cli.auth import get_token_manager, reset_token_manager
   from specify_cli.auth.token_manager import TokenManager
   from specify_cli.auth.session import StoredSession, Team


   def _expired_session() -> StoredSession:
       now = datetime.now(timezone.utc)
       return StoredSession(
           user_id="u",
           email="u@example.com",
           name="U",
           teams=[Team(id="tm", name="T", role="admin")],
           default_team_id="tm",
           access_token="at_old",
           refresh_token="rt_xyz",
           session_id="sess",
           issued_at=now - timedelta(hours=2),
           access_token_expires_at=now - timedelta(seconds=10),  # already expired
           refresh_token_expires_at=now + timedelta(days=89),
           scope="offline_access",
           storage_backend="file",
           last_used_at=now,
           auth_method="authorization_code",
       )


   @pytest.fixture(autouse=True)
   def _isolate(monkeypatch):
       monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
       reset_token_manager()
       yield
       reset_token_manager()


   @pytest.mark.asyncio
   async def test_single_flight_refresh_under_concurrency(monkeypatch):
       """10 concurrent get_access_token() calls = exactly 1 refresh call."""
       refresh_count = 0
       refreshed_session = None

       async def fake_refresh(session):
           nonlocal refresh_count, refreshed_session
           refresh_count += 1
           # Simulate slow network so concurrency matters
           await asyncio.sleep(0.05)
           now = datetime.now(timezone.utc)
           refreshed_session = StoredSession(
               user_id=session.user_id,
               email=session.email,
               name=session.name,
               teams=session.teams,
               default_team_id=session.default_team_id,
               access_token="at_new",
               refresh_token=session.refresh_token,
               session_id=session.session_id,
               issued_at=now,
               access_token_expires_at=now + timedelta(hours=1),
               refresh_token_expires_at=session.refresh_token_expires_at,
               scope=session.scope,
               storage_backend=session.storage_backend,
               last_used_at=now,
               auth_method=session.auth_method,
           )
           return refreshed_session

       fake_storage = MagicMock()
       fake_storage.read.return_value = _expired_session()
       fake_storage.write = lambda s: None
       fake_storage.backend_name = "file"

       with patch("specify_cli.auth.secure_storage.SecureStorage.from_environment", return_value=fake_storage):
           with patch("specify_cli.auth.flows.refresh.TokenRefreshFlow") as MockRefreshFlow:
               MockRefreshFlow.return_value.refresh = fake_refresh
               reset_token_manager()
               tm = get_token_manager()
               # Fire 10 concurrent get_access_token calls
               results = await asyncio.gather(*[tm.get_access_token() for _ in range(10)])

       assert refresh_count == 1, f"Expected exactly 1 refresh, got {refresh_count}"
       assert all(t == "at_new" for t in results)
   ```

**Files**: `tests/auth/concurrency/__init__.py` (empty), `tests/auth/concurrency/test_single_flight_refresh.py` (~120 lines)

**Validation**:
- [ ] Test passes
- [ ] Refresh count == 1
- [ ] All 10 results are the new token

---

### T062: Create `test_file_storage_concurrent.py`

**Purpose**: Stress test for the file fallback under concurrent writes.

**Steps**:

1. Create `tests/auth/stress/__init__.py` (empty).
2. Create `tests/auth/stress/test_file_storage_concurrent.py`:
   ```python
   """Stress test: concurrent writes to file fallback do not corrupt the file."""
   import threading
   import pytest
   from datetime import datetime, timedelta, timezone
   from pathlib import Path
   from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
   from specify_cli.auth.session import StoredSession, Team


   def _make_session(token_suffix: str) -> StoredSession:
       now = datetime.now(timezone.utc)
       return StoredSession(
           user_id="u",
           email="u@example.com",
           name="U",
           teams=[Team(id="tm", name="T", role="admin")],
           default_team_id="tm",
           access_token=f"at_{token_suffix}",
           refresh_token=f"rt_{token_suffix}",
           session_id=f"sess_{token_suffix}",
           issued_at=now,
           access_token_expires_at=now + timedelta(hours=1),
           refresh_token_expires_at=now + timedelta(days=90),
           scope="offline_access",
           storage_backend="file",
           last_used_at=now,
           auth_method="authorization_code",
       )


   @pytest.fixture
   def isolated_home(tmp_path, monkeypatch):
       monkeypatch.setenv("HOME", str(tmp_path))
       yield tmp_path


   def test_concurrent_writes_no_corruption(isolated_home):
       storage = FileFallbackStorage()
       errors = []

       def writer(suffix):
           try:
               session = _make_session(suffix)
               storage.write(session)
           except Exception as exc:
               errors.append(exc)

       threads = [threading.Thread(target=writer, args=(str(i),)) for i in range(20)]
       for t in threads:
           t.start()
       for t in threads:
           t.join()

       assert not errors, f"Concurrent writes raised exceptions: {errors}"

       # Final read must succeed and return one of the written sessions
       loaded = storage.read()
       assert loaded is not None
       assert loaded.access_token.startswith("at_")
       assert loaded.user_id == "u"


   def test_atomic_write_no_partial_file(isolated_home):
       storage = FileFallbackStorage()
       session = _make_session("test")
       storage.write(session)
       loaded = storage.read()
       assert loaded.access_token == "at_test"
   ```

**Files**: `tests/auth/stress/__init__.py` (empty), `tests/auth/stress/test_file_storage_concurrent.py` (~100 lines)

**Validation**:
- [ ] Concurrent writes complete without errors
- [ ] Final read returns a valid session

---

### T063: AUDIT — integration tests must use CliRunner/subprocess

**Purpose**: The hard gate that prevents the previous failure mode.

**Steps**:

1. Run the audit:
   ```bash
   FILES=$(grep -l 'AuthorizationCodeFlow\|DeviceCodeFlow' tests/auth/integration/*.py 2>/dev/null || true)
   for f in $FILES; do
       if ! grep -qE 'CliRunner|subprocess' "$f"; then
           echo "FAIL: $f imports a flow class but does not use CliRunner or subprocess"
           exit 1
       fi
   done
   echo "PASS: all integration tests use CliRunner or subprocess"
   ```

2. Expected: PASS. Any integration test that imports a flow class without
   also importing CliRunner is a regression and the WP is incomplete.

3. Add the audit to a Python test that runs in CI:
   ```python
   # tests/auth/integration/test_audit_clirunner.py
   from pathlib import Path
   import pytest

   def test_no_flow_class_only_integration_tests():
       """Integration tests must use CliRunner or subprocess."""
       integration_dir = Path("tests/auth/integration")
       offending = []
       for test_file in integration_dir.glob("*.py"):
           if test_file.name == "test_audit_clirunner.py":
               continue
           content = test_file.read_text()
           uses_flow = "AuthorizationCodeFlow" in content or "DeviceCodeFlow" in content
           uses_runner = "CliRunner" in content or "subprocess" in content
           if uses_flow and not uses_runner:
               offending.append(str(test_file))
       assert not offending, f"Integration tests must use CliRunner: {offending}"
   ```

**Files**: `tests/auth/integration/test_audit_clirunner.py` (~30 lines)

**Validation**:
- [ ] Audit returns PASS
- [ ] Audit test passes in CI

---

### T064: AUDIT — zero `CredentialStore`/`AuthClient` references in tests/

**Purpose**: Mirror of T045 (WP08) for the test tree. After this WP, no test
should reference the legacy classes.

**Steps**:

1. Run the audit:
   ```bash
   grep -rn 'CredentialStore\|AuthClient' tests/ --include='*.py'
   ```
   Expected: empty, OR only matches in `tests/sync/test_auth.py` regression
   stub from WP10.

2. If the WP10 regression stub uses the names in a string (e.g., `with pytest.raises(ImportError):`),
   that's allowed. The audit excludes:
   ```bash
   grep -rn 'CredentialStore\|AuthClient' tests/ --include='*.py' \
       | grep -v 'tests/sync/test_auth.py' \
       | grep -v 'pytest.raises'
   ```

3. Add as a Python test in `tests/auth/integration/test_audit_clirunner.py`
   (same file as T063):
   ```python
   def test_no_legacy_class_references_in_tests():
       """No test outside the WP10 regression stub should reference the legacy classes."""
       import subprocess
       result = subprocess.run(
           ["grep", "-rn", "CredentialStore", "tests/", "--include=*.py"],
           capture_output=True, text=True,
       )
       offending = [
           line for line in result.stdout.splitlines()
           if "test_auth.py" not in line  # Exclude WP10 regression stub
       ]
       assert not offending, f"Tests reference legacy CredentialStore: {offending}"
   ```

**Files**: included in `tests/auth/integration/test_audit_clirunner.py`

**Validation**:
- [ ] Audit returns empty
- [ ] Audit test passes

---

## Definition of Done

- [ ] All 8 subtasks completed
- [ ] All integration, concurrency, and stress tests pass
- [ ] T063 audit returns PASS
- [ ] T064 audit returns empty
- [ ] Single-flight refresh test verifies 10+ concurrent = 1 refresh
- [ ] File storage concurrent test verifies no corruption
- [ ] All integration tests use CliRunner or subprocess
- [ ] No test imports a flow class without CliRunner

## Reviewer Guidance

**This is the gate that catches dead-code regressions.** Reviewer must:

1. Spot-check each integration test file: does it import `CliRunner`?
2. Run the T063 audit shell command and verify PASS
3. Run the T064 audit shell command and verify empty
4. Run `pytest tests/auth/integration/ tests/auth/concurrency/ tests/auth/stress/ -v` and verify all pass
5. Reject if any integration test calls a flow class directly without CliRunner

## Risks & Edge Cases

- **Risk**: CliRunner mocking is complex and tests are flaky. **Mitigation**: aggressive use of `unittest.mock.patch` to mock the loopback server and SaaS HTTP — accept the test complexity as the price of catching dead code.
- **Risk**: T063 audit produces a false positive on a test that legitimately needs to import a flow class for type hints. **Mitigation**: the audit checks for the substring inside the file content; type hints in import-only-for-typing patterns can be put in a `TYPE_CHECKING` block.
- **Edge case**: Concurrency test may be flaky on slow CI runners. **Mitigation**: the test asserts on COUNT (== 1), not on timing; even slow refresh is fine as long as the count is right.

## Activity Log

- 2026-04-09T21:23:30Z – claude:opus-4-6:python-implementer:implementer – shell_pid=52903 – Started implementation via action command
- 2026-04-09T21:48:14Z – claude:opus-4-6:python-implementer:implementer – shell_pid=52903 – Integration tests (27), concurrency (4), stress (4), audit (5) all green. 254/254 auth tests pass, no regressions in sync suite.

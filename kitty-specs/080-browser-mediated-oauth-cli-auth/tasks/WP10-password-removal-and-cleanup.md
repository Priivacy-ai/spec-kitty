---
work_package_id: WP10
title: Password Removal & Legacy Cleanup
dependencies:
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T052
- T053
- T054
- T055
- T056
history: []
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/auth.py
- tests/sync/test_auth.py
- tests/sync/test_auth_concurrent_refresh.py
status: pending
tags: []
agent: "claude:opus-4-6:python-reviewer:reviewer"
shell_pid: "52484"
---

# WP10: Password Removal & Legacy Cleanup

**Objective**: Complete the hard cutover (C-001). DELETE
`src/specify_cli/sync/auth.py` (the legacy `AuthClient` and `CredentialStore`).
Update or remove the legacy auth tests. Verify no password prompts remain
anywhere in the CLI. Ensure the new `auth login` Typer command help text
contains zero mentions of "password" or "username".

**Context**: This WP runs after WP04-WP08 have rewired every consumer of
`sync/auth.py`. By this point, no production code imports from the legacy
module. WP10 is the deletion + verification gate.

**CRITICAL**: WP10 must NOT run before WP08 completes. If WP10 deletes
`sync/auth.py` while sync/client.py still imports from it, the entire
sync subsystem breaks. The dependency chain enforces this ordering.

**Acceptance Criteria**:
- [ ] `src/specify_cli/sync/auth.py` is deleted
- [ ] `grep -rn 'from specify_cli.sync.auth\|from .auth' src/specify_cli/sync/ src/specify_cli/tracker/ --include='*.py'` returns nothing
- [ ] `grep -rn 'AuthClient\|CredentialStore' src/specify_cli/ --include='*.py'` returns nothing (the auth.py file no longer exists, so the auth/ exclusion is moot)
- [ ] `tests/sync/test_auth.py` is updated or removed
- [ ] `spec-kitty auth login --help` does NOT contain the words "password" or "username"
- [ ] CLI smoke test: `python -c "from specify_cli.cli.commands.auth import app; print('ok')"` succeeds
- [ ] Regression test asserts the Typer app has `login`, `logout`, `status` commands
- [ ] All test suites pass

---

## Subtask Guidance

### T052: DELETE `src/specify_cli/sync/auth.py`; verify no imports remain

**Purpose**: Remove the legacy auth module.

**Steps**:

1. Before deleting, verify nothing imports from it:
   ```bash
   grep -rn 'from specify_cli.sync.auth\|from .auth import\|sync\.auth' \
       src/specify_cli/ --include='*.py'
   ```
   Expected: empty output (WP08 should have removed all such imports).
   If any remain, find the file and remove the import.

2. Delete the file:
   ```bash
   rm src/specify_cli/sync/auth.py
   ```

3. Verify no broken imports:
   ```bash
   python -c "from specify_cli.cli.commands.auth import app"
   python -c "from specify_cli.sync.client import *"
   python -c "from specify_cli.tracker.saas_client import *"
   ```
   All three must succeed without ImportError.

4. If anything fails, the corresponding rewire in WP08 was incomplete. WP10
   should reject the implementation back to WP08, NOT add the import back.

**Files**: DELETE `src/specify_cli/sync/auth.py`

**Validation**:
- [ ] File no longer exists
- [ ] All smoke imports succeed
- [ ] No grep hits for legacy class names

---

### T053: Update or remove `tests/sync/test_auth.py`

**Purpose**: The legacy test file exercises `AuthClient` and `CredentialStore`,
both of which no longer exist. The tests must be updated, repurposed, or
removed.

**Steps**:

1. Read the existing `tests/sync/test_auth.py`. Identify what each test
   verifies:
   - Tests of `CredentialStore.save/load/clear` → DELETE (replaced by tests/auth/test_secure_storage_*.py from WP01)
   - Tests of `AuthClient.is_authenticated` → DELETE (replaced by tests/auth/test_token_manager.py)
   - Tests of `AuthClient.refresh_tokens()` → DELETE (replaced by tests/auth/test_refresh_flow.py from WP04 + tests/auth/concurrency/test_single_flight_refresh.py from WP11)
   - Tests of legacy password-based `obtain_tokens()` → DELETE (functionality removed)

2. Decide: DELETE the entire file, OR replace its contents with a single
   import-error stub that catches accidental restoration:
   ```python
   """Legacy auth tests removed in mission 080 (browser-mediated OAuth).

   The previous tests covered AuthClient and CredentialStore which no longer
   exist. Equivalent coverage now lives in:
   - tests/auth/test_secure_storage_keychain.py
   - tests/auth/test_secure_storage_file.py
   - tests/auth/test_token_manager.py
   - tests/auth/test_refresh_flow.py
   - tests/auth/concurrency/test_single_flight_refresh.py
   """
   def test_legacy_auth_module_is_gone():
       import pytest
       with pytest.raises(ImportError):
           from specify_cli.sync import auth  # noqa: F401
   ```

3. Apply the same treatment to `tests/sync/test_auth_concurrent_refresh.py`
   if it exists. The single-flight refresh tests are now in WP11's
   `tests/auth/concurrency/test_single_flight_refresh.py`.

4. Run the test suite to confirm nothing depends on the deleted tests:
   ```bash
   pytest tests/sync/ -v
   ```

**Files**: `tests/sync/test_auth.py` (REPLACE), `tests/sync/test_auth_concurrent_refresh.py` (REPLACE or DELETE)

**Validation**:
- [ ] No tests in `tests/sync/test_auth.py` reference `AuthClient` or `CredentialStore`
- [ ] The test file either contains the legacy regression stub or is deleted
- [ ] `pytest tests/sync/` passes

---

### T054: Search and remove any password-prompt code

**Purpose**: Ensure no `getpass`, `input("password")`, or similar prompts
remain in the CLI auth path.

**Steps**:

1. Run the search:
   ```bash
   grep -rn 'getpass\|input.*password\|prompt.*password\|hide_input.*True' \
       src/specify_cli/ --include='*.py' | grep -v 'src/specify_cli/sync/clock.py'
   ```
   - `sync/clock.py` uses `getpass.getuser()` which is unrelated (gets the
     username for system identification, not for auth) — exclude it.
   - Any other hit indicates leftover password-collection code → remove.

2. Run a broader search for "username":
   ```bash
   grep -rn 'username.*input\|prompt.*username' src/specify_cli/cli/ --include='*.py'
   ```
   Expected: empty.

3. Verify the help text:
   ```bash
   spec-kitty auth login --help 2>&1 | grep -i 'password\|username'
   ```
   Expected: empty. (Run via `python -m specify_cli auth login --help` if
   `spec-kitty` is not on PATH in the test environment.)

**Files**: no file changes expected (T020 in WP04 already removed the code);
this is a verification subtask

**Validation**:
- [ ] No password prompts in source code
- [ ] No "username" prompts in source code
- [ ] `auth login --help` mentions neither

---

### T055: Verify `spec-kitty auth login --help` does not mention password

**Purpose**: User-facing verification.

**Steps**:

1. Use CliRunner to capture the help output:
   ```python
   from typer.testing import CliRunner
   from specify_cli.cli.commands.auth import app

   runner = CliRunner()
   result = runner.invoke(app, ["login", "--help"])
   assert result.exit_code == 0
   assert "password" not in result.stdout.lower()
   assert "username" not in result.stdout.lower()
   ```

2. Add this assertion as a test in `tests/sync/test_auth.py` (the regression
   stub from T053) or in a new regression test file owned by WP10.

**Files**: included in test from T053 or T056

**Validation**:
- [ ] CliRunner test passes
- [ ] Help text contains neither word

---

### T056: Regression test asserting Typer app has login/logout/status commands

**Purpose**: A simple smoke test that catches the most common breakage:
the dispatch shell from WP04 not registering all three commands.

**Steps**:

1. Add to `tests/sync/test_auth.py` (or a new file):
   ```python
   def test_typer_app_has_required_commands():
       """Regression: the auth Typer app must have login, logout, and status commands."""
       from specify_cli.cli.commands.auth import app
       command_names = {cmd.name for cmd in app.registered_commands}
       assert "login" in command_names
       assert "logout" in command_names
       assert "status" in command_names

   def test_no_oauth_prefixed_commands():
       """Regression: there must be no parallel oauth-login/oauth-logout/oauth-status commands.

       Hard cutover (C-001) means the new flow IS the auth login command,
       not a parallel set.
       """
       from specify_cli.cli.commands.auth import app
       command_names = {cmd.name for cmd in app.registered_commands}
       assert "oauth-login" not in command_names
       assert "oauth_login" not in command_names
       assert "oauth-logout" not in command_names
       assert "oauth-status" not in command_names

   def test_login_command_no_password_in_help():
       from typer.testing import CliRunner
       from specify_cli.cli.commands.auth import app
       runner = CliRunner()
       result = runner.invoke(app, ["login", "--help"])
       assert result.exit_code == 0
       help_lower = result.stdout.lower()
       assert "password" not in help_lower
       assert "username" not in help_lower
   ```

2. These tests are owned by WP10 and live in `tests/sync/test_auth.py` (the
   replacement file from T053).

**Files**: `tests/sync/test_auth.py` (final form, ~80 lines)

**Validation**:
- [ ] All three tests pass
- [ ] `pytest tests/sync/test_auth.py -v` succeeds

---

## Definition of Done

- [ ] All 5 subtasks completed
- [ ] `src/specify_cli/sync/auth.py` no longer exists
- [ ] No grep hits for `AuthClient`, `CredentialStore`, or `from specify_cli.sync.auth` anywhere in `src/specify_cli/`
- [ ] No password prompts in source code
- [ ] `auth login --help` mentions neither "password" nor "username"
- [ ] Typer app has exactly `login`, `logout`, `status` commands (no parallel `oauth-*` commands)
- [ ] All test suites pass

## Reviewer Guidance

- Verify the file `src/specify_cli/sync/auth.py` is actually deleted (not just emptied)
- Verify the regression test for `oauth-login` etc. asserts those names DO NOT exist
- Verify the help-text test uses CliRunner against the real `app`
- If the legacy test file was repurposed, verify it has zero references to AuthClient/CredentialStore

## Risks & Edge Cases

- **Risk**: A scratch script or example in `docs/` references the legacy classes. **Mitigation**: search docs/ separately and update if needed (not blocking — docs update is a follow-up).
- **Risk**: Some external tooling depends on the existence of `~/.spec-kitty/credentials` file format. **Mitigation**: out of scope; the new file fallback uses a different path (`~/.config/spec-kitty/credentials.json`).
- **Edge case**: The user has stale `~/.spec-kitty/credentials` from the old format. **Mitigation**: Document in the user-facing migration notes (handled by mission release notes, not this WP).

## Activity Log

- 2026-04-09T20:59:09Z – claude:opus-4-6:python-implementer:implementer – shell_pid=23068 – Started implementation via action command
- 2026-04-09T21:20:34Z – claude:opus-4-6:python-implementer:implementer – shell_pid=23068 – Legacy auth removed, all tests green
- 2026-04-09T21:21:10Z – claude:opus-4-6:python-reviewer:reviewer – shell_pid=52484 – Started review via action command

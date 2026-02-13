---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
title: "Fix sync status --check to use real token"
phase: "Wave 1 - Independent Fixes"
lane: "planned"  # DO NOT EDIT - use: spec-kitty agent tasks move-task WP03 --to <lane>
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-12T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Fix sync status --check to use real token

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03
```

No dependencies — branches directly from the 2.x branch.

---

## Objectives & Success Criteria

- `sync status --check` uses the user's real auth token from `~/.spec-kitty/credentials`
- No false 403 errors from hardcoded test tokens
- Clear "Not authenticated — run `spec-kitty auth login`" message when no credentials are stored
- Token refresh attempted automatically if access token is expired
- Existing sync tests pass with zero regressions

## Context & Constraints

- **Delivery branch**: 2.x
- **Root cause**: `sync status --check` (approximately `sync.py:531` on 2.x) uses a hardcoded test token for connectivity probing, producing misleading 403 errors that don't reflect actual auth state
- **Auth infrastructure**: `src/specify_cli/sync/auth.py` already provides credential loading and token refresh — reuse these functions
- **Credential format**: TOML at `~/.spec-kitty/credentials` with `tokens.access`, `tokens.refresh`, `tokens.access_expires_at`, `tokens.refresh_expires_at`
- **Reference**: `spec.md` (FR-018), `plan.md` (WP03), `contracts/batch-ingest.md` (authentication section)

## Subtasks & Detailed Guidance

### Subtask T011 – Load real access token from credentials store

- **Purpose**: Replace the hardcoded test token with the user's actual JWT access token.
- **Steps**:
  1. Find the hardcoded test token on 2.x. Search for it:
     ```bash
     grep -rn "test.*token\|hardcoded\|Bearer.*test" src/specify_cli/sync/ src/specify_cli/cli/commands/
     ```
  2. Read `src/specify_cli/sync/auth.py` to find the credential loading functions (likely `load_credentials()` or `get_access_token()`)
  3. Replace the hardcoded token with a call to the auth module:
     ```python
     from specify_cli.sync.auth import get_access_token  # or equivalent
     token = get_access_token()
     ```
  4. If `get_access_token()` doesn't exist, create a wrapper that reads from `~/.spec-kitty/credentials`
- **Files**: Sync status check file (find on 2.x — may be in `sync/runtime.py`, `sync/client.py`, or `cli/commands/` sync subcommand)
- **Parallel?**: No — foundation for T012/T013

### Subtask T012 – Handle token refresh and missing credentials

- **Purpose**: Gracefully handle expired tokens and missing credentials instead of producing misleading errors.
- **Steps**:
  1. Check if credentials file exists at `~/.spec-kitty/credentials`
  2. If not present: print clear message and return early:
     ```python
     console.print("[yellow]Not authenticated.[/yellow] Run `spec-kitty auth login` to connect.")
     return
     ```
  3. If present but access token is expired:
     - Attempt refresh using the stored refresh token (use existing `auth.py` refresh logic)
     - If refresh succeeds: proceed with new access token
     - If refresh fails (refresh token also expired): print "Session expired — run `spec-kitty auth login` to re-authenticate"
  4. If present and token is valid: proceed to T013 endpoint probe
- **Files**: Same file as T011
- **Parallel?**: No — depends on T011
- **Notes**: Token expiry is stored in `tokens.access_expires_at` in ISO 8601 format. Compare with current time.

### Subtask T013 – Probe actual endpoint with real token

- **Purpose**: Test connectivity against the real batch endpoint instead of a synthetic test path.
- **Steps**:
  1. Use the real access token to make a lightweight probe request
  2. Options for probe:
     - **Option A**: HEAD request to the batch endpoint URL
     - **Option B**: POST an empty batch `{"events": []}` and check for 200 with empty results
     - **Option C**: Use a dedicated health/ping endpoint if available
  3. Report the result clearly:
     - 200: "Connected: Server reachable, authentication valid"
     - 401: "Authentication failed — run `spec-kitty auth login`"
     - 403: "Permission denied — check team membership for this project"
     - Timeout/connection error: "Server unreachable — events will be queued for later sync"
  4. Use the server URL from credentials (`server.url` field)
- **Files**: Same file as T011
- **Parallel?**: No — depends on T011/T012
- **Notes**: Keep the probe lightweight to avoid unintended side effects. An empty batch POST is safe per the contract.

### Subtask T014 – Write tests for auth-aware status check

- **Purpose**: Validate all three paths: valid token, expired token, no credentials.
- **Steps**:
  1. Create or extend test file for sync status:
     ```python
     # Test with valid credentials
     def test_status_check_with_valid_token(mock_credentials, mock_server):
         # Mock credentials with valid token
         # Mock server response 200
         # Assert "Connected" in output

     # Test with expired token, successful refresh
     def test_status_check_with_expired_token_refresh_success(mock_credentials):
         # Mock expired access token, valid refresh
         # Assert refresh was attempted
         # Assert "Connected" in output

     # Test with expired token, failed refresh
     def test_status_check_with_expired_token_refresh_failed(mock_credentials):
         # Mock expired access + expired refresh
         # Assert "Session expired" in output

     # Test with no credentials
     def test_status_check_no_credentials(tmp_path):
         # No credentials file
         # Assert "Not authenticated" in output

     # Test with server unreachable
     def test_status_check_server_unreachable(mock_credentials):
         # Mock connection timeout
         # Assert "Server unreachable" in output
     ```
  2. Use `unittest.mock.patch` to mock credential loading and HTTP calls
  3. Run existing sync tests for regression:
     ```bash
     python -m pytest tests/sync/ -x -v
     ```
- **Files**: `tests/sync/test_sync_status.py` (new or extend)
- **Parallel?**: No — depends on T011-T013

## Test Strategy

- **New tests**: ~5 tests covering all auth/connectivity paths
- **Run command**: `python -m pytest tests/sync/ -x -v`
- **Fixtures**: Mock `~/.spec-kitty/credentials` with tmp_path, mock HTTP responses

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Hardcoded token location moved on 2.x | Search broadly: `grep -rn "Bearer\|test_token\|hardcoded" src/specify_cli/` |
| auth.py API differs from expectations | Read auth.py first; adapt to actual function signatures |
| Probe endpoint returns unexpected status | Test against mock; document expected codes in contract |

## Review Guidance

- Verify no hardcoded test tokens remain in the codebase
- Check that all three credential states are handled (valid, expired, missing)
- Verify token refresh is attempted before reporting failure
- Run `python -m pytest tests/sync/ -x -v` — all tests green

## Activity Log

- 2026-02-12T12:00:00Z – system – lane=planned – Prompt created.

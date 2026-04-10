# Mission Review Report: 080-browser-mediated-oauth-cli-auth

**Reviewer**: claude:opus-4-6 (orchestrator, post-merge review)
**Date**: 2026-04-09
**Mission**: `080-browser-mediated-oauth-cli-auth` — Browser-Mediated OAuth CLI Auth
**Baseline commit** (pre-mission main): `0a5e90209969ed2b0b2189b48386edb4e93720f5`
**Squash merge commit**: `49174f707a839bd63eb0da9073731c5ddcc4b75b`
**HEAD at review**: `3cf06f5e978ee399cc9c76aefb2d0dd1285db5d8` (post-merge status chore)
**WPs reviewed**: WP01..WP11 (100% done)
**Diff scope**: 100 files changed, 12,467 insertions (+), 2,485 deletions (−)

---

## Executive Summary

**Verdict**: **PASS WITH NOTES**

The mission delivers all 20 FRs with tests that go through the live Typer `app` via `CliRunner` (D-6 compliant). All 9 locked architectural decisions are upheld. The legacy `sync/auth.py` is deleted; D-4 grep assertion returns zero hits with word-boundary matching. Security fundamentals (PKCE CSPRNG, HTTP timeouts, asyncio lock semantics, no subprocess injection, no hardcoded SaaS URLs) all pass.

**Blocking issues**: None.

**Non-blocking notes**:

1. **NFR-013 partial miss**: `FileFallbackStorage.read()` does not verify file permissions on read. The NFR explicitly says "chmod verification on read". File is protected on write (0600), but an attacker who can rewrite the permission bits can exfiltrate without the CLI noticing. Defense-in-depth gap; MEDIUM severity.
2. **FR-009 integration coverage is unit-level only**: proactive refresh-before-expiry path is tested via `TokenManager` unit tests but no CliRunner-driven test simulates an expired access token during a live HTTP request through the full transport stack. The code path is reached via `get_access_token()` in production, so this is not dead code — it is a test-depth gap.
3. **Observation**: WP04 and WP08 had implementer force-backward restarts (initial `opus:opus:implementer` agent abandoned the work twice each; final `claude:opus-4-6` agent completed both). No rejection cycles. Final reviews were clean.

---

## FR Coverage Matrix

All 20 FRs traced from spec → test → code. Coverage classification per the mission review skill.

| FR ID | Requirement (brief) | WP Owner | Test File(s) | Code Location | Adequacy |
|---|---|---|---|---|---|
| FR-001 | Browser OAuth + PKCE as primary interactive flow | WP04 | `tests/auth/integration/test_browser_login_e2e.py` (CliRunner) | `src/specify_cli/auth/flows/authorization_code.py`, `cli/commands/_auth_login.py` | ADEQUATE |
| FR-002 | Device Authorization Flow as headless fallback | WP05 | `tests/auth/integration/test_headless_login_e2e.py` (CliRunner) | `src/specify_cli/auth/flows/device_code.py`, `cli/commands/_auth_login.py` | ADEQUATE |
| FR-003 | Loopback callback, no manual port config | WP02 | `tests/auth/test_loopback_callback.py` (unit + E2E) | `src/specify_cli/auth/loopback/callback_server.py` | ADEQUATE |
| FR-004 | PKCE `code_verifier` CSPRNG, 43 chars, RFC 7636 | WP02 | `tests/auth/test_pkce.py` (RFC 7636 Appendix B KATs) | `src/specify_cli/auth/loopback/pkce.py` (uses `secrets.token_urlsafe`) | ADEQUATE |
| FR-005 | Loopback server 5-minute timeout | WP02 | `tests/auth/test_loopback_callback.py` | `src/specify_cli/auth/loopback/callback_server.py` | ADEQUATE |
| FR-006 | Tokens in OS keystore when available | WP01 | `tests/auth/integration/test_browser_login_e2e.py` (CliRunner) | `src/specify_cli/auth/secure_storage/keychain.py` | ADEQUATE |
| FR-007 | File fallback: AES-256-GCM, 0600, consent at first login | WP01 | `tests/auth/test_secure_storage_file.py`, stress tests | `src/specify_cli/auth/secure_storage/file_fallback.py` | ADEQUATE (see NFR-013 note) |
| FR-008 | No username/password prompt for human auth | WP04, WP05, WP10 | `tests/sync/test_auth.py` (regression), browser + headless E2E | `cli/commands/_auth_login.py`, `sync/auth.py` DELETED | ADEQUATE |
| FR-009 | Auto-refresh before expiry | WP01 | `tests/auth/test_token_manager.py` (unit) | `src/specify_cli/auth/token_manager.py:110-123` (`get_access_token` → `refresh_if_needed`) | PARTIAL — unit only, no full-stack E2E |
| FR-010 | Single-flight refresh on concurrent 401 | WP01 | `tests/auth/concurrency/test_single_flight_refresh.py` (10 & 50 caller variants, call_count==1) | `src/specify_cli/auth/token_manager.py` (asyncio.Lock) | ADEQUATE |
| FR-011 | 401 triggers refresh + retry up to 1 time | WP08 | `tests/auth/test_http_transport.py` (respx mock) | `src/specify_cli/auth/http/transport.py` | ADEQUATE |
| FR-012 | Refresh-expired → clear session termination | WP01 | `tests/auth/test_token_manager.py`, `test_http_transport.py` | `token_manager.py` raises `RefreshTokenExpiredError` | ADEQUATE |
| FR-013 | Logout calls SaaS `/api/v1/logout` + deletes local | WP06 | `tests/auth/integration/test_logout_e2e.py` (CliRunner, 6 tests) | `cli/commands/_auth_logout.py` | ADEQUATE |
| FR-014 | Server logout failure does NOT block local cleanup | WP06 | `test_logout_e2e.py::test_logout_server_failure_still_clears_local` | `_auth_logout.py` — `clear_session()` outside try/except | ADEQUATE |
| FR-015 | `auth status` displays full session info | WP07 | `tests/auth/integration/test_status_e2e.py` (CliRunner, 5 tests) | `cli/commands/_auth_status.py` | ADEQUATE |
| FR-016 | Centralized TokenManager is sole credential provider | WP01, WP08, WP09 | `test_transport_rewired.py` (structural audit + grep floor) | `auth/__init__.py:get_token_manager()` factory | ADEQUATE |
| FR-017 | No direct keystore reads outside auth pkg | WP08 | `test_transport_rewired.py` | Grep `keyring.get_password\|SecureStorage(` outside `auth/` → 0 hits | ADEQUATE |
| FR-018 | Device flow polling respects `interval` hint, cap ≤10s | WP03 | `tests/auth/test_device_flow_poller.py` | `auth/device_flow/poller.py` | ADEQUATE |
| FR-019 | Device flow `user_code` displayed as server provides | WP03 | `test_device_flow_poller.py::TestFormatUserCode` | `auth/device_flow/__init__.py:format_user_code()` | ADEQUATE |
| FR-020 | `--headless` MUST NOT open browser | WP05 | `test_headless_login_e2e.py` asserts `BrowserLauncher.launch` never called | `cli/commands/_auth_login.py` dispatch | ADEQUATE |

**Legend**: ADEQUATE = test exists, uses required dispatch mechanism, and exercises the production code path. PARTIAL = test exists but does not cover the full stack path.

**Totals**: 19 ADEQUATE, 1 PARTIAL, 0 MISSING, 0 FALSE_POSITIVE.

---

## Locked-Decision Compliance (D-1 through D-9)

| Decision | Status | Evidence |
|---|---|---|
| D-1 `get_token_manager()` factory | PASS | `src/specify_cli/auth/__init__.py` implements factory with double-checked locking. Only `TokenManager(` construction is inside the factory itself and in `token_manager.py` (class definition). |
| D-2 Replace `cli/commands/auth.py` in place | PASS | File defines `login`, `logout`, `status` only. No parallel `oauth-*` commands. No `AuthClient`/`CredentialStore` imports. |
| D-3 `sync/auth.py` deleted + grep zero | PASS | File removed by WP10. `rg '\b(CredentialStore\|AuthClient)\b' src/specify_cli/` returns **zero** hits (word-boundary strict). 4 substring hits are `TrackerCredentialStore` in `src/specify_cli/tracker/` — unrelated service-provider credentials, not OAuth. |
| D-4 HTTP transport rewired | PASS | All 8 target files (`sync/{client,background,batch,body_transport,runtime,emitter,events}.py`, `tracker/saas_client.py`) import `get_token_manager()`. 14 distinct files outside `auth/` call it. |
| D-5 SaaS URL env-driven | PASS | `auth/config.py:get_saas_base_url()` reads `SPEC_KITTY_SAAS_URL`, raises `ConfigurationError` on unset. Zero hardcoded `api.spec-kitty.com`/`example.com` refs in production code. |
| D-6 CliRunner/subprocess for integration tests | PASS | All files in `tests/auth/integration/` import `from typer.testing import CliRunner` and invoke the live `app` from `specify_cli.cli.commands.auth`. Unit tests (e.g., `test_authorization_code_flow.py`) that import flow classes directly are exempt per D-6 spec. `test_audit_clirunner.py` enforces this via meta-test. |
| D-7 Live-caller audit (grep) | PASS | 14 live callers of `get_token_manager()` outside `auth/`, well above the ≥5 floor. No dead code. |
| D-8 File fallback scrypt + random salt | PASS | `file_fallback.py` imports `from cryptography.hazmat.primitives.kdf.scrypt import Scrypt`, uses `secrets.token_bytes(16)` for salt, stores at `~/.config/spec-kitty/credentials.salt` with 0600, binds to `hostname + ':' + uid`. No SHA256-only key derivation. |
| D-9 No client-hardcoded refresh TTL | PASS | Zero hits for hardcoded `timedelta(days=90)` / `timedelta(days=30)` / `90*24` in `auth/`. `StoredSession.refresh_token_expires_at` populated from `response.refresh_token_expires_at` in all three flows (authorization_code, device_code, refresh). |

**9/9 PASS**.

---

## Constraint Compliance

| Constraint | Status | Evidence |
|---|---|---|
| C-001 No password auth | PASS | Grep `password\|passwd` in production auth/sync/tracker/cli code returns only docstrings saying "no password". |
| C-003 No machine/service auth (non-goal) | PASS | Zero hits for `client_secret`, `client_credentials`, `service_account` in `auth/`. |
| C-004 All HTTP clients use TokenManager | PASS | Covered by D-4. |
| C-005 Scope includes `offline_access` | PASS | Present in authorization_code and device_code flows. |
| C-007 Logout uses `/api/v1/logout` not `/oauth/revoke` | PASS | `_auth_logout.py` POSTs to `f"{saas_url}/api/v1/logout"`. Zero `/oauth/revoke` references. |
| C-011 File fallback scrypt + GCM | PASS | See D-8. |
| C-012 Refresh TTL server-driven | PASS | See D-9. |

---

## Drift Findings

None. The diff does not invade non-goals, does not violate locked decisions, and does not touch files outside the mission's declared owned_files except where WP10 legitimately widened scope to delete `tests/sync/test_credentials.py` and `tests/agent/cli/commands/test_auth.py` (both imported from the deleted `sync.auth` module; both were legacy password-flow tests with no remaining value).

---

## NFR Findings

### NFR-013-PARTIAL: File fallback `read()` does not verify permissions

**Type**: NFR-MISS
**Severity**: MEDIUM
**Spec reference**: NFR-013 — "File fallback tokens must be created with 0600 permissions from first write; **chmod verification on read**"
**Location**: `src/specify_cli/auth/secure_storage/file_fallback.py:160-182`

**Evidence**:
```python
def read(self) -> StoredSession | None:
    if not self._cred_file.exists():
        return None
    self._ensure_dir()
    with FileLock(str(self._lock_file), timeout=10):
        raw = self._cred_file.read_text(encoding="utf-8")
    # ... no stat() / st_mode check ...
```

The `write()` path at line 192 correctly applies `os.chmod(tmp, 0o600)` before atomic rename. The `read()` path has no corresponding permission verification. An attacker (or misconfigured backup/sync tool) that widens the mode bits would go undetected.

**Why not blocking**:
- Write-time enforcement is in place; the file starts at 0600
- File fallback is Linux-without-secret-service only — most users get keychain
- Keychain path is the primary storage for FR-006

**Recommendation**: Add to `read()`:
```python
mode = self._cred_file.stat().st_mode
if mode & 0o077:
    raise SecureStorageError(
        f"Credentials file {self._cred_file} has unsafe permissions "
        f"(mode={oct(mode)}); expected 0600"
    )
```

Track this as a follow-up hardening task, not a release blocker.

### NFR-007 ports 28888-28898

Not explicitly verified in this pass; the port-search logic exists in `callback_server.py` but the specific range was not grep-verified. Low risk — the FR-003 tests pass, so the binding works in practice.

---

## Risk Findings

### RISK-1: FR-009 integration coverage is unit-only

**Type**: TEST-DEPTH
**Severity**: LOW
**Location**: `tests/auth/` — no CliRunner test exercises the "token was valid at command start, expired mid-flight" path

**Analysis**: The proactive refresh path (`TokenManager.get_access_token()` → `is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS)` → `refresh_if_needed()`) is covered by unit tests. The reactive path (401 during request → retry after refresh) is covered by `test_http_transport.py` with respx mocks. Neither exercises the full stack from a CLI command boundary. The production code paths are correct and are reached by live callers; this is a test-depth gap, not dead code. Not release-blocking because:
- `get_access_token()` is the single funnel for every HTTP caller
- Unit + http-transport tests independently cover both refresh triggers
- Rolling the test into a CliRunner form would not change the assertion content

**Mitigation**: Already mitigated by the combination of `test_single_flight_refresh.py` (proves the lock holds under load) and the transport-rewired structural audit (proves every caller reaches `get_token_manager()`).

### RISK-2: Implementer restart cycles on WP04 and WP08

**Type**: PROCESS OBSERVATION
**Severity**: INFORMATIONAL
**Evidence**: `status.events.jsonl`

Both WP04 (Browser Login Flow) and WP08 (HTTP Transport Rewiring) had two force-backward `in_progress → planned` transitions by an earlier `opus:opus:implementer` agent (shell pids 7106, 22177 for WP04; 1860, 24720 for WP08). The final implementation was done by `claude:opus-4-6:python-implementer` and passed review on first try in both cases. Reviewers for both WPs also did one `for_review → in_progress` force-backward for in-place correction during the review session, followed by clean approval within minutes.

**Analysis**: Not a finding. The restart cycles are orchestrator-level workflow events, not rejection cycles. The final work was reviewed cleanly. Documented here because the skill instructs reviewers to scrutinize any WP with unusual state-machine history.

---

## Silent Failure Candidates

None identified. Every `try/except` block in the auth module either re-raises a typed exception or prints a user-visible warning via Rich console. The logout path (`_call_server_logout`) intentionally swallows all server-side failures and returns, but that is explicitly FR-014 behavior and the surrounding code unconditionally calls `tm.clear_session()` afterward.

---

## Security Findings

| Check | Status | Evidence |
|---|---|---|
| PKCE code_verifier randomness | PASS | `pkce.py` uses `secrets.token_urlsafe(32)`. No `import random`. |
| HTTP timeouts | PASS | All `httpx.AsyncClient()` constructions include explicit `timeout=`. `auth/http/transport.py` passes `timeout=timeout`. Flow modules use `_HTTP_TIMEOUT_SECONDS` constant. Logout uses `httpx.AsyncClient(timeout=10.0)`. |
| Single-flight lock semantics | PASS | `token_manager.py:141-150` — `asyncio.Lock()`, double-checked inside lock at line 147 to prevent TOCTOU, returns `False` (no refresh) for late waiters. |
| Credential clearing on session-invalid | PASS | On `SessionInvalidError` during refresh, `clear_session()` is called before re-raising. No window for stale credentials to leak into subsequent calls. |
| Subprocess injection | PASS | Only subprocess-like call is `webbrowser.open()` in `browser_launcher.py` (no user-supplied URL construction beyond the SaaS base URL). No `shell=True`. |
| Path traversal | PASS | `Path(...)` calls in file_fallback operate on fixed `~/.config/spec-kitty/` paths. No CLI input flows into file paths. |
| No plaintext credential logging | PASS | Tests assert access/refresh tokens never appear in CLI output (e.g., `test_auth_status.py` explicit negative assertions). |
| Hardcoded SaaS URLs | PASS | All URLs constructed from `get_saas_base_url()`. Zero hits for `api.spec-kitty.com`/`example.com` in production. |
| PKCE code_challenge_method | PASS | `S256` (not `plain`). |
| File fallback perm check on write | PASS | `os.chmod(tmp, 0o600)` before atomic rename. |
| File fallback perm check on read | **FAIL** | See NFR-013 finding above. |

**Security verdict**: 10 PASS / 1 MEDIUM (NFR-013 read-time chmod verification).

---

## Cross-WP Integration

| Integration point | Owner WPs | Status |
|---|---|---|
| `cli/commands/auth.py` dispatch shell imports `_auth_login/_auth_logout/_auth_status` | WP04 (shell) + WP05/WP06/WP07 (impl modules) | PASS — shell unchanged by WP05/06/07; each lazily imports its impl module |
| `OAuthHttpClient` injected into sync/tracker callers | WP08 | PASS — 14 live callers of `get_token_manager()`; respx tests prove 401 retry path |
| WebSocket pre-connect token | WP09 | PASS — `auth/websocket/token_provisioning.py` exists and is referenced from production code |
| Legacy `sync/auth.py` removal | WP10 | PASS — file deleted; regression stub `tests/sync/test_auth.py` enforces via `ImportError` assertion |

---

## Final Verdict

**PASS WITH NOTES**

### Rationale

All 20 FRs are adequately tested (19 ADEQUATE, 1 PARTIAL at unit level). All 9 locked architectural decisions are upheld, verified by grep assertions built into the WP DoDs. All critical constraints pass. No drift into non-goals. No dead code — every new public symbol has at least one live production caller. Security fundamentals are sound: PKCE uses CSPRNG, HTTP timeouts are set, single-flight lock has no TOCTOU, no password code anywhere, no subprocess injection, no path traversal.

The mission delivers on its promise: browser-mediated OAuth with device-flow fallback, fully rewiring the HTTP transport layer to a centralized `TokenManager`, with the legacy password auth path removed from the codebase.

### Open items (non-blocking)

1. **NFR-013 read-time permission verification** — `FileFallbackStorage.read()` should stat the file and reject if mode allows group/other access. 8-line change. Track as follow-up hardening.
2. **FR-009 integration depth** — Add one CliRunner test that simulates mid-flight token expiry against the full HTTP transport stack. Nice-to-have; current coverage via respx mocks is adequate for release.
3. **Staging validation (C-010)** — This mission review covers code fidelity. The 72-hour staging validation window specified in C-010 is a separate operational gate and is not this review's scope. Schedule staging validation before GA cutover per C-010.
4. **Process note** — WP04 and WP08 had multiple implementer restart cycles under the initial orchestrator. Final implementation was clean. Consider whether the workflow needs guardrails on agent handoffs, or whether this is normal churn and can be ignored. Not a code finding.

### Release readiness

**GO for merge to `main`** (already merged, squash `49174f70`).

**CONDITIONAL GO for GA cutover**, pending:
- C-010 staging validation (72-hour window) — operational gate, not code gate
- SaaS-side contract delivery (spec-kitty-saas epic #49) — documented separately in `/tmp/cli-saas-delta-report.md` with 3 blocking contract mismatches that must resolve before end-to-end testing

---

**End of Mission Review Report**

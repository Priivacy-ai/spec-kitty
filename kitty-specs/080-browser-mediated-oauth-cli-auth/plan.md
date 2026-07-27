# Implementation Plan: Browser-Mediated OAuth/OIDC CLI Authentication

**Mission**: `080-browser-mediated-oauth-cli-auth`
**Branch**: `main` | **Date**: 2026-04-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/080-browser-mediated-oauth-cli-auth/spec.md`
**Epic**: #559 | **Related issues**: #560, #561, #562, #564, #565
**SaaS counterpart**: epic #49 (spec-kitty-saas)

> This plan was rewritten on 2026-04-09 after a post-merge mission review found
> that an earlier implementation produced dead code. The architectural decisions
> below exist specifically to prevent that failure mode.

---

## Summary

Replace password-based human CLI authentication with browser-mediated OAuth 2.0
Authorization Code + PKCE against `spec-kitty-saas`. Device Authorization Flow
serves as the sole headless fallback. A new shared `TokenManager` becomes the
single source of bearer tokens for every HTTP, batch, background, tracker, and
WebSocket caller in the CLI. Tokens move out of the existing TOML credentials
file into OS-backed secure storage (Keychain / Credential Manager / Secret
Service), with an encrypted file fallback only when no OS keystore is available.
The cutover is hard: the existing `AuthClient` and `CredentialStore` (TOML)
classes are removed, every legacy caller is rewired, and the existing
`auth login` / `auth logout` / `auth status` Typer commands are replaced in
place — no parallel command set.

---

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase requirement)
**Primary dependencies**:
- `httpx` — already present (sync/client.py uses it)
- `filelock` — already present (used by existing CredentialStore for cross-process locking)
- `keyring>=24.0` — **NEW** dependency. OS keystore abstraction (Keychain/Credential Manager/Secret Service). NOT currently in `pyproject.toml`. WP01 adds it.
- `cryptography>=42.0` — **NEW** dependency. AES-256-GCM AEAD + scrypt KDF for the encrypted file fallback (per C-011). NOT currently in `pyproject.toml`. WP01 adds it.
- `asyncio` (stdlib) — single-flight refresh, async coordination
- `secrets` (stdlib) — PKCE verifier and CSRF state generation
- `webbrowser` (stdlib) — open browser cross-platform

**Storage**:
- OS keystore via `keyring` library (preferred)
- Encrypted file fallback at `~/.config/spec-kitty/credentials.json` (0600 perms,
  AES-256-GCM, scrypt-derived key, salt at `~/.config/spec-kitty/credentials.salt`)
- Lock coordination via `filelock` (already in repo)

**Testing**: pytest, pytest-asyncio (already in repo). Integration tests use
`typer.testing.CliRunner` against the live `app` from `specify_cli.__main__`,
or `subprocess.run(['spec-kitty', ...])` for end-to-end.

**Target Platform**: macOS (Keychain), Linux (Secret Service), Windows
(Credential Manager). File fallback for any platform with no OS keystore.

**Project Type**: Single-repo Python CLI tool

**Performance Goals** (NFRs from spec):
- Browser login total time: < 30s (excluding user think time)
- Headless login start: < 5s (network only)
- Token refresh: < 500ms p99 (NFR-004)
- Refresh blocking time on user CLI: < 3s (NFR-005)
- Single-flight coordination overhead: < 100ms (NFR-006)
- Loopback port discovery: 28888-28898 search range (NFR-007)

**Constraints** (from spec §5):
- C-001 Hard cutover: password auth removed entirely, no fallback
- C-002 Device flow is the sole headless human path
- C-003 Machine/service auth is out of scope
- C-004 TokenManager is the only token source for all HTTP callers
- C-005 OAuth scope must include `offline_access`
- C-006 Device polling uses `/oauth/device` POST + `/oauth/token` device_code grant
- C-007 Logout calls `/api/v1/logout` (not `/oauth/revoke`)
- C-008 Access TTL ~1h; refresh TTL is SaaS-managed and surfaced via `refresh_token_expires_in` / `refresh_token_expires_at` on every `POST /oauth/token` response (landed 2026-04-09)
- C-009 Server-managed sessions, no JWT self-contained state
- C-010 72+ hour staging validation before GA cutover

**Scale/Scope**: Single user CLI. Tokens are per-user, per-machine. Multi-team
support via team list in stored session, default team for status display.

---

## Charter Check

*Charter file `.kittify/charter/charter.md` is not present in this repository.
Charter Check is **skipped** for this mission.*

---

## Architectural Decisions (Locked)

These decisions resolve ambiguities that the previous (failed) run left
implicit. Every WP must conform to these or be rejected at review.

### D-1: TokenManager lifecycle is a shared instance via factory

**Decision**: Implement `get_token_manager()` as a module-level factory function
in `src/specify_cli/auth/__init__.py`. It returns a process-wide
`TokenManager` instance that lazy-initializes from secure storage on first call.
Subsequent calls return the same instance.

```python
# src/specify_cli/auth/__init__.py
_tm: Optional[TokenManager] = None
_tm_lock = threading.Lock()

def get_token_manager() -> TokenManager:
    global _tm
    if _tm is None:
        with _tm_lock:
            if _tm is None:
                storage = SecureStorage.from_environment()
                _tm = TokenManager(storage)
                _tm.load_from_storage_sync()
    return _tm
```

**Rationale**: The previous run had WP04 define `TokenManager(storage)` as a
per-instance constructor and WP09 call `TokenManager.get_instance()` (singleton).
The two APIs did not compose, so WP09 implementer wrote stubs. A factory
function avoids both pitfalls and gives every caller a single shared instance
without the test-hostile global state of a true singleton class attribute.

**Consequence**: Tests inject a fresh TokenManager via a context manager that
swaps `_tm` for a test instance (not via monkeypatching the class).

### D-2: Replace existing `cli/commands/auth.py` commands in place

**Decision**: WP09 modifies the existing `src/specify_cli/cli/commands/auth.py`
file. The existing `login`, `logout`, and `status` Typer commands are
**rewritten** in place to use `get_token_manager()` and the new auth flows.
No parallel `oauth-login` / `oauth-logout` / `oauth-status` commands are added.

**Rationale**: The previous run added a parallel command set, leaving both old
and new auth systems live in the same file. Hard cutover (C-001) means there is
exactly one command path. The user runs `spec-kitty auth login` and gets the
browser flow — no choice between systems.

**Consequence**: WP09's `owned_files` includes
`src/specify_cli/cli/commands/auth.py`. After WP09, that file no longer
imports `AuthClient` or `CredentialStore`.

### D-3: Legacy `sync/auth.py` AuthClient and CredentialStore are deleted

**Decision**: `src/specify_cli/sync/auth.py` is removed entirely. Any remaining
references in the codebase are rewired to import from `specify_cli.auth`.

**Rationale**: The legacy `AuthClient` reads/writes a TOML credentials file
under `~/.spec-kitty/credentials`. The new system reads/writes via TokenManager.
Keeping both creates a forking auth state where one half of the codebase reads
from TOML and the other reads from keychain. The post-merge review found
exactly this — the new TokenManager existed but was dead code because every
production caller still used `AuthClient.credential_store.get_access_token()`.

**Consequence**: An audit step (D-7 below) verifies zero hits for
`CredentialStore` and `AuthClient` in `src/specify_cli/` outside of the auth
package itself.

### D-4: HTTP transport rewiring is a first-class WP, not a side effect

**Decision**: One WP — referred to here as **WP-Rewire** — owns the rewiring of
all legacy HTTP/transport callers. Its `owned_files` explicitly includes:
- `src/specify_cli/sync/client.py`
- `src/specify_cli/sync/background.py`
- `src/specify_cli/sync/batch.py`
- `src/specify_cli/sync/body_transport.py`
- `src/specify_cli/sync/runtime.py`
- `src/specify_cli/sync/emitter.py`
- `src/specify_cli/sync/events.py`
- `src/specify_cli/tracker/saas_client.py`

WP-Rewire's acceptance criterion includes a grep verification:
```bash
# After WP-Rewire is done, this must return zero hits:
grep -rn 'CredentialStore\|AuthClient\|sync\.auth' src/specify_cli/ \
    --include='*.py' | grep -v '^src/specify_cli/auth/'
```

**Rationale**: The previous run had WP07 own only `src/specify_cli/auth/http/**`,
which built `OAuthHttpClient` in isolation but did not require any caller to
use it. The result was a complete OAuth http module with zero callers from
production code. Making the rewiring explicit and grep-verified prevents this.

### D-5: SaaS base URL is environment-driven, never hardcoded

**Decision**: All references to the SaaS base URL come from a
`get_saas_base_url()` helper that reads from environment variable
`SPEC_KITTY_SAAS_URL`. There is no fallback to a hardcoded domain.

```python
# src/specify_cli/auth/config.py
import os

def get_saas_base_url() -> str:
    url = os.environ.get('SPEC_KITTY_SAAS_URL')
    if not url:
        raise ConfigurationError(
            'SPEC_KITTY_SAAS_URL environment variable is not set. '
            'Set it to your spec-kitty-saas instance URL '
            '(e.g. https://api.spec-kitty.example.com).'
        )
    return url.rstrip('/')
```

**Rationale**: The post-merge review found hardcoded `https://example.com`
URLs in stub code and `https://api.spec-kitty.com` references in flow code.
The user clarified (recorded earlier in this session) that dev/prod are on
fly.io-generated hostnames and there is no stable domain. Reading from env
prevents both hardcoded test URLs and accidental production references.

**Consequence**: Tests use `monkeypatch.setenv('SPEC_KITTY_SAAS_URL', ...)`.
CI sets it. Local dev sets it via `direnv` or shell rc.

### D-6: Integration tests subprocess the live CLI or use CliRunner against the live app

**Decision**: WP-IntegrationTest's tests must invoke the actual CLI entry point.
Either:

```python
# Option A: subprocess
result = subprocess.run(
    ['spec-kitty', 'auth', 'login'],
    env={**os.environ, 'SPEC_KITTY_SAAS_URL': mock_saas.url},
    capture_output=True, text=True,
)
```

or:

```python
# Option B: CliRunner against the real Typer app
from typer.testing import CliRunner
from specify_cli.__main__ import app
runner = CliRunner()
result = runner.invoke(app, ['auth', 'login'], env={'SPEC_KITTY_SAAS_URL': mock_saas.url})
```

Tests must NOT call `AuthorizationCodeFlow().login()` or
`TokenManager().get_access_token()` directly as their primary integration
target. Direct calls are acceptable as unit-level tests but at least one
WP-IntegrationTest test per acceptance scenario must go through the live entry
point.

**Rationale**: The previous run wrote 45 integration tests that all called
flow classes directly. Every single test passed even though the CLI commands
were stubs. The post-merge review caught this only by reading the source.

**Consequence**: WP-IntegrationTest's acceptance criterion explicitly says "at
least one test per scenario uses CliRunner or subprocess against the real
`app`". Reviewer rejects WP-IntegrationTest if grep finds tests that import
flow classes without also importing `CliRunner` or `subprocess`.

### D-7: WP completion includes a grep audit for live integration

**Decision**: Each WP that creates a new module or function includes a final
audit subtask: `grep` for live callers from production code. If a new public
function or class has zero hits in `src/specify_cli/` outside its own
package and outside `tests/`, the WP is incomplete.

Specifically, after WP-TokenManager is done:
```bash
# Must return at least 5 hits (sync/client, sync/background, sync/batch,
# tracker/saas_client, cli/commands/auth) — possibly more:
grep -rn 'get_token_manager\b' src/specify_cli/ --include='*.py' \
    | grep -v '^src/specify_cli/auth/'
```

**Rationale**: The "passing tests, dead code" failure is the most expensive
defect because it survives review. A built-in grep audit per WP makes the
defect impossible to ship undetected.

### D-9: Refresh token TTL is server-driven, never client-hardcoded

**Decision**: The CLI MUST NOT hardcode any refresh-token TTL (90 days, 30
days, or otherwise). The CLI reads `refresh_token_expires_at` directly from
the SaaS token response on every token exchange and refresh, and stores the
server-supplied datetime verbatim in `StoredSession.refresh_token_expires_at`.
When the server omits the absolute form, the CLI falls back to
`now + timedelta(seconds=refresh_token_expires_in)`. The CLI never performs
local clock math beyond that fallback and never applies a default TTL if both
fields are absent.

**Rationale**: A pre-implementation review found that the SaaS side was
mixing 30-day, 90-day, and "renewable indefinitely" semantics across different
code paths. Hardcoding 90 days in the CLI would codify drift, not resolve it.
The SaaS team landed `contracts/saas-amendment-refresh-ttl.md` on 2026-04-09,
adding `refresh_token_expires_in` and `refresh_token_expires_at` to the
`POST /oauth/token` response for all grant types and
`refresh_token_expires_at` to `GET /api/v1/me`. The CLI mission now reads
these fields directly — no client-side TTL policy exists anywhere in the
code.

**Consequence**: TTL-sensitive UX is now fully unblocked:
- `auth status` "expires in N days" for the refresh token displays the
  real server-supplied value
- proactive expiry warnings are issued based on the server timestamp
- session-end countdowns are displayed with real duration

No CLI code hardcodes a refresh TTL anywhere. Reviewers must grep for
numeric constants near refresh logic and reject any hit that looks like a
TTL default.

**Note**: Spec.md constraint C-012 documents this binding contractually.

### D-8: File fallback uses scrypt key derivation with random salt

**Decision**: The encrypted file fallback derives its AES-256-GCM key via
`cryptography.hazmat.primitives.kdf.scrypt.Scrypt` from a passphrase composed
of `hostname + ':' + str(os.getuid())`, with a random 16-byte salt stored at
`~/.config/spec-kitty/credentials.salt` (0600 perms, generated on first write).

```python
# src/specify_cli/auth/secure_storage/file_fallback.py
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

def _derive_key(salt: bytes) -> bytes:
    passphrase = f"{socket.gethostname()}:{os.getuid()}".encode('utf-8')
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(passphrase)
```

**Rationale**: The previous run derived the key from `SHA256(hostname)` alone.
Hostnames are guessable, deterministic, and identical across all containers
with the same hostname (common in Docker/Kubernetes). scrypt with a random
salt forces an attacker who copies the credentials.json off a host to also
copy the salt and crack scrypt. UID adds a second factor against shared-host
attacks.

**Consequence**: Tests for the file fallback verify (a) the salt file is
created on first write with 0600 perms, (b) reading without the salt file
fails, (c) corrupted ciphertext fails authenticated decryption, (d) the key
is stable across reads on the same host but different across UIDs.

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/080-browser-mediated-oauth-cli-auth/
├── meta.json                    # Mission identity
├── spec.md                      # Specification (preserved from prior round)
├── plan.md                      # This file
├── data-model.md                # Phase 1 design (preserved)
├── quickstart.md                # Phase 1 validation walkthrough (preserved)
├── checklists/
│   └── requirements.md          # FR coverage checklist
├── contracts/                   # SaaS contract docs (preserved)
│   ├── api-logout-endpoint.md
│   ├── api-ws-token-endpoint.md
│   ├── error-responses.md
│   ├── oauth-authorize-endpoint.md
│   ├── oauth-device-endpoint.md
│   └── oauth-token-endpoint.md
├── research/                    # (empty — no open clarifications)
├── tasks.md                     # Generated by /spec-kitty.tasks (next step)
└── tasks/                       # WP prompt files (generated by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── auth/                              # NEW package (replaces sync/auth.py concerns)
│   ├── __init__.py                    # Exports: get_token_manager(), TokenManager
│   ├── config.py                      # get_saas_base_url() helper
│   ├── token_manager.py               # Shared TokenManager class
│   ├── session.py                     # StoredSession + Team dataclasses
│   ├── errors.py                      # All AuthenticationError subclasses
│   ├── secure_storage/
│   │   ├── __init__.py                # SecureStorage.from_environment() factory
│   │   ├── abstract.py                # SecureStorage ABC
│   │   ├── keychain.py                # macOS Keychain backend (keyring lib)
│   │   ├── credential_manager.py      # Windows backend (keyring lib)
│   │   ├── secret_service.py          # Linux backend (keyring lib)
│   │   └── file_fallback.py           # AES-256-GCM + scrypt KDF
│   ├── flows/
│   │   ├── __init__.py
│   │   ├── authorization_code.py      # Browser OAuth + PKCE flow orchestration
│   │   ├── device_code.py             # Device authorization flow orchestration
│   │   └── refresh.py                 # Token refresh flow
│   ├── loopback/
│   │   ├── __init__.py
│   │   ├── pkce.py                    # generate_code_verifier/challenge
│   │   ├── state.py                   # PKCEState dataclass
│   │   ├── state_manager.py           # State lifecycle + 5-min expiry
│   │   ├── callback_server.py         # Localhost HTTP server
│   │   ├── callback_handler.py        # CSRF state validation, code extraction
│   │   └── browser_launcher.py        # Cross-platform webbrowser wrapper
│   ├── device_flow/
│   │   ├── __init__.py
│   │   ├── state.py                   # DeviceFlowState dataclass
│   │   └── poller.py                  # Polling loop with interval cap
│   ├── http/
│   │   ├── __init__.py
│   │   └── transport.py               # OAuthHttpClient (httpx wrapper)
│   └── websocket/
│       ├── __init__.py
│       └── token_provisioning.py      # Pre-connect WS token fetcher
├── cli/commands/
│   └── auth.py                        # REWRITTEN: login/logout/status commands
├── sync/
│   ├── auth.py                        # DELETED (was AuthClient + CredentialStore)
│   ├── client.py                      # REWIRED to get_token_manager()
│   ├── background.py                  # REWIRED
│   ├── batch.py                       # REWIRED
│   ├── body_transport.py              # REWIRED
│   ├── runtime.py                     # REWIRED
│   ├── emitter.py                     # REWIRED
│   └── events.py                      # REWIRED
└── tracker/
    └── saas_client.py                 # REWIRED to get_token_manager()

tests/
├── auth/
│   ├── test_pkce.py                   # PKCE generation
│   ├── test_loopback_callback.py      # Callback server unit tests
│   ├── test_state_manager.py          # PKCE state lifecycle
│   ├── test_browser_launcher.py       # Cross-platform browser launching
│   ├── test_device_flow_poller.py     # Polling loop, interval cap
│   ├── test_secure_storage_keychain.py # Keychain backend
│   ├── test_secure_storage_file.py    # File fallback (encryption, salt, perms)
│   ├── test_token_manager.py          # Single-flight refresh, get_token_manager
│   ├── test_authorization_code_flow.py # Browser flow orchestration
│   ├── test_device_code_flow.py       # Device flow orchestration
│   ├── test_refresh_flow.py           # Token refresh flow
│   ├── test_http_transport.py         # OAuthHttpClient bearer + 401 retry
│   ├── test_websocket_provisioning.py # WS token pre-connect
│   ├── test_config.py                 # SPEC_KITTY_SAAS_URL helper
│   ├── integration/
│   │   ├── test_browser_login_e2e.py  # CliRunner + mock SaaS
│   │   ├── test_headless_login_e2e.py # CliRunner + mock SaaS
│   │   ├── test_logout_e2e.py         # CliRunner + mock SaaS
│   │   ├── test_status_e2e.py         # CliRunner
│   │   └── test_transport_rewired.py  # sync/client makes calls via TokenManager
│   ├── concurrency/
│   │   └── test_single_flight_refresh.py # 10+ concurrent 401s = 1 refresh
│   └── stress/
│       └── test_file_storage_concurrent.py
├── cli/commands/
│   └── test_auth.py                   # CLI command unit tests via CliRunner
├── sync/                              # Existing sync tests, updated for TokenManager
└── tracker/                           # Existing tracker tests, updated for TokenManager
```

### Files removed by this mission

```
src/specify_cli/sync/auth.py           # AuthClient + CredentialStore deleted
~/.spec-kitty/credentials              # User-side TOML file no longer read/written
tests/sync/test_auth*.py               # Legacy auth tests removed (preserved as
                                       # baseline only if explicitly noted in WP)
```

---

## Phase 0: Outline & Research

All planning unknowns are resolved by spec.md and the locked decisions D-1
through D-8 above. No `research.md` is generated for this round because:

- **OAuth flow choices** are locked by spec.md §1 and ADR
  `architecture/2.x/adr/2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md`
- **SaaS endpoints** are documented in `contracts/oauth-token-endpoint.md`,
  `contracts/oauth-device-endpoint.md`, `contracts/api-logout-endpoint.md`,
  `contracts/api-ws-token-endpoint.md`
- **Error responses** are documented in `contracts/error-responses.md`
- **Single-flight refresh pattern** is locked by FR-010 and the existing
  `tests/sync/test_auth_concurrent_refresh.py` baseline
- **Keychain backend choice** (`keyring` library) is locked by NFR-013
- **Cross-platform browser launching** uses stdlib `webbrowser`

The only previously-implicit decisions (TokenManager lifecycle, command
replacement vs. addition, AuthClient deletion, transport rewiring scope, SaaS
URL config, integration test discipline, KDF) are now explicit in §
"Architectural Decisions (Locked)" above.

**Phase 0 Output**: No new artifacts. spec.md + this plan.md + existing
contracts/ are the inputs to /spec-kitty.tasks.

---

## Phase 1: Design & Contracts

**Status**: Already complete from a prior round; preserved as-is.

- `data-model.md` (355 lines) defines `OAuthTokenResponse`, `StoredSession`,
  `Team`, `PKCEState`, `DeviceFlowState`, and the secure storage schemas.
- `contracts/oauth-authorize-endpoint.md` documents the SaaS authorize
  endpoint contract.
- `contracts/oauth-token-endpoint.md` documents token exchange + refresh.
- `contracts/oauth-device-endpoint.md` documents device authorization flow.
- `contracts/api-logout-endpoint.md` documents `/api/v1/logout`.
- `contracts/api-ws-token-endpoint.md` documents WS pre-connect token.
- `contracts/error-responses.md` documents all SaaS error codes.
- `quickstart.md` (634 lines) documents the validation walkthrough.

These artifacts are accurate to the SaaS contract from epic #49 as of
2026-04-09 (per `meta.json` mission creation date) and require no changes.

**Phase 1 Output**: Existing artifacts preserved. No regeneration.

---

## Work Package Decomposition Guidance for /spec-kitty.tasks

The next step (`/spec-kitty.tasks`) must produce a WP decomposition that
mirrors **spec.md §10** (which is the spec author's intended decomposition)
rather than reorganizing into module-based WPs. The high-level WP shape should
roughly be:

| WP | Title | Owns (concrete files) | Depends on |
|---|---|---|---|
| WP01 | TokenManager + SecureStorage Foundation | `auth/token_manager.py`, `auth/session.py`, `auth/secure_storage/**`, `auth/__init__.py`, `auth/config.py`, `auth/errors.py` | (none) |
| WP02 | Loopback Callback Handler + PKCE | `auth/loopback/**` | WP01 |
| WP03 | Device Authorization Flow Poller | `auth/device_flow/**` | WP01 |
| WP04 | Browser Login Flow (`auth login`) | `auth/flows/authorization_code.py`, `auth/flows/refresh.py`, partial `cli/commands/auth.py` (login command only) | WP01, WP02 |
| WP05 | Headless Login Flow (`auth login --headless`) | `auth/flows/device_code.py`, partial `cli/commands/auth.py` (--headless branch) | WP01, WP03, WP04 |
| WP06 | Logout Command (`auth logout`) | partial `cli/commands/auth.py` (logout command), uses `auth/http/**` for `/api/v1/logout` call | WP01, WP08 |
| WP07 | Status Command (`auth status`) | partial `cli/commands/auth.py` (status command) | WP01 |
| WP08 | HTTP Transport Rewiring | `auth/http/**`, `sync/client.py`, `sync/background.py`, `sync/batch.py`, `sync/body_transport.py`, `sync/runtime.py`, `sync/emitter.py`, `sync/events.py`, `tracker/saas_client.py` | WP01 |
| WP09 | WebSocket Pre-Connect Token Provisioning | `auth/websocket/**`, integration into `sync/client.py` ws path | WP01, WP08 |
| WP10 | Password Removal & Legacy Cleanup | `sync/auth.py` (DELETE), `tests/sync/test_auth*.py` (DELETE or rewrite) | WP04, WP05, WP06, WP07, WP08, WP09 |
| WP11 | Integration Tests, Concurrency Tests, Staging Validation | `tests/auth/integration/**`, `tests/auth/concurrency/**`, `tests/auth/stress/**`, audit subtask | WP01-WP10 |

**Critical guidance for /spec-kitty.tasks**:

1. WP06 and WP07 are SEPARATE WPs from WP04/WP05 because the spec §10 has
   them separate. Bundling all CLI commands into one WP (as the previous run
   did) creates a single 9-subtask WP that the implementer fills with stubs
   when API gaps appear.

2. WP04, WP05, WP06, WP07 all touch `cli/commands/auth.py` — they share
   ownership. Use `partial ownership` semantics (different functions in the
   same file) and serialize them in dependency order. WP04 is first
   (dependency for the others) and writes the structural shell.

3. WP08 is the **HTTP Transport Rewiring** WP with explicit `owned_files`
   listing the legacy transport modules. Its DoD includes the grep
   verification from D-4: zero hits for `CredentialStore|AuthClient` outside
   the auth package after WP08.

4. WP10 is the **deletion** WP. It deletes `sync/auth.py` and updates any
   remaining importers. It must be after WP08 because WP08 does the
   rewiring; WP10 just deletes the now-unreachable file.

5. WP11's integration tests use CliRunner / subprocess per D-6. Reviewer
   rejection criterion: any test that calls `AuthorizationCodeFlow().login()`
   without also using `CliRunner` is flagged.

6. **Every WP that creates a new public symbol** has a final subtask:
   "Verify integration: grep for callers from src/specify_cli/ outside this
   WP's owned files; assert at least one hit per public symbol." Reviewer
   re-runs the grep before approving.

7. **FR-to-WP mapping**: see the matrix below. The previous run had
   systematic FR mismatches. The /spec-kitty.tasks command must call
   `spec-kitty agent tasks map-requirements --batch '{...}'` with this
   exact mapping.

---

## FR-to-WP Mapping (authoritative)

| FR | Description (brief) | Owning WP |
|---|---|---|
| FR-001 | Browser PKCE primary, no password prompt | WP04 |
| FR-002 | Device flow fallback | WP05 |
| FR-003 | Loopback callback no port config | WP02 |
| FR-004 | 43-char crypto verifier RFC 7636 | WP02 |
| FR-005 | 5-min loopback callback timeout | WP02 |
| FR-006 | OS-backed secure storage when available | WP01 |
| FR-007 | File fallback with 0600 perms + consent | WP01 |
| FR-008 | No username/password prompts anywhere | WP10 |
| FR-009 | Auto-refresh before expiry | WP01 |
| FR-010 | Single-flight refresh | WP01 |
| FR-011 | 401 → auto-refresh + 1 retry | WP08 |
| FR-012 | Expired refresh terminates with clear message | WP01 |
| FR-013 | Logout calls `/api/v1/logout` | WP06 |
| FR-014 | Server logout failure does not block local delete | WP06 |
| FR-015 | Status shows user/team/expiry/storage backend | WP07 |
| FR-016 | TokenManager is sole source for ALL transports | WP08 |
| FR-017 | All HTTP callers use TokenManager | WP08 |
| FR-018 | Device polling respects interval, ≤10s cap | WP03 |
| FR-019 | User code human-friendly (ABCD-1234 format) | WP03 |
| FR-020 | `--headless` does not open browser | WP05 |

| NFR | Description (brief) | Owning WP |
|---|---|---|
| NFR-001 | Browser login < 30s | WP11 (perf test) |
| NFR-002 | Headless login < 5s | WP11 (perf test) |
| NFR-003 | Device polling timeout ≤ 15min | WP03 |
| NFR-004 | Token refresh < 500ms p99 | WP11 (perf test) |
| NFR-005 | Refresh blocks user CLI < 3s | WP11 (perf test) |
| NFR-006 | Single-flight overhead < 100ms | WP11 (perf test) |
| NFR-007 | Loopback port search 28888-28898 | WP02 |
| NFR-008 | 99.9% refresh success (SLO) | WP11 (staging validation) |
| NFR-009 | Zero duplicate concurrent refreshes | WP01 + WP11 (concurrency test) |
| NFR-010 | Storage durability under concurrent access | WP01 + WP11 (stress test) |
| NFR-011 | Atomic file ops or transactions | WP01 |
| NFR-012 | Backend selection logged + visible | WP01 + WP07 |
| NFR-013 | File fallback 0600 perms enforced | WP01 |

---

## Risk Register

| Risk | Mitigation |
|---|---|
| Implementer adds parallel command set instead of replacing existing one | D-2 explicit; WP04 reviewer checks that legacy login function is gone before approving |
| New TokenManager has zero callers (dead code) | D-7 grep audit per WP; WP11 cross-WP audit before staging validation |
| Test passes with synthetic fixture instead of real CLI path | D-6 explicit; WP11 reviewer rejects flow-class-only tests |
| SaaS base URL leaks into source code | D-5 explicit; WP-level grep for `https://api.spec-kitty` rejects the WP |
| File fallback key derivation is hostname-only | D-8 explicit; WP01 reviewer verifies scrypt + salt file usage |
| Hard cutover removes legacy code before transports are rewired | WP10 (deletion) explicitly depends on WP08 (rewiring) |
| Integration tests pass while CLI is broken | D-6 explicit reviewer criterion; WP11 must include at least one CliRunner test per scenario |
| WPs that share `cli/commands/auth.py` collide on edits | WP04 writes the structural shell first; WP05/WP06/WP07 only add their command function within the same file in dependency order |

---

## Complexity Tracking

| Category | Complexity | Notes |
|---|---|---|
| Number of FRs | 20 | Spec is fully specified |
| Number of NFRs | 13 | Several measurable thresholds |
| Number of WPs | 11 | Matches spec §10 decomposition |
| Estimated subtasks | 60-80 | 5-8 per WP |
| Cross-WP file ownership | 1 file shared (cli/commands/auth.py) | Dependency-ordered serialization |
| Files DELETED | 1+ | sync/auth.py |
| Files REWIRED | 8+ | sync/* and tracker/saas_client.py |
| Files CREATED | ~25 | New auth/ package |
| Test files CREATED | ~20 | Unit + integration + concurrency + stress |
| External dependencies (new) | 0 | All new libs already in repo |
| Charter dependencies | None (skipped) | No charter file |

---

## Branch Strategy

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Mission branch (will be created at /spec-kitty.implement)**: `kitty/mission-080-browser-mediated-oauth-cli-auth`
- **Lane workspaces**: computed by `finalize-tasks` based on WP write_scope
  overlap. `cli/commands/auth.py` shared ownership across WP04-WP07 will
  likely place those WPs in a single lane that runs sequentially.

---

## Next Step

Run `/spec-kitty.tasks` to generate `tasks.md` and the per-WP prompt files
based on this plan and spec.md §10. The /spec-kitty.tasks command must:

1. Mirror spec.md §10 WP decomposition exactly (11 WPs as defined above)
2. Apply the FR-to-WP mapping table above via
   `spec-kitty agent tasks map-requirements --batch`
3. Set `owned_files` per WP to include both NEW files and EXISTING files
   that must be modified (especially WP08's transport rewiring)
4. Add a "verify integration via grep" subtask to every WP that creates a new
   public symbol
5. Add a "use CliRunner / subprocess" criterion to every WP11 integration test
6. Run `spec-kitty agent mission finalize-tasks --json` to compute lanes and
   commit the artifacts

After /spec-kitty.tasks finishes successfully, the orchestrator may run
`/spec-kitty-implement-review` to dispatch implementation.

**Final branch contract restatement**:
- **Current branch**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: `true`

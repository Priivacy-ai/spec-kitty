---
work_package_id: WP01
title: SaaS Client Foundation
dependencies: []
requirement_refs:
- C-007
- FR-003
- NFR-001
- NFR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-widen-mode-and-write-back-01KPXFGJ
base_commit: 41983ee6dffad54ea0456b64acc4bc1a1cb72dfd
created_at: '2026-04-23T16:00:35.416008+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:sonnet-4-7:python-reviewer:reviewer"
shell_pid: "69576"
history:
- date: '2026-04-23T15:43:52Z'
  event: created
agent_profile: python-implementer
authoritative_surface: src/specify_cli/saas_client/
execution_mode: code_change
mission_slug: cli-widen-mode-and-write-back-01KPXFGJ
model: claude-sonnet-4-7
owned_files:
- src/specify_cli/saas_client/__init__.py
- src/specify_cli/saas_client/client.py
- src/specify_cli/saas_client/auth.py
- src/specify_cli/saas_client/endpoints.py
- src/specify_cli/saas_client/errors.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile:

```
/ad-hoc-profile-load python-implementer
```

This profile contains the coding standards, patterns, and constraints for this codebase.

---

## Objective

Create `src/specify_cli/saas_client/` — a thin, mockable HTTP client package for communicating with spec-kitty-saas #110 (widen + audience-default endpoints) and #111 (discussion fetch endpoint). This client is used exclusively by the widen flow modules and the prereq checker.

No existing code is modified. This is a net-new package.

---

## Context

The CLI does not embed an LLM or call inference APIs. All SaaS calls are thin HTTP (via `httpx`). The client must:
- Be **mockable** for tests (dependency-injected `httpx.Client`).
- Be **non-fatal** on failure: callers handle `SaasClientError` and suppress it gracefully (C-007: local-first).
- Use short timeouts (500ms for prereq probes, 5s default for data calls, 10s for discussion fetch).
- Read auth from `SPEC_KITTY_SAAS_TOKEN` env var, falling back to `.kittify/saas-auth.json`.

---

## Branch Strategy

This WP is planned against `main` and must be merged back into `main`.

When you are handed this WP via `spec-kitty agent action implement WP01`, the runtime will have resolved the correct execution workspace and branch. Implement all changes there.

Implementation command (no dependencies):
```bash
spec-kitty agent action implement WP01 --agent claude
```

---

## Subtask T001 — Create `saas_client/` Package Skeleton

**Purpose:** Establish the directory structure and package `__init__.py` with public re-exports.

**Files to create:**
- `src/specify_cli/saas_client/__init__.py`
- `src/specify_cli/saas_client/client.py` (stub)
- `src/specify_cli/saas_client/auth.py` (stub)
- `src/specify_cli/saas_client/endpoints.py` (stub)
- `src/specify_cli/saas_client/errors.py` (stub)

**`__init__.py` should re-export:**
```python
from specify_cli.saas_client.client import SaasClient
from specify_cli.saas_client.errors import SaasClientError, SaasTimeoutError, SaasAuthError, SaasNotFoundError
from specify_cli.saas_client.auth import AuthContext, load_auth_context

__all__ = [
    "SaasClient",
    "SaasClientError", "SaasTimeoutError", "SaasAuthError", "SaasNotFoundError",
    "AuthContext", "load_auth_context",
]
```

**Validation:** `python -c "from specify_cli.saas_client import SaasClient"` exits 0.

---

## Subtask T002 — Implement `SaasClient` Class

**Purpose:** Core HTTP client with dependency-injected `httpx.Client` for testability.

**File:** `src/specify_cli/saas_client/client.py`

**Class signature:**
```python
from __future__ import annotations
import httpx
from specify_cli.saas_client.auth import AuthContext

class SaasClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = 5.0,
        _http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._http = _http or httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> SaasClient:
        """Construct from environment. Raises SaasClientError if auth unavailable."""
        ctx = load_auth_context()
        return cls(base_url=ctx.saas_url, token=ctx.token)
```

**Key design decisions:**
- All methods raise `SaasClientError` (or subclasses) on failure — never propagate raw `httpx` exceptions.
- The `_http` parameter is used in tests by passing a mock `httpx.Client`.
- Use `contextlib.suppress` in callers, not here.

**Validation:** `SaasClient("http://localhost", "token")` constructs without error.

---

## Subtask T003 — Implement Auth Context

**Purpose:** Read `SPEC_KITTY_SAAS_URL` + `SPEC_KITTY_SAAS_TOKEN` from environment; fall back to `.kittify/saas-auth.json` if env vars absent.

**File:** `src/specify_cli/saas_client/auth.py`

**Implementation:**
```python
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from specify_cli.saas_client.errors import SaasAuthError

@dataclass(frozen=True)
class AuthContext:
    saas_url: str
    token: str
    team_slug: str | None = None  # extracted from token payload if available

def load_auth_context(repo_root: Path | None = None) -> AuthContext:
    """Load SaaS auth context. Raises SaasAuthError if unavailable."""
    url = os.environ.get("SPEC_KITTY_SAAS_URL", "").strip()
    token = os.environ.get("SPEC_KITTY_SAAS_TOKEN", "").strip()

    if not token and repo_root is not None:
        auth_file = repo_root / ".kittify" / "saas-auth.json"
        if auth_file.exists():
            data = json.loads(auth_file.read_text())
            token = data.get("token", "")
            url = url or data.get("saas_url", "")

    if not token:
        raise SaasAuthError("SPEC_KITTY_SAAS_TOKEN not set and .kittify/saas-auth.json not found")
    if not url:
        url = "https://api.spec-kitty.io"  # production default

    return AuthContext(saas_url=url, token=token)
```

**Fallback behavior:** If `load_auth_context()` raises `SaasAuthError`, callers (primarily `check_prereqs()`) catch it and return `PrereqState(saas_reachable=False, teamspace_ok=False, slack_ok=False)` silently (C-007, C-009).

---

## Subtask T004 — Implement Endpoint Helpers

**Purpose:** Typed endpoint methods on `SaasClient` corresponding to each SaaS surface used by the widen flow.

**File:** `src/specify_cli/saas_client/client.py` (add methods to the `SaasClient` class)

**Methods to implement:**

```python
def get_audience_default(self, mission_id: str) -> list[str]:
    """GET /api/v1/missions/{id}/audience-default → list of member display names.
    Timeout: 5s. Raises SaasClientError on failure."""

def post_widen(self, decision_id: str, invited: list[str]) -> WidenResponse:
    """POST /api/v1/decision-points/{id}/widen with {"invited": invited}.
    Returns WidenResponse. Raises SaasClientError on non-2xx."""

def get_team_integrations(self, team_slug: str) -> list[str]:
    """GET /api/v1/teams/{slug}/integrations → list of integration names (e.g. ["slack"]).
    Timeout: 500ms (prereq probe). Raises SaasClientError on failure."""

def health_probe(self) -> bool:
    """GET /api/v1/health → True if 200. Timeout: 500ms. Returns False on any error (never raises)."""

def fetch_discussion(self, decision_id: str) -> DiscussionData:
    """GET /api/v1/decision-points/{id}/discussion → raw discussion data.
    Timeout: 10s (per NFR-002). Raises SaasClientError on failure."""
```

**Import note:** `WidenResponse` and `DiscussionData` are imported from `specify_cli.widen.models` — but to avoid circular imports, define minimal response TypedDicts in `endpoints.py` and import from there.

**Error mapping:**
- `httpx.TimeoutException` → `SaasTimeoutError`
- HTTP 401/403 → `SaasAuthError`
- HTTP 404 → `SaasNotFoundError`
- Other non-2xx → `SaasClientError`

---

## Subtask T005 — Implement Error Hierarchy

**Purpose:** Typed exception hierarchy so callers can discriminate between auth, timeout, and general errors.

**File:** `src/specify_cli/saas_client/errors.py`

```python
from __future__ import annotations

class SaasClientError(Exception):
    """Base error for all SaaS client failures."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

class SaasTimeoutError(SaasClientError):
    """Raised when an HTTP request to SaaS exceeds the configured timeout."""

class SaasAuthError(SaasClientError):
    """Raised on HTTP 401/403 or missing credentials."""

class SaasNotFoundError(SaasClientError):
    """Raised on HTTP 404 (decision or mission not found)."""
```

**Usage pattern in callers:**
```python
import contextlib
from specify_cli.saas_client import SaasClient, SaasClientError

# Non-fatal pattern:
with contextlib.suppress(SaasClientError):
    integrations = client.get_team_integrations(team_slug)
```

---

## Definition of Done

- [ ] `src/specify_cli/saas_client/` package with 5 files exists and imports cleanly.
- [ ] `SaasClient.from_env()` constructs from `SPEC_KITTY_SAAS_TOKEN` env var.
- [ ] All five endpoint methods exist with correct signatures and error mapping.
- [ ] `SaasClientError` hierarchy: base + 3 subclasses.
- [ ] `tests/specify_cli/saas_client/test_client.py` exists (stubs OK; full tests in WP10).
- [ ] `mypy src/specify_cli/saas_client/` exits 0.
- [ ] `ruff check src/specify_cli/saas_client/` exits 0.
- [ ] `from __future__ import annotations` on all new modules.

## Risks

- **Circular import:** `client.py` imports from `widen.models` for response types. Solution: define lightweight `TypedDict` response shapes in `endpoints.py` and have `widen.models` import from `saas_client.endpoints`, not vice versa. Or keep response parsing in `widen.models` and return raw dicts from `SaasClient`, letting callers parse.
- **SaaS contracts not finalized:** #110 and #111 endpoints may not be live yet. `SaasClient` is mockable by design — tests in WP10 use `respx` to stub responses. The endpoint paths above match the plan.md spec; adjust if contracts differ.

## Reviewer Guidance

Verify: `SaasClient("http://x", "tok", _http=mock_client)` calls `mock_client.get(...)` correctly in the test. Verify timeout configuration is passed to `httpx.Client`. Verify error types match the documented hierarchy.

## Activity Log

- 2026-04-23T16:05:14Z – claude – shell_pid=67750 – Ready for review: saas_client foundation with typed models + errors + auth reuse
- 2026-04-23T16:06:02Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=68626 – Started review via action command
- 2026-04-23T16:08:15Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=68626 – Moved to planned
- 2026-04-23T16:08:56Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=69012 – Started implementation via action command
- 2026-04-23T16:10:46Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=69012 – Moved to for_review
- 2026-04-23T16:11:01Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=69295 – Started review via action command
- 2026-04-23T16:12:34Z – claude:sonnet-4-7:python-implementer:implementer – shell_pid=69295 – Cycle 2: fixed mypy errors by changing dict[str, object] to dict[str, Any]
- 2026-04-23T16:12:49Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=69576 – Started review via action command
- 2026-04-23T16:13:36Z – claude:sonnet-4-7:python-reviewer:reviewer – shell_pid=69576 – Cycle 2 review passed: mypy clean (Success: no issues found in 5 source files), ruff clean, 20/20 tests pass. Type fix correct and complete.

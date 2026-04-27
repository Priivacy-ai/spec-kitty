---
work_package_id: WP01
title: 'compat package foundation: LatestVersionProvider'
dependencies: []
requirement_refs:
- FR-002
- FR-005
- FR-022
- NFR-002
- NFR-005
- NFR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
base_commit: 1ea2a8353983f302a43cbaec9209ddfdd3750eef
created_at: '2026-04-27T08:38:41.928182+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
shell_pid: '55038'
history:
- at: '2026-04-27T08:19:12Z'
  actor: planner
  note: WP authored from /spec-kitty.tasks for mission cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
authoritative_surface: src/specify_cli/compat/
execution_mode: code_change
mission_id: 01KQ6YDNMX2X2AN4WH43R5K2ZS
mission_slug: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN
owned_files:
- src/specify_cli/compat/__init__.py
- src/specify_cli/compat/provider.py
- tests/specify_cli/compat/__init__.py
- tests/specify_cli/compat/test_provider_pypi.py
- tests/specify_cli/compat/test_provider_no_network.py
- tests/specify_cli/compat/test_provider_fake.py
priority: P0
tags: []
---

# WP01 — compat package foundation: LatestVersionProvider

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP01 --agent <name>` from `lanes.json`. Do not create your own worktree.

## Objective

Stand up the `src/specify_cli/compat/` package and the network abstraction it depends on. After this WP merges, every later WP can consume a `LatestVersionProvider` to ask "what is the newest published `spec-kitty-cli` version?" without coupling to PyPI.

This is a **foundation** work package. It must merge before WP06 (planner) can run, but it has no dependencies of its own.

## Context

- Spec: [`spec.md`](../spec.md) — see FR-002, FR-005, FR-006, FR-022, FR-024, NFR-002, NFR-005, NFR-008.
- Plan: [`plan.md`](../plan.md) §"Engineering Alignment" decision 2 (provider abstraction with PyPI default).
- Research: [`research.md`](../research.md) §R-01 (PyPI JSON endpoint).
- Data model: [`data-model.md`](../data-model.md) §1.11 (`LatestVersionResult`).
- Security checklist: [`checklists/security.md`](../checklists/security.md) — CHK011 (TLS), CHK012 (response size cap), CHK013 (hostname allowlist), CHK014 (redirects), CHK015 (downgrade payload), CHK016 (malformed version), CHK018 (no PII headers), CHK048 (no telemetry), CHK049 (User-Agent).
- Charter: typer + rich + ruamel.yaml + pytest + mypy --strict + 90%+ coverage on new code.

## Subtasks

### T001 — Create `compat/` package skeleton

**Purpose**: Establish the package directory so subsequent files have a home.

**Steps**:
1. Create `src/specify_cli/compat/__init__.py` — leave it as an **empty placeholder** in this WP. WP06 will populate the public API exports. Do NOT add any imports yet (avoids circular-import risk with adapters in WP05).
2. Create `tests/specify_cli/compat/__init__.py` — empty file.

**Files**: `src/specify_cli/compat/__init__.py` (new, empty), `tests/specify_cli/compat/__init__.py` (new, empty).

**Validation**: `python -c "import specify_cli.compat"` succeeds.

### T002 — Implement `LatestVersionProvider` Protocol + `LatestVersionResult` dataclass

**Purpose**: Define the abstract contract every provider must satisfy.

**Steps**:
1. In `src/specify_cli/compat/provider.py`, declare:
   - `LatestVersionResult` — frozen dataclass with fields `version: str | None`, `source: Literal["pypi","none"]`, `error: str | None`.
   - `LatestVersionProvider` — typing.Protocol with one method `def get_latest(self, package: str) -> LatestVersionResult: ...`.
2. The result MUST never raise from `get_latest`. Errors are encoded as `LatestVersionResult(version=None, source="none", error="<short_description>")`.
3. The `error` string must be a fixed-vocabulary token (e.g. `"timeout"`, `"http_error"`, `"parse_error"`, `"oversized"`) — no PII, no user paths (security CHK030).

**Files**: `src/specify_cli/compat/provider.py` (new).

**Validation**: `mypy --strict` accepts the file; the Protocol is structurally satisfied by a one-line stub class.

### T003 — Implement `PyPIProvider`

**Purpose**: The default provider that hits PyPI.

**Steps**:
1. `PyPIProvider(timeout_s: float = 2.0, package_name_default: str = "spec-kitty-cli")`.
2. `get_latest(package)` does:
   - URL: `f"https://pypi.org/pypi/{package}/json"` — and ONLY this hostname (CHK013). Use `httpx.Client(follow_redirects=False, timeout=timeout_s)`.
   - User-Agent header: `f"spec-kitty-cli/{installed_version} compat-planner"` — no other headers (CHK018, CHK049).
   - Response cap: read at most 1 MB (`response.content[:1_048_576]`); if the response is larger, return `error="oversized"` (CHK012).
   - Parse JSON; pull `info.version`. If parse fails or field is missing, return `error="parse_error"`.
   - Sanitise version string against regex `^[A-Za-z0-9.\-+]{1,64}$`. If it doesn't match, return `error="parse_error"` (CHK016, CHK028).
   - Wrap entire body in `try/except httpx.HTTPError, ValueError, json.JSONDecodeError`; on any exception return appropriate fixed-vocabulary error.
3. The provider does **not** parse, compare, or judge the version — it just returns it. The planner does the comparison.

**Files**: `src/specify_cli/compat/provider.py` (extend).

**Validation**:
- Successful request returns `LatestVersionResult(version="2.0.14", source="pypi", error=None)`.
- Timeout returns `error="timeout"`.
- 500 status returns `error="http_error"`.
- 1.5 MB body returns `error="oversized"`.
- ANSI-injected version string returns `error="parse_error"`.
- TLS verification is on by default (httpx default) — do NOT disable.

### T004 — Implement `NoNetworkProvider` and `FakeLatestVersionProvider`

**Purpose**: Drop-in replacements for CI mode and tests.

**Steps**:
1. `NoNetworkProvider`: `get_latest(package)` always returns `LatestVersionResult(version=None, source="none", error=None)`. It MUST NOT open a socket — implementer should ensure no network code is reachable (no httpx import in this class's hot path).
2. `FakeLatestVersionProvider(version: str | None = None, *, error: str | None = None)`: returns the configured value. Used by tests.
3. Both classes implement the same Protocol structurally — no inheritance from `PyPIProvider`.

**Files**: `src/specify_cli/compat/provider.py` (extend).

**Validation**: `NoNetworkProvider` returns `version=None` 100% of the time; `FakeLatestVersionProvider("2.0.14")` returns `version="2.0.14"`.

### T005 — Unit tests for all three providers

**Purpose**: Hit ≥90% coverage on `compat/provider.py` without touching the network.

**Steps**:
1. `tests/specify_cli/compat/test_provider_pypi.py`:
   - Use `respx` if available; otherwise `pytest-httpx`; otherwise `unittest.mock.patch("httpx.Client.get")`. Pick whichever is already in `pyproject.toml`'s dev deps. If none is, fall back to `unittest.mock`.
   - Cases: success, timeout, 500, 404, malformed JSON, missing `info.version`, oversized body (mock returns 2 MB), version string with ANSI escapes, version string with shell metacharacters, redirect (assert NOT followed), TLS failure simulated.
   - Assert User-Agent header is set; assert NO other request headers leak data.
2. `tests/specify_cli/compat/test_provider_no_network.py`:
   - Assert `get_latest` returns `version=None` and `source="none"`.
   - Assert no httpx client is constructed (use `mock.patch("httpx.Client", side_effect=AssertionError)`).
3. `tests/specify_cli/compat/test_provider_fake.py`:
   - Round-trip the fake provider with a few configured values.

**Files**: `tests/specify_cli/compat/test_provider_pypi.py`, `tests/specify_cli/compat/test_provider_no_network.py`, `tests/specify_cli/compat/test_provider_fake.py`.

**Validation**: `pytest tests/specify_cli/compat/` passes; `pytest-cov` reports ≥90% on `compat/provider.py`.

## Definition of Done

- [ ] `src/specify_cli/compat/__init__.py` exists (empty).
- [ ] `src/specify_cli/compat/provider.py` exposes `LatestVersionResult`, `LatestVersionProvider` Protocol, `PyPIProvider`, `NoNetworkProvider`, `FakeLatestVersionProvider`.
- [ ] All security properties from CHK011-CHK016, CHK018, CHK048, CHK049 enforced in code (assert in PR review).
- [ ] All three providers implement the Protocol structurally (no inheritance).
- [ ] `mypy --strict src/specify_cli/compat/` clean.
- [ ] `ruff check src/specify_cli/compat/ tests/specify_cli/compat/` clean.
- [ ] `pytest tests/specify_cli/compat/test_provider_*.py -v` green.
- [ ] Coverage on `compat/provider.py` ≥ 90%.
- [ ] No real network calls during tests (CI assertion).

## Risks

- httpx is already a runtime dep in `spec-kitty` (per CLAUDE.md history); confirm via `pyproject.toml`. If absent, prefer adding it (it's a high-quality stdlib alternative); document the decision in the WP review.
- `respx` may not be installed; fall back order is `respx` → `pytest-httpx` → `unittest.mock`. Document the choice in the test file's module docstring.
- The User-Agent header must NOT include the OS, hostname, or any user-identifying data.

## Reviewer Guidance

When reviewing this WP:

1. **Network safety**: confirm no test reaches the real network (CI predicate test in WP08 will catch this too, but check here for early defense).
2. **Sanitisation**: the version string MUST be regex-validated; an attacker-controlled response with `\x1b[31mUPGRADE NOW\x1b[0m` as the version must be rejected.
3. **Error vocabulary**: the `error` field uses a small fixed token set; no free-form strings.
4. **No leaks**: no headers, no logs, no telemetry beyond `User-Agent: spec-kitty-cli/<version> compat-planner`.
5. **Protocol satisfaction**: confirm tests structurally satisfy `LatestVersionProvider` for all three classes; `mypy --strict` clean.

## Implementation command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

This WP has no dependencies; it can run as soon as `lanes.json` is computed by `finalize-tasks`.

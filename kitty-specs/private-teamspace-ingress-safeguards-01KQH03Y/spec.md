# CLI Private Teamspace Ingress Safeguards

**Mission ID**: 01KQH03YSS4H9PQVJ5YCTGZYMR
**Mission Slug**: private-teamspace-ingress-safeguards-01KQH03Y
**Mission Type**: software-dev
**Status**: Specified
**Created**: 2026-05-01
**Related Issue**: Priivacy-ai/spec-kitty-saas#142

---

## Problem Statement

The Spec Kitty SaaS rejects direct sync ingress whose target is not a Private Teamspace, returning:

```text
Forbidden: Direct sync ingress must target Private Teamspace.
```

The CLI today resolves the ingress target by falling back to `default_team_id`, and ultimately to `teams[0]`, when the stored auth session does not surface a Private Teamspace. A user whose authenticated session contains only shared Teamspaces — because of a stale local session, an old SaaS server, or a malformed `/api/v1/me` payload — therefore generates direct-ingress traffic that the SaaS will refuse, and that refusal is currently appended to the stdout of strict-JSON commands such as `spec-kitty agent mission create --json`.

The companion SaaS change in issue `Priivacy-ai/spec-kitty-saas#142` will make shared-only authenticated sessions impossible. This mission ensures the CLI defends itself independently of that SaaS change so that direct ingress can never target a shared Teamspace under any circumstance, and so that strict-JSON command output is never corrupted by background sync diagnostics.

---

## Goals

- Eliminate every code path where direct sync ingress can resolve a non-Private-Teamspace target.
- Recover transparently when the stored session is the only thing missing private-team identity, by performing a one-shot rehydrate against `/api/v1/me`.
- Fail closed and noisily on stderr when no Private Teamspace can be obtained, without breaking the local mission/task/status commands that triggered the ingress attempt.
- Keep `--json` mode strict-JSON parseable on stdout regardless of sync health.

---

## Out of Scope

- The companion SaaS-side change in `Priivacy-ai/spec-kitty-saas#142` that prevents shared-only authenticated sessions from being issued. This mission assumes that fix may not be deployed yet.
- Shared-Teamspace selection in non-ingress UI surfaces and tracker control-plane operations that are intentionally shared-team-scoped.
- Tracker provider read paths that are deliberately shared-team-scoped.
- Any change that hides SaaS failures by silently writing to a shared team.
- Renaming or removing `pick_default_team_id`; it is preserved for login/UI default-team display.

---

## Actors

| Actor | Role |
|-------|------|
| CLI User | Runs commands such as `spec-kitty agent mission create --json` with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` |
| Spec Kitty CLI | Resolves the ingress target Teamspace, performs rehydrate, emits diagnostics |
| Spec Kitty SaaS | Authoritative source for `/api/v1/me`, `/api/v1/events/batch/`, and `/api/v1/ws-token` |

---

## User Scenarios

### Scenario 1 — Healthy session with a Private Teamspace (primary flow)

1. User runs a mission/task/status command with sync enabled.
2. CLI resolves the ingress target via the strict private-team helper.
3. Helper returns the Private Teamspace from the existing session without rehydrating.
4. Direct ingress is sent with `X-Team-Slug` set to the Private Teamspace id.
5. Command exits 0; stdout is unchanged.

### Scenario 2 — Stored session lacks a Private Teamspace, rehydrate succeeds

1. User runs a mission/task/status command with sync enabled.
2. Strict helper finds no Private Teamspace in `StoredSession.teams`.
3. CLI performs a single authenticated GET to `/api/v1/me`.
4. Response includes a Private Teamspace; CLI updates `StoredSession.teams` and `default_team_id` on disk.
5. Strict helper re-evaluates and returns the Private Teamspace id.
6. Direct ingress proceeds using that id; command exits 0.

### Scenario 3 — Stored session lacks a Private Teamspace, rehydrate also fails

1. User runs a mission/task/status command with sync enabled.
2. Strict helper finds no Private Teamspace; rehydrate is attempted once.
3. `/api/v1/me` still returns no Private Teamspace (or the request fails).
4. CLI emits a stderr/log diagnostic stating that the SaaS session payload is invalid for direct ingress and that no ingress was attempted.
5. No HTTP request is sent to `/api/v1/events/batch/` and no shared id is sent to `/api/v1/ws-token`.
6. The local command (mission create, task update, status read) succeeds; exit code is 0; stdout remains strict-JSON parseable in `--json` mode.

### Scenario 4 — Default points at a shared team but a Private Teamspace exists

1. Stored session has `default_team_id` set to a shared team id, but `StoredSession.teams` contains a Private Teamspace.
2. Strict helper ignores `default_team_id` and selects the Private Teamspace from the team list.
3. Direct ingress proceeds; existing "private team wins even when default drifts" behavior is preserved.

### Scenario 5 — Auth refresh after server-side membership change

1. Refresh flow exchanges tokens with the SaaS.
2. The current session lacks a Private Teamspace, or the server-issued payload advertises a newer membership generation.
3. Refresh re-fetches `/api/v1/me` and updates `StoredSession.teams` and `default_team_id` from the fresh payload.
4. Refresh does not blindly preserve a stale `teams` list when private identity is missing.

### Scenario 6 — Strict sync command (`spec-kitty sync now --strict`)

1. User invokes a sync-primary command whose contract is "fail loudly when sync cannot complete".
2. Strict helper / rehydrate cannot resolve a Private Teamspace.
3. Command exits non-zero, consistent with that command's existing failure semantics.
4. This explicit-sync path is the only place where missing Private Teamspace causes a non-zero CLI exit.

---

## Domain Language

| Term | Canonical Meaning | Avoid |
|------|------------------|-------|
| Private Teamspace | A Teamspace where `is_private_teamspace=true`; the only valid target for direct sync ingress. In identifier-context (helper names like `require_private_team_id`, log fields like `direct_ingress_missing_private_team`) the compact form "private team" is acceptable; in narrative prose, prefer "Private Teamspace". | "personal team", "default team" |
| Direct sync ingress | CLI-originated writes to SaaS endpoints `/api/v1/events/batch/` and `/api/v1/ws-token` | "sync", "upload" (too broad — both apply to non-ingress paths too) |
| Strict private-team resolver | The single canonical helper, e.g. `require_private_team_id(session)`, that returns only a `is_private_teamspace=true` team or signals missing | "team picker", "default team helper" (those describe `pick_default_team_id`) |
| One-shot rehydrate | A single authenticated GET to `/api/v1/me` that updates `StoredSession.teams` and `default_team_id` and is **not** retried within the same call | "refresh", "reload" (reserved for token refresh flow) |
| Strict-JSON command | A CLI invocation in `--json` mode whose stdout must be parseable by `json.loads` without ignoring trailing content | "JSON output" |

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Provide a single canonical CLI helper for resolving the direct-ingress target Teamspace (e.g. `require_private_team_id(session)`) that returns only a team where `is_private_teamspace=true`. | Approved |
| FR-002 | The strict resolver must never use `default_team_id` and never use `teams[0]` as a fallback for direct sync ingress, even when those values are present and non-empty. | Approved |
| FR-003 | When the strict resolver finds no Private Teamspace in the stored session, the CLI must attempt exactly one authenticated GET to `/api/v1/me` and, if the response carries a Private Teamspace, update `StoredSession.teams` and `default_team_id` on disk and re-resolve. | Approved |
| FR-004 | If the one-shot rehydrate still does not yield a Private Teamspace, the CLI must skip direct ingress entirely (no HTTP request to `/api/v1/events/batch/` or `/api/v1/ws-token`) and emit a targeted diagnostic stating that the SaaS session payload is invalid for direct ingress. | Approved |
| FR-005 | The batch sync code path (`src/specify_cli/sync/batch.py`) must use the strict resolver and must not set the `X-Team-Slug` header unless the value is a Private Teamspace id. | Approved |
| FR-006 | The websocket client (`src/specify_cli/sync/client.py`) must use the strict resolver for WebSocket token provisioning and must never post a shared team id to `/api/v1/ws-token`. | Approved |
| FR-007 | The event emitter and offline queue (`src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/queue.py`) must use the strict resolver for any team-identity metadata associated with direct ingress. | Approved |
| FR-008 | The auth refresh flow (`src/specify_cli/auth/flows/refresh.py`) must rehydrate team membership from `/api/v1/me` when the current session has no Private Teamspace, or when the server advertises a newer membership payload, instead of blindly preserving stale `teams`. | Approved |
| FR-009 | All sync warnings, rehydrate failures, and background connection diagnostics produced during a `--json` agent command must be written to stderr or structured logs, and must never appear on stdout after the JSON object. | Approved |
| FR-010 | When rehydrate cannot produce a Private Teamspace, the local command (mission create, task update, status read, etc.) must still succeed with exit code 0; only sync-primary commands (e.g. `spec-kitty sync now --strict`) may exit non-zero on missing Private Teamspace, and only when their existing contract treats unsynced events as failure. | Approved |
| FR-011 | When the stored session already contains a Private Teamspace, the existing direct-ingress behavior must be preserved, including the case where `default_team_id` points at a shared team. | Approved |
| FR-012 | `pick_default_team_id` must remain available for login/session default-team display, but its docstring/contract must explicitly state that it is not valid as a fallback for direct ingress. | Approved |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Rehydrate is one-shot per CLI process for a shared-only session: single-flight via lock, plus a process-lifetime negative cache so repeat ingress attempts in the same process do not re-issue the GET. No retry loop, no exponential backoff, no in-process re-entry. | At most 1 GET to `/api/v1/me` per CLI process for a shared-only session; zero GETs for healthy sessions; cache is busted only on session-identity change, fresh login, or explicit `force=True` repair paths. | Approved |
| NFR-002 | Direct-ingress diagnostics must be machine-distinguishable: error category, whether rehydrate was attempted, and whether ingress was sent must be derivable from the stderr/log line. | 100% of skip-ingress events emit a structured log entry containing `category="direct_ingress_missing_private_team"`, `rehydrate_attempted: bool`, `ingress_sent: false`. | Approved |
| NFR-003 | `--json` strict-mode stdout must remain parseable by `json.loads(stdout)` for any agent command tested in this mission, regardless of sync health, including the case where the SaaS rejects ingress. | 100% of strict-JSON tests in this mission pass `json.loads(stdout)` without modification. | Approved |
| NFR-004 | Existing tests that prove "Private Teamspace wins even when `default_team_id` drifts" continue to pass without modification. | 0 regressions in the affected test files at the start of mission. | Approved |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Do not change shared-Teamspace selection in non-ingress UI or tracker control-plane operations unless they are proven to perform direct sync ingress. | Approved |
| C-002 | Do not change tracker-provider read paths to always use a Private Teamspace; reads that are intentionally shared-team-scoped must remain shared-team-scoped. | Approved |
| C-003 | Do not hide SaaS failures by writing to a shared team. Failure must surface as a stderr/log diagnostic and a skipped ingress, never as a silent shared-team write. | Approved |
| C-004 | Do not remove or rename `pick_default_team_id`; it is preserved for login/session default display. | Approved |
| C-005 | Do not introduce a separate auth/me HTTP client; reuse the existing authenticated HTTP layer (`src/specify_cli/auth/http` or equivalent rehydrate module). | Approved |

---

## Acceptance Criteria

| ID | Criterion | Maps to |
|----|-----------|---------|
| AC-001 | A session containing only shared teams never causes an HTTP request to `/api/v1/events/batch/` with `X-Team-Slug` set to a shared team. | FR-002, FR-005 |
| AC-002 | A session containing only shared teams triggers a single `/api/v1/me` rehydrate before direct ingress is attempted. | FR-003, NFR-001 |
| AC-003 | If `/api/v1/me` returns a Private Teamspace, direct ingress uses that id and the stored session is updated on disk. | FR-003 |
| AC-004 | If `/api/v1/me` still returns no Private Teamspace, no direct ingress request is sent. | FR-004 |
| AC-005 | WebSocket provisioning never posts a shared team id to `/api/v1/ws-token`. | FR-006 |
| AC-006 | `spec-kitty agent mission create --json` remains strict-JSON parseable (single `json.loads(stdout)` call) even when background sync cannot connect. | FR-009, NFR-003 |
| AC-007 | Existing tests proving "Private Teamspace wins even when default drifts" still pass. | FR-011, NFR-004 |
| AC-008 | When direct ingress is skipped due to missing Private Teamspace, the originating local command still exits 0 and produces its normal output. | FR-010 |
| AC-009 | Auth refresh updates stale team membership from `/api/v1/me` when the session lacks private identity. | FR-008 |

---

## Success Criteria

- **SC-001**: 100% of direct-ingress attempts on a shared-only session result in zero HTTP requests to `/api/v1/events/batch/` and zero requests to `/api/v1/ws-token`, measured across the test plan.
- **SC-002**: 100% of `--json` agent command outputs in this mission's test suite parse with a single `json.loads(stdout)` call regardless of sync health.
- **SC-003**: When a user's session was healthy before the change, the post-change behavior is byte-identical for direct ingress (no extra HTTP calls to `/api/v1/me`, no diagnostic noise on stderr, no measurable latency added).
- **SC-004**: Operators reading stderr/structured logs can determine within a single line whether direct ingress was skipped, whether rehydrate was attempted, and whether rehydrate failed locally vs. returned no private team.

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `StoredSession` | The on-disk auth session. Fields used by this mission: `teams` (list of teams with `is_private_teamspace` and id), `default_team_id`. |
| Private Teamspace | A team object where `is_private_teamspace=true`. The only valid target for direct sync ingress. |
| Strict private-team resolver | The single canonical helper that returns a Private Teamspace id or signals missing. The only entry point used by direct-ingress call sites. |
| Direct-ingress endpoints | `POST /api/v1/events/batch/` and `POST /api/v1/ws-token`. |
| Rehydrate endpoint | `GET /api/v1/me`. |

---

## Assumptions

1. The companion SaaS fix (`Priivacy-ai/spec-kitty-saas#142`) may not yet be deployed when this CLI change ships; the CLI must defend itself in either case.
2. `is_private_teamspace` is the authoritative field on a team payload from `/api/v1/me`; no heuristic guesses (slug pattern, role, etc.) substitute for that field.
3. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is the only supported way to enable sync side-effects on developer machines during this mission.
4. Existing test fixtures for auth/sync (`tests/auth/test_session.py`, `tests/sync/test_batch_sync.py`, `tests/sync/test_client_integration.py`) provide adequate scaffolding for the new tests; no large refactor of those fixtures is required.
5. Tracker provider reads and shared-team UI surfaces do not currently send writes to `/api/v1/events/batch/` or `/api/v1/ws-token`; if any are discovered during implementation, they fall under the constraint C-001 audit and must be triaged.
6. The auth refresh flow already has an authenticated HTTP layer that can call `/api/v1/me`; this mission reuses it rather than introducing a new client.

---

## Dependencies

- `src/specify_cli/auth/session.py` — strict resolver lives here.
- `src/specify_cli/auth/flows/refresh.py` — refresh flow rehydrate hook.
- `src/specify_cli/auth/http` (or equivalent) — authenticated `/api/v1/me` GET.
- `src/specify_cli/sync/batch.py`, `client.py`, `emitter.py`, `queue.py` — direct-ingress call sites.
- Strict-JSON contract for agent commands (existing).

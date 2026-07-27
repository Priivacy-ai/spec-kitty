# Data Model — Stability & Hygiene Hardening

**Mission**: `stability-and-hygiene-hardening-2026-04-01KQ4ARB`
**Date**: 2026-04-26

This document captures the entities and state machines this mission *touches*.
The mission introduces no new persistent entities; it tightens semantics on
existing ones.

## Mission

| Field | Type | Notes |
|-------|------|-------|
| `mission_id` | ULID (str, 26 chars) | Canonical identity; immutable |
| `mid8` | str (8 chars) | First 8 of `mission_id`; used in branch / worktree names |
| `mission_slug` | str (kebab-case) | Human handle |
| `mission_number` | int \| null | **Display-only**; null pre-merge; assigned at merge time |
| `friendly_name` | str | Display title |
| `mission_type` | str | e.g. `software-dev` |
| `target_branch` | str | Always set; never hardcoded `main` in code |
| `pr_bound` | bool | New optional field; default false; gates branch strategy (FR-033) |
| `created_at` | ISO 8601 str | Immutable |

Selector resolution order: `mission_id` → `mid8` → `mission_slug`. Ambiguous
handles raise `MISSION_AMBIGUOUS_SELECTOR`. No silent fallback.

## Work Package (WP)

The 9-lane state machine is unchanged; transitions are tightened.

```
planned -> claimed -> in_progress -> for_review -> in_review -> approved -> done
              |             |             |             |
              v             v             v             v
            blocked      blocked      blocked      blocked
              |             |             |             |
              v             v             v             v
          canceled      canceled      canceled      canceled
```

| Field | Type | Notes |
|-------|------|-------|
| `wp_id` | str (e.g. `WP01`) | Stable within a mission |
| `lane` | enum | One of 9 above |
| `execution_mode` | enum | `worktree` (default) \| `planning_artifact` (FR-015 new) |
| `depends_on` | list[str] | WP IDs this WP needs before it can start |
| `lane_assignment` | str \| null | e.g. `lane-a`; null for `planning_artifact` |
| `workspace_path` | path \| null | null for `planning_artifact` |

**Tightened transitions** (this mission):

- **`for_review -> in_review`** (NOT `for_review -> in_progress`) when a
  reviewer claims a WP (FR-016).
- **`planned -> in_progress`** event MUST be emitted before any worktree
  allocation that could fail (FR-014). On allocation failure, emit
  `in_progress -> blocked` with `reason="worktree_alloc_failed"`.

## Status Event (append-only)

Lives at `kitty-specs/<slug>/status.events.jsonl`. One JSON object per line,
sorted keys.

| Field | Required | Notes |
|-------|----------|-------|
| `event_id` | yes | ULID |
| `at` | yes | UTC ISO 8601 |
| `actor` | yes | e.g. `claude`, `human:rob` |
| `feature_slug` | yes | mission slug (legacy field name) |
| `wp_id` | yes | |
| `from_lane` | yes | |
| `to_lane` | yes | |
| `execution_mode` | yes | matches WP's `execution_mode` |
| `force` | yes (bool) | |
| `reason` | optional | free text |
| `evidence` | optional | dict |
| `review_ref` | optional | str |

Events are written via `emit_status_transition()` against the **canonical
mission repo** (FR-013). The resolver in `workspace/root_resolver.py` ensures
this even when the caller's CWD is a worktree.

## Mission Brief (intake artifact)

Stored at `.kittify/mission-brief.md` with sidecar provenance YAML at
`.kittify/brief-source.yaml`.

| Field | Required | Notes |
|-------|----------|-------|
| `source_file` | yes | Sanitized path; comment-escape rules (FR-007) |
| `source_sha256` | yes | hex digest of the brief content |
| `intake_root` | yes | Absolute path used for scanning; same as write root (FR-012) |
| `size_bytes` | yes | <= `intake.max_brief_bytes` (NFR-003) |
| `read_at` | yes | UTC ISO 8601 |

Writes are atomic via `safe_commit` (FR-010): write to `<target>.tmp` →
`fsync` → `os.replace`.

Provenance lines in any consumer of this brief MUST pass through
`intake.provenance.escape_for_comment()`.

## Charter Context

A render of `.kittify/charter/charter.md` scoped to one action. Two modes.

| Mode | When | Body | Section anchors | Directive IDs | Tactic IDs |
|------|------|------|-----------------|---------------|------------|
| `bootstrap` | First load per action | Full | All | All | All |
| `compact` | Subsequent loads per action | Collapsed | **All** (FR-034 fix) | **All** (FR-034 fix) | **All** (FR-034 fix) |

First-load tracking lives in `.kittify/charter/context-state.json`, keyed by
action.

## Sync Queue

Existing SQLite `OfflineQueue`; this mission tightens overflow and replay
semantics.

| Operation | Behavior (post-mission) |
|-----------|-------------------------|
| `append(event)` | Raises `OfflineQueueFull` if would exceed `sync.queue_max_events` (default 10_000) instead of silent drop (FR-027) |
| `replay()` | On `(tenant_id, project_id)` match: idempotent. Mismatch: structured `TenantMismatch` or `ProjectMismatch`, skip event, log conflict (FR-028) |
| `drain_to_file(path)` | New helper for FR-027 recovery path |

## Auth Transport

New module: `src/specify_cli/auth/transport.py`.

```text
AuthenticatedClient
  ├── token_store: TokenStore        # singleton per process
  ├── refresh_lock: RefreshLock       # mutex
  ├── _user_facing_failure_emitted: bool  # per-invocation dedup (FR-029)
  └── methods:
      get / post / put / delete / stream / websocket_connect
      → on 401: acquire refresh_lock, refresh once, retry
      → on refresh failure: raise AuthRefreshFailed; emit ≤1 user-facing line
```

State machine for token refresh:

```
fresh ─(401)──> refreshing ─(success)──> fresh
                  │
                  ├─(failure)──> failed ──(next 401)──> refreshing (with backoff)
                  │
                  └─(in-flight 401 from sibling)──> waits on lock, returns shared result
```

Architectural test asserts no caller in `sync/`, `tracker/`, or websocket
modules imports `httpx.Client` / `httpx.AsyncClient` directly (FR-030).

## Cross-Repo Package Contract

Two PyPI packages remain external, with frozen public surfaces:

- `spec_kitty_events.*` — see `contracts/events-envelope.md`.
- `spec_kitty_tracker.*` — see `contracts/tracker-public-imports.md`.

A *resolved-version* contract test reads `uv.lock` and asserts the test
fixtures match the resolved version's public schema. Bumping a package without
regenerating the snapshot fails the contract gate.

## Issue Traceability Matrix

`kitty-specs/<mission>/issue-matrix.md` (FR-037 / D1).

| Column | Type | Notes |
|--------|------|-------|
| repo | str | e.g. `Priivacy-ai/spec-kitty` |
| issue | int | GitHub issue number |
| theme | enum | merge / intake / runtime / packages / sync / governance / e2e |
| verdict | enum | `fixed` \| `verified-already-fixed` \| `deferred-with-followup` |
| wp_id | str | The WP that owns the verdict |
| evidence_ref | str | test name, commit SHA, doc anchor, or follow-up issue link |

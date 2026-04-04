---
title: Orchestrator API Reference
description: Contract reference for external orchestration providers that integrate with spec-kitty via the orchestrator-api command group.
---

# Orchestrator API Reference

`spec-kitty orchestrator-api` is the host-side contract for external orchestration
providers. It is the **only** supported interface for systems running outside the
project directory (CI pipelines, custom orchestrators, dashboards).

- External providers (for example `spec-kitty-orchestrator`) must use this API.
- Commands always emit JSON: exactly one JSON envelope on stdout; non-zero exit on failure.
- Parser/usage errors (missing required args, unknown options) also return a JSON envelope with error code `USAGE_ERROR`.
- Agents running **inside** the project use the host CLI (`spec-kitty next`, `spec-kitty agent tasks move-task`) instead.

---

## Contract Version

- `CONTRACT_VERSION`: `1.0.0`
- Command: `spec-kitty orchestrator-api contract-version`
- Always call `contract-version` at orchestrator startup, before any other commands.

---

## Canonical JSON Envelope

Every command returns a single JSON object:

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.<subcommand>",
  "timestamp": "2026-03-22T15:01:26.559052+00:00",
  "correlation_id": "corr-d05f72846fff4dfab587a4d0d87e5b58",
  "success": true,
  "error_code": null,
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `contract_version` | string | Host API contract version (`1.0.0`). |
| `command` | string | Fully qualified command name (`orchestrator-api.<subcommand>`). |
| `timestamp` | string | Host generation timestamp (ISO 8601 with timezone). |
| `correlation_id` | string | Unique request/response correlation token. Use for audit trails and log correlation. |
| `success` | bool | `true` on success, `false` on failure. |
| `error_code` | string or null | Machine-readable error identifier on failure, otherwise `null`. |
| `data` | object | Command-specific payload. |

**Rules:**
- `success=true` means `error_code` is always `null`.
- `success=false` means `error_code` is a machine-readable string. Exit code is 1 for operational errors, 2 for usage/parse errors.
- Use `error_code` as the stable failure discriminator. Do not parse human-readable messages for control flow.

---

## Lanes and Mapping

The orchestrator API exposes 8 canonical lanes:

| Lane | Terminal | Description |
|------|:--------:|-------------|
| `planned` | | Initial state, work not started |
| `claimed` | | Claimed by an actor, not yet started |
| `in_progress` | | Actively being worked |
| `for_review` | | Submitted for review |
| `approved` | | Approved by reviewer |
| `done` | Yes | Complete |
| `blocked` | | Blocked by external dependency |
| `canceled` | Yes | Canceled (force required to leave) |

The alias `doing` resolves to `in_progress` at input boundaries. It is never
persisted in events or returned in API responses.

---

## Command Summary

| # | Command | Purpose | Mutates State |
|---|---------|---------|:-------------:|
| 1 | [`contract-version`](#1-contract-version) | Verify API compatibility | No |
| 2 | [`feature-state`](#2-feature-state) | Query full feature state | No |
| 3 | [`list-ready`](#3-list-ready) | List WPs ready to start | No |
| 4 | [`start-implementation`](#4-start-implementation) | Claim + begin WP (atomic) | Yes |
| 5 | [`start-review`](#5-start-review) | Reviewer rollback (for_review to in_progress) | Yes |
| 6 | [`transition`](#6-transition) | Explicit single lane change | Yes |
| 7 | [`append-history`](#7-append-history) | Add note to WP activity log | Yes |
| 8 | [`accept-feature`](#8-accept-feature) | Mark feature as accepted | Yes |
| 9 | [`merge-feature`](#9-merge-feature) | Merge WP branches into target | Yes |

---

## 1. contract-version

Verify API contract compatibility between orchestrator and host CLI.

```
Usage: spec-kitty orchestrator-api contract-version [OPTIONS]

Options:
  --provider-version  TEXT  Caller's provider version; returns
                            CONTRACT_VERSION_MISMATCH if below minimum
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--provider-version` | TEXT | No | none | Orchestrator's contract version for compatibility check |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `api_version` | string | Current API contract version |
| `min_supported_provider_version` | string | Minimum provider version the host accepts |

**Example output:**

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.contract-version",
  "timestamp": "2026-03-22T15:01:26.559052+00:00",
  "correlation_id": "corr-d05f7284-6fff-4dfa-b587-a4d0d87e5b58",
  "success": true,
  "error_code": null,
  "data": {
    "api_version": "1.0.0",
    "min_supported_provider_version": "0.1.0"
  }
}
```

**Error codes:**

| Code | Cause |
|------|-------|
| `CONTRACT_VERSION_MISMATCH` | Provider version is below `min_supported_provider_version` |

**Usage notes:**
- Call at orchestrator startup, before any other commands.
- Do not cache across host CLI version changes.
- If the error fires, upgrade the orchestrator to match the host.

---

## 2. feature-state

Query the full state of a feature and all its work packages.

```
Usage: spec-kitty orchestrator-api feature-state [OPTIONS]

Options:
  --feature  TEXT  Feature slug (e.g. 034-my-feature) [required]
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug (e.g., `047-namespace-aware-artifact-body-sync`) |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `feature_slug` | string | The feature identifier |
| `summary.planned` | int | WPs in the `planned` lane |
| `summary.claimed` | int | WPs in the `claimed` lane |
| `summary.in_progress` | int | WPs in the `in_progress` lane |
| `summary.for_review` | int | WPs in the `for_review` lane |
| `summary.approved` | int | WPs in the `approved` lane |
| `summary.done` | int | WPs in the `done` lane |
| `summary.blocked` | int | WPs in the `blocked` lane |
| `summary.canceled` | int | WPs in the `canceled` lane |
| `work_packages` | list | Per-WP objects (see below) |
| `work_packages[].wp_id` | string | Work package identifier (e.g., `WP01`) |
| `work_packages[].lane` | string | Current lane |
| `work_packages[].dependencies` | list | List of WP IDs this WP depends on |
| `work_packages[].last_actor` | string or null | Last actor to modify this WP |

**Example output** (run against feature `047-namespace-aware-artifact-body-sync`):

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.feature-state",
  "timestamp": "2026-03-22T15:01:27.957292+00:00",
  "correlation_id": "corr-23ce339e-8b17-4b8b-a599-c3f9136a0e45",
  "success": true,
  "error_code": null,
  "data": {
    "feature_slug": "047-namespace-aware-artifact-body-sync",
    "summary": {
      "planned": 0,
      "claimed": 0,
      "in_progress": 0,
      "for_review": 0,
      "approved": 0,
      "done": 7,
      "blocked": 0,
      "canceled": 0
    },
    "work_packages": [
      {
        "wp_id": "WP01",
        "lane": "done",
        "dependencies": [],
        "last_actor": null
      },
      {
        "wp_id": "WP02",
        "lane": "done",
        "dependencies": ["WP01"],
        "last_actor": null
      },
      {
        "wp_id": "WP03",
        "lane": "done",
        "dependencies": ["WP01", "WP02"],
        "last_actor": null
      },
      {
        "wp_id": "WP04",
        "lane": "done",
        "dependencies": ["WP01"],
        "last_actor": null
      },
      {
        "wp_id": "WP05",
        "lane": "done",
        "dependencies": ["WP03", "WP01"],
        "last_actor": null
      },
      {
        "wp_id": "WP06",
        "lane": "done",
        "dependencies": ["WP02", "WP04"],
        "last_actor": null
      },
      {
        "wp_id": "WP07",
        "lane": "done",
        "dependencies": ["WP05", "WP06"],
        "last_actor": null
      }
    ]
  }
}
```

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists in `kitty-specs/` |

---

## 3. list-ready

List work packages that are ready to start (in `planned` lane with all
dependencies satisfied).

```
Usage: spec-kitty orchestrator-api list-ready [OPTIONS]

Options:
  --feature  TEXT  Feature slug [required]
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `feature_slug` | string | The feature identifier |
| `ready_work_packages` | list | WPs ready to start (see below) |
| `ready_work_packages[].wp_id` | string | Work package identifier |
| `ready_work_packages[].lane` | string | Current lane (always `planned` for returned WPs) |
| `ready_work_packages[].dependencies_satisfied` | bool | Always `true` for returned WPs |
| `ready_work_packages[].recommended_base` | string or null | WP ID to pass as `--base` to `spec-kitty implement` (e.g., `WP01`, not a branch name) |

**Example output** (feature with ready WPs):

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.list-ready",
  "timestamp": "2026-03-22T15:01:28.542408+00:00",
  "correlation_id": "corr-90d4382c-8880-4a3f-996d-ad2d1f1771e8",
  "success": true,
  "error_code": null,
  "data": {
    "feature_slug": "042-test-feature",
    "ready_work_packages": [
      {
        "wp_id": "WP03",
        "lane": "planned",
        "dependencies_satisfied": true,
        "recommended_base": "WP01"
      }
    ]
  }
}
```

An empty `ready_work_packages` list means all WPs are either in-progress,
in-review, done, or have unmet dependencies.

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists |

**Usage notes:**
- This is a query-only command; it does **not** modify any state.
- Safe to poll repeatedly from CI.

---

## 4. start-implementation

Claim a work package and begin implementation. This is a **composite transition**
that moves the WP through `planned` -> `claimed` -> `in_progress` atomically
(two events in one call).

```
Usage: spec-kitty orchestrator-api start-implementation [OPTIONS]

Options:
  --feature  TEXT  Feature slug [required]
  --wp       TEXT  Work package ID (e.g. WP01) [required]
  --actor    TEXT  Actor identity [required]
  --policy   TEXT  Policy metadata JSON (required)
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--wp` | TEXT | Yes | -- | Work package ID (e.g., `WP01`) |
| `--actor` | TEXT | Yes | -- | Identity of the claiming actor |
| `--policy` | TEXT | Yes | -- | JSON string with [policy metadata](#policy-metadata-schema) |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `workspace_path` | string | Computed worktree path. The caller must create the worktree. |
| `prompt_path` | string | Path to the WP task file to present to the agent. |
| `from_lane` | string | Lane the WP was in before the transition |
| `to_lane` | string | Lane the WP is now in (`in_progress`) |
| `policy_metadata_recorded` | bool | Whether policy metadata was recorded |
| `no_op` | bool | `true` if WP was already `in_progress` by the same actor (idempotent hit) |

**Idempotency behavior:**

| Current state | Same actor | Different actor |
|---|---|---|
| `planned` | Transitions to `in_progress` | Transitions to `in_progress` |
| `claimed` by this actor | Transitions to `in_progress` | `WP_ALREADY_CLAIMED` error |
| `in_progress` by this actor | `no_op=true`, success | `WP_ALREADY_CLAIMED` error |
| Other lane | `TRANSITION_REJECTED` | `TRANSITION_REJECTED` |

**Error codes:**

| Code | Cause |
|------|-------|
| `POLICY_METADATA_REQUIRED` | `--policy` missing or incomplete |
| `POLICY_VALIDATION_FAILED` | Bad JSON or contains secret-like values |
| `WP_ALREADY_CLAIMED` | Another actor has already claimed this WP |
| `TRANSITION_REJECTED` | Guard failure (dependency not met, invalid state) |
| `WP_NOT_FOUND` | WP ID does not exist in feature |

---

## 5. start-review

Reviewer rollback: transitions a WP from `for_review` back to `in_progress`
so the implementing agent can address review feedback.

```
Usage: spec-kitty orchestrator-api start-review [OPTIONS]

Options:
  --feature     TEXT  Feature slug [required]
  --wp          TEXT  Work package ID [required]
  --actor       TEXT  Actor identity [required]
  --policy      TEXT  Policy metadata JSON (required)
  --review-ref  TEXT  Review feedback reference (required)
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--wp` | TEXT | Yes | -- | Work package ID |
| `--actor` | TEXT | Yes | -- | Identity of the reviewing actor |
| `--policy` | TEXT | Yes | -- | JSON string with [policy metadata](#policy-metadata-schema) |
| `--review-ref` | TEXT | Yes | -- | Reference to review feedback (e.g., PR comment URL, review ID) |

`--review-ref` is the guard condition for the `for_review` -> `in_progress`
transition. It records what review feedback triggered the rollback.

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `from_lane` | string | Lane the WP was in before (typically `for_review`) |
| `to_lane` | string | Lane the WP is now in (`in_progress`) |
| `prompt_path` | string | Path to the WP task file |
| `policy_metadata_recorded` | bool | Whether policy metadata was recorded |

**Error codes:**

| Code | Cause |
|------|-------|
| `POLICY_METADATA_REQUIRED` | `--policy` missing or incomplete |
| `TRANSITION_REJECTED` | WP is not in `for_review` lane, or `--review-ref` missing |

---

## 6. transition

Perform an explicit single lane transition on a work package.

```
Usage: spec-kitty orchestrator-api transition [OPTIONS]

Options:
  --feature     TEXT  Feature slug [required]
  --wp          TEXT  Work package ID [required]
  --to          TEXT  Target lane [required]
  --actor       TEXT  Actor identity [required]
  --note        TEXT  Reason/note for the transition
  --policy      TEXT  Policy metadata JSON (required for run-affecting lanes)
  --force             Force the transition
  --review-ref  TEXT  Review reference
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--wp` | TEXT | Yes | -- | Work package ID |
| `--to` | TEXT | Yes | -- | Target lane |
| `--actor` | TEXT | Yes | -- | Identity of the transitioning actor |
| `--note` | TEXT | No | none | Audit note explaining the transition |
| `--policy` | TEXT | Conditional | none | JSON policy metadata (required for run-affecting lanes) |
| `--force` | FLAG | No | off | Override guard checks (recovery only) |
| `--review-ref` | TEXT | No | none | Review artifact reference |

**Valid target lanes and policy requirement:**

| Lane | Requires `--policy` | Description |
|------|:-------------------:|-------------|
| `planned` | No | Reset WP to planning state |
| `claimed` | Yes | Mark WP as claimed by an actor |
| `in_progress` | Yes | Mark WP as actively being worked |
| `for_review` | Yes | Submit WP for review |
| `approved` | No | Mark WP as approved |
| `done` | No | Mark WP as complete |
| `blocked` | No | Mark WP as blocked |
| `canceled` | No | Cancel the WP |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `from_lane` | string | Previous lane |
| `to_lane` | string | New lane |

**Error codes:**

| Code | Cause |
|------|-------|
| `TRANSITION_REJECTED` | Guard failure or invalid lane transition |
| `POLICY_METADATA_REQUIRED` | Run-affecting lane without `--policy` |
| `POLICY_VALIDATION_FAILED` | Bad JSON or contains secret-like values |
| `WP_NOT_FOUND` | WP ID does not exist in feature |

**Usage notes:**
- Use `--force` only for recovery from known-bad state, never in normal flow.
- Use `--note` to record reasoning in the audit trail.
- Use `--review-ref` when transitioning from `for_review` or `approved` back to `in_progress` or `planned` (review rollback guard).

---

## 7. append-history

Append a timestamped note to a work package's activity log. Does not change
the WP lane.

```
Usage: spec-kitty orchestrator-api append-history [OPTIONS]

Options:
  --feature  TEXT  Feature slug [required]
  --wp       TEXT  Work package ID [required]
  --actor    TEXT  Actor identity [required]
  --note     TEXT  History note to append [required]
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--wp` | TEXT | Yes | -- | Work package ID |
| `--actor` | TEXT | Yes | -- | Identity of the author |
| `--note` | TEXT | Yes | -- | History note content |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `history_entry_id` | string | Unique identifier for the history entry |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists |
| `WP_NOT_FOUND` | WP ID does not exist in feature |

---

## 8. accept-feature

Mark a feature as accepted. All work packages must be in the `done` lane.

```
Usage: spec-kitty orchestrator-api accept-feature [OPTIONS]

Options:
  --feature  TEXT  Feature slug [required]
  --actor    TEXT  Actor identity [required]
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--actor` | TEXT | Yes | -- | Identity of the accepting actor |

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `accepted` | bool | `true` if feature was accepted |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists |
| `FEATURE_NOT_READY` | One or more WPs are not in the `done` lane |

**Usage notes:**
- Always call `feature-state` first to verify all WPs are done.
- This is a guard-protected operation; it rejects if any WP is not done.

---

## 9. merge-feature

Run preflight checks then merge all WP branches into the target branch in
dependency order.

```
Usage: spec-kitty orchestrator-api merge-feature [OPTIONS]

Options:
  --feature   TEXT  Feature slug [required]
  --target    TEXT  Target branch to merge into (auto-detected from meta.json)
  --strategy  TEXT  Merge strategy: merge, squash, or rebase [default: merge]
  --push           Push target branch after merge
```

**Flags:**

| Flag | Type | Required | Default | Description |
|------|------|:--------:|---------|-------------|
| `--feature` | TEXT | Yes | -- | Feature slug |
| `--target` | TEXT | No | auto-detected from `meta.json` | Target branch to merge into |
| `--strategy` | TEXT | No | `merge` | Merge strategy: `merge` (--no-ff), `squash`, or `rebase` |
| `--push` | FLAG | No | off | Push target branch to remote after merge |

**Preflight checks (4 steps):**

1. All expected WPs have worktrees (based on tasks in `kitty-specs/`)
2. All worktrees are clean (no uncommitted changes)
3. Target branch is not behind origin
4. Missing WPs in done lane are handled (skipped with warnings)

On preflight failure, returns `PREFLIGHT_FAILED` with a detailed error list.

**Response `data` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `merged` | bool | Whether the merge completed successfully |
| `merged_wps` | list | Work package IDs that were merged |
| `target_branch` | string | Branch merged into |
| `strategy` | string | Merge strategy that was used |
| `worktree_removed` | bool | Whether worktrees were cleaned up |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists |
| `PREFLIGHT_FAILED` | Worktree dirty, target diverged, or missing WPs |
| `MERGE_FAILED` | Git merge failed (conflicts or other git error) |
| `PUSH_FAILED` | Push to remote failed |
| `UNSUPPORTED_STRATEGY` | Strategy not in `{merge, squash, rebase}` |

**Usage notes:**
- Feature should be accepted before merging.
- The WP merge order respects the dependency graph.
- Use `--push` only when the orchestrator has confirmed the merge result.

---

## Policy Metadata Schema

Transitions to run-affecting lanes (`claimed`, `in_progress`, `for_review`)
require `--policy` with a JSON object. Policy metadata is recorded in the
append-only event log for every run-affecting transition, enabling post-incident
review of exactly what orchestrator drove each state change.

### Required Fields (7)

```json
{
  "orchestrator_id": "my-ci-bot",
  "orchestrator_version": "1.0.0",
  "agent_family": "claude",
  "approval_mode": "manual",
  "sandbox_mode": "container",
  "network_mode": "restricted",
  "dangerous_flags": []
}
```

| Field | Type | Description | Example values |
|-------|------|-------------|----------------|
| `orchestrator_id` | string | Unique identifier for the orchestrator driving the workflow | `"my-ci-bot"`, `"github-actions-orch"` |
| `orchestrator_version` | string | Semver version of the orchestrator | `"1.0.0"`, `"0.3.2"` |
| `agent_family` | string | Agent type being orchestrated | `"claude"`, `"codex"`, `"gemini"`, `"cursor"` |
| `approval_mode` | string | How transitions are approved | `"manual"`, `"auto"`, `"supervised"` |
| `sandbox_mode` | string | Execution environment isolation | `"container"`, `"none"`, `"vm"` |
| `network_mode` | string | Network access the agent has | `"restricted"`, `"full"`, `"none"` |
| `dangerous_flags` | array | Dangerous flags the agent has enabled | `[]`, `["--dangerously-skip-permissions"]` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `tool_restrictions` | string or null | Tools the agent is permitted to use |

### Validation Rules

- All 7 required fields must be present. Missing fields return `POLICY_VALIDATION_FAILED`.
- `dangerous_flags` must be an array. A non-array value fails validation.
- Field values must not contain secret-like patterns: `token`, `secret`, `key`, `password`, `credential`. Values matching these patterns are rejected with `POLICY_VALIDATION_FAILED`.
- Invalid JSON (syntax errors) returns `POLICY_VALIDATION_FAILED`.

### Policy Purpose

Policy metadata serves three functions:

1. **Identity** -- `orchestrator_id` and `orchestrator_version` identify WHO is driving the workflow, enabling audit and blame tracking.
2. **Safety** -- `sandbox_mode`, `network_mode`, `dangerous_flags`, and `tool_restrictions` declare the execution environment. The host can enforce safety invariants or refuse transitions that violate project policy.
3. **Auditability** -- Policy is recorded in the WP history alongside every run-affecting transition. Post-incident review can reconstruct exactly what orchestrator, with what permissions, drove each state change.

---

## Error Code Catalog

Complete list of all error codes returned by orchestrator-api commands.

| Error Code | Commands | Cause |
|------------|----------|-------|
| `USAGE_ERROR` | All | Parser/usage error (missing required args, unknown options) |
| `CONTRACT_VERSION_MISMATCH` | `contract-version` | Provider version below `min_supported_provider_version` |
| `FEATURE_NOT_FOUND` | `feature-state`, `list-ready`, `append-history`, `accept-feature`, `merge-feature` | Feature slug does not resolve to a directory in `kitty-specs/` |
| `WP_NOT_FOUND` | `start-implementation`, `start-review`, `transition`, `append-history` | WP ID does not exist in the feature |
| `TRANSITION_REJECTED` | `start-implementation`, `start-review`, `transition` | Invalid lane transition or guard failure (dependency not met, invalid state) |
| `WP_ALREADY_CLAIMED` | `start-implementation` | Another actor has already claimed the WP |
| `POLICY_METADATA_REQUIRED` | `start-implementation`, `start-review`, `transition` | Policy missing on run-affecting lane (`claimed`, `in_progress`, `for_review`) |
| `POLICY_VALIDATION_FAILED` | `start-implementation`, `start-review`, `transition` | Invalid JSON, missing required fields, non-array `dangerous_flags`, or secret-like values detected |
| `FEATURE_NOT_READY` | `accept-feature` | Not all WPs are in the `done` lane |
| `PREFLIGHT_FAILED` | `merge-feature` | Dirty worktrees, diverged target branch, or missing WP worktrees |
| `MERGE_FAILED` | `merge-feature` | Git merge failed (conflicts or other git error) |
| `PUSH_FAILED` | `merge-feature` | Push to remote failed after merge |
| `UNSUPPORTED_STRATEGY` | `merge-feature` | Merge strategy not in `{merge, squash, rebase}` |

**Handling errors programmatically:**

```python
import json, subprocess

result = subprocess.run(
    ["spec-kitty", "orchestrator-api", "feature-state", "--feature", slug],
    capture_output=True, text=True,
)
envelope = json.loads(result.stdout)

if not envelope["success"]:
    match envelope["error_code"]:
        case "FEATURE_NOT_FOUND":
            handle_missing_feature(slug)
        case _:
            raise RuntimeError(f"Unexpected error: {envelope['error_code']}")
```

---

## Host Boundary Rules

The orchestrator-api is the **only** supported interface for external systems.
Agents running inside the project use the host CLI instead. These two interfaces
are not interchangeable.

### Who Uses What

| Interface | Audience | Entry Point |
|-----------|----------|-------------|
| **Host CLI** | Agents running inside the project (Claude Code, Codex, etc.) | `spec-kitty next`, `spec-kitty agent tasks move-task`, slash commands |
| **Orchestrator API** | External systems (CI pipelines, custom orchestrators, dashboards) | `spec-kitty orchestrator-api <subcommand>` |

### Decision Matrix

| Scenario | Interface | Reason |
|----------|-----------|--------|
| Agent implements a WP it was assigned | Host CLI | Agent is inside the project |
| CI pipeline starts implementation for an agent | Orchestrator API | CI is external |
| Agent moves its own WP to for_review | Host CLI | Agent is inside the project |
| Dashboard moves a WP to approved | Orchestrator API | Dashboard is external |
| Agent queries its next step | Host CLI (`spec-kitty next`) | Agent is inside the project |
| Supervisor queries ready WPs | Orchestrator API (`list-ready`) | Supervisor is external |
| External tool reads WP state | Orchestrator API (`feature-state`) | External tool must use API |
| CI accepts a feature after all checks pass | Orchestrator API (`accept-feature`) | CI is external |

### Anti-Patterns (Do NOT Do)

**1. Edit frontmatter directly**

```yaml
# WRONG: kitty-specs/017-feature/tasks/WP01-setup.md
---
lane: in_progress  # Do not write this directly!
---
```

Skips guard validation, policy recording, history logging, and lane transition
hooks. Use `orchestrator-api transition --to in_progress` instead.

**2. Call internal CLI commands from external systems**

```bash
# WRONG
spec-kitty agent tasks move-task WP01 --to for_review
```

Internal commands do not enforce policy metadata and do not emit the JSON
contract envelope. Use `orchestrator-api transition` instead.

**3. Create worktrees manually**

```bash
# WRONG
git worktree add .worktrees/017-feature-lane-a -b 017-feature-lane-a
```

Manual worktree creation skips state transitions, policy recording, claim
tracking, and canonical workspace resolution. Use `orchestrator-api start-implementation`
first, then create or attach the worktree at the returned `workspace_path`.

**4. Poll by reading files**

```bash
# WRONG
grep "lane:" kitty-specs/017-feature/tasks/WP01-setup.md
```

File content may be stale, partially written, or in a format that changes
between versions. Use `orchestrator-api feature-state` or `list-ready`.

**5. Skip contract-version check**

Always call `contract-version` at orchestrator startup. If the host CLI has been
upgraded and the contract version changed, command semantics may differ.

**6. Skip --policy on run-affecting transitions**

Run-affecting lanes (`claimed`, `in_progress`, `for_review`) require policy
metadata. Omitting `--policy` returns `POLICY_METADATA_REQUIRED`.

---

## Integration Pattern

A typical external orchestrator loop:

```bash
# 1. Verify contract
spec-kitty orchestrator-api contract-version --provider-version "1.0.0"

# 2. Query ready WPs
spec-kitty orchestrator-api list-ready --feature 017-my-feature

# 3. Start implementation for each ready WP
spec-kitty orchestrator-api start-implementation \
  --feature 017-my-feature --wp WP01 --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch","orchestrator_version":"1.0.0","agent_family":"claude","approval_mode":"auto","sandbox_mode":"container","network_mode":"restricted","dangerous_flags":[]}'

# 4. (Agent executes the prompt_path in the worktree the orchestrator created)

# 5. Record history
spec-kitty orchestrator-api append-history \
  --feature 017-my-feature --wp WP01 --actor "ci-bot" \
  --note "Implementation complete"

# 6. Transition to review
spec-kitty orchestrator-api transition \
  --feature 017-my-feature --wp WP01 --to for_review --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch","orchestrator_version":"1.0.0","agent_family":"claude","approval_mode":"auto","sandbox_mode":"container","network_mode":"restricted","dangerous_flags":[]}'

# 7. (Reviewer reviews the work)

# 8. Transition to done
spec-kitty orchestrator-api transition \
  --feature 017-my-feature --wp WP01 --to done --actor "reviewer-bot" \
  --force --note "Approved in PR #42"

# 9. When all WPs are done, accept and merge
spec-kitty orchestrator-api accept-feature \
  --feature 017-my-feature --actor "ci-bot"
spec-kitty orchestrator-api merge-feature \
  --feature 017-my-feature --strategy squash --push
```

---

## See Also

- [How to Run the External Orchestrator](../how-to/run-external-orchestrator.md)
- [How to Build a Custom Orchestrator](../how-to/build-custom-orchestrator.md)
- [Event Envelope Reference](event-envelope.md)

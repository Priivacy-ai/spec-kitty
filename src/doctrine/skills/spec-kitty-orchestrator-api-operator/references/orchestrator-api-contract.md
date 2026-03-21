# Orchestrator API Contract Reference

Complete CLI reference for `spec-kitty orchestrator-api` subcommands.

Every command returns a canonical JSON envelope:

```json
{
  "contract_version": "1.0.0",
  "command": "orchestrator-api.<subcommand-name>",
  "timestamp": "2026-03-21T08:00:00Z",
  "correlation_id": "uuid-v4",
  "success": true,
  "error_code": null,
  "data": { ... }
}
```

On failure, `success` is `false` and `error_code` contains a machine-readable
code. The `data` field may contain diagnostic details.

---

## 1. contract-version

Verify API contract compatibility between orchestrator and host CLI.

```bash
spec-kitty orchestrator-api contract-version [--provider-version TEXT]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--provider-version` | TEXT | none | Orchestrator's contract version for compatibility check |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `api_version` | string | Current API contract version |
| `min_supported_provider_version` | string | Minimum provider version the host accepts |

**Error codes:**

| Code | Cause |
|------|-------|
| `CONTRACT_VERSION_MISMATCH` | Provider version is below `min_supported_provider_version` |

**Usage notes:**

- Call at orchestrator startup, before any other commands
- Do not cache across host CLI version changes
- If the error fires, upgrade the orchestrator to match the host

---

## 2. feature-state

Query the full state of a feature and all its work packages.

```bash
spec-kitty orchestrator-api feature-state --feature TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug (e.g., `017-my-feature`) |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `summary.done_count` | int | WPs in the `done` lane |
| `summary.for_review_count` | int | WPs in the `for_review` lane |
| `summary.in_progress_count` | int | WPs in the `in_progress` lane |
| `summary.planned_count` | int | WPs in the `planned` lane |
| `summary.total_wps` | int | Total number of work packages |
| `work_packages` | list | Per-WP objects with `wp_id`, `lane`, `dependencies`, `last_actor` |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists in `kitty-specs/` |

---

## 3. list-ready

List work packages that are ready to start (dependencies satisfied, in
`planned` lane).

```bash
spec-kitty orchestrator-api list-ready --feature TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ready_work_packages` | list | Objects with fields below |
| `ready_work_packages[].wp_id` | string | Work package identifier (e.g., `WP01`) |
| `ready_work_packages[].lane` | string | Current lane (always `planned` for ready WPs) |
| `ready_work_packages[].dependencies_satisfied` | bool | Always `true` for returned WPs |
| `ready_work_packages[].recommended_base` | string or null | Recommended `--base` value for `implement` |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_FOUND` | No feature with this slug exists |

**Usage notes:**

- This is a query-only command; it does NOT modify any state
- Safe to poll repeatedly from CI
- An empty `ready_work_packages` list means all WPs are either in-progress, in-review, or done

---

## 4. start-implementation

Claim a work package and begin implementation. This is a composite transition
that moves the WP through planned -> claimed -> in_progress atomically.

```bash
spec-kitty orchestrator-api start-implementation \
  --feature TEXT --wp TEXT --actor TEXT --policy TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--wp` | TEXT | required | Work package ID (e.g., `WP01`) |
| `--actor` | TEXT | required | Identity of the claiming actor |
| `--policy` | TEXT | required | JSON string with policy metadata (see below) |

**Policy JSON fields (all required):**

| Field | Type | Description |
|-------|------|-------------|
| `orchestrator_id` | string | Unique identifier for this orchestrator |
| `orchestrator_version` | string | Version of the orchestrator |
| `agent_family` | string | Agent type: `claude`, `codex`, `gemini`, etc. |
| `approval_mode` | string | `manual`, `auto`, or `supervised` |
| `sandbox_mode` | string | `container`, `none`, `vm`, etc. |
| `network_mode` | string | `restricted`, `full`, `none` |
| `dangerous_flags` | list | Any dangerous flags the agent has enabled |
| `tool_restrictions` | string or null | optional | Tools the agent is permitted to use |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `workspace_path` | string | Computed worktree path (the caller is responsible for creating the worktree) |
| `prompt_path` | string | Path to the WP task file (the caller is responsible for presenting it to the agent) |
| `from_lane` | string | Lane the WP was in before (`planned`, `claimed`, or `in_progress` for idempotent calls) |
| `to_lane` | string | Lane the WP is now in (`in_progress`) |
| `policy_metadata_recorded` | bool | Whether policy metadata was recorded |
| `no_op` | bool | `true` if WP was already `in_progress` by the same actor (idempotent hit) |

**Error codes:**

| Code | Cause |
|------|-------|
| `POLICY_METADATA_REQUIRED` | `--policy` missing or incomplete |
| `WP_ALREADY_CLAIMED` | Another actor has already claimed this WP |
| `TRANSITION_REJECTED` | Guard failure (dependency not met, invalid state) |

---

## 5. start-review

Reviewer rollback: transitions a WP from `for_review` back to `in_progress` so the
implementing agent can address review feedback. Requires `--review-ref` to link
the review feedback that triggered the rollback.

```bash
spec-kitty orchestrator-api start-review \
  --feature TEXT --wp TEXT --actor TEXT --review-ref TEXT --policy TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--wp` | TEXT | required | Work package ID |
| `--actor` | TEXT | required | Identity of the reviewing actor |
| `--review-ref` | TEXT | required | Reference to review feedback (PR comment URL, review ID) |
| `--policy` | TEXT | required | JSON string with policy metadata |

**Data fields:**

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

Perform an explicit lane transition on a work package.

```bash
spec-kitty orchestrator-api transition \
  --feature TEXT --wp TEXT --to TEXT --actor TEXT \
  [--note TEXT] [--policy TEXT] [--force] [--review-ref TEXT]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--wp` | TEXT | required | Work package ID |
| `--to` | TEXT | required | Target lane |
| `--actor` | TEXT | required | Identity of the transitioning actor |
| `--note` | TEXT | none | Audit note explaining the transition |
| `--policy` | TEXT | none | JSON policy metadata (required for run-affecting lanes) |
| `--force` | FLAG | off | Override guard checks (recovery only) |
| `--review-ref` | TEXT | none | Review artifact reference |

**Valid target lanes:**

| Lane | Requires `--policy` | Description |
|------|---------------------|-------------|
| `planned` | no | Reset WP to planning state |
| `claimed` | yes | Mark WP as claimed by an actor |
| `in_progress` | yes | Mark WP as actively being worked |
| `for_review` | yes | Submit WP for review |
| `approved` | no | Mark WP as approved |
| `done` | no | Mark WP as complete |
| `blocked` | no | Mark WP as blocked |
| `canceled` | no | Cancel the WP |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `from_lane` | string | Previous lane |
| `to_lane` | string | New lane |

**Error codes:**

| Code | Cause |
|------|-------|
| `TRANSITION_REJECTED` | Guard failure or invalid lane transition |
| `POLICY_METADATA_REQUIRED` | Run-affecting lane without `--policy` |

**Usage notes:**

- Use `--force` only for recovery from known-bad state, never in normal flow
- Use `--note` to record reasoning for audit trail
- Use `--review-ref` when transitioning from `for_review` or `approved` back to `in_progress` or `planned` (review rollback guard)

---

## 7. append-history

Append a timestamped note to a work package's history log.

```bash
spec-kitty orchestrator-api append-history \
  --feature TEXT --wp TEXT --actor TEXT --note TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--wp` | TEXT | required | Work package ID |
| `--actor` | TEXT | required | Identity of the author |
| `--note` | TEXT | required | History note content |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `history_entry_id` | string | Unique identifier for the history entry |

---

## 8. accept-feature

Mark a feature as accepted. All work packages must be in the `done` lane.

```bash
spec-kitty orchestrator-api accept-feature --feature TEXT --actor TEXT
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--actor` | TEXT | required | Identity of the accepting actor |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `accepted` | bool | True if feature was accepted |

**Error codes:**

| Code | Cause |
|------|-------|
| `FEATURE_NOT_READY` | One or more WPs are not in the `done` lane |

**Usage notes:**

- Always call `feature-state` first to verify all WPs are done
- This is a guard-protected operation; it will reject if any WP is not done

---

## 9. merge-feature

Merge all work packages for a feature into the target branch.

```bash
spec-kitty orchestrator-api merge-feature \
  --feature TEXT [--target TEXT] [--strategy merge|squash|rebase] [--push]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--feature` | TEXT | required | Feature slug |
| `--target` | TEXT | auto-detected from `meta.json` | Target branch to merge into |
| `--strategy` | TEXT | `merge` | Merge strategy: `merge`, `squash`, or `rebase` |
| `--push` | FLAG | off | Push to remote after merge |

**Data fields:**

| Field | Type | Description |
|-------|------|-------------|
| `merged` | bool | Whether the merge completed successfully |
| `merged_wps` | list | Work package IDs that were merged |
| `target_branch` | string | Branch merged into |
| `strategy` | string | Merge strategy that was used |
| `worktree_removed` | bool | Whether worktrees were cleaned up |

**Usage notes:**

- Feature should be accepted before merging
- The WP merge order respects the dependency graph
- Use `--push` only when the orchestrator has confirmed the merge result

---

## Error Code Summary

| Error Code | Commands | Description |
|------------|----------|-------------|
| `CONTRACT_VERSION_MISMATCH` | contract-version | Provider version too old |
| `FEATURE_NOT_FOUND` | feature-state, list-ready | Unknown feature slug |
| `FEATURE_NOT_READY` | accept-feature | Not all WPs are done |
| `POLICY_METADATA_REQUIRED` | start-implementation, start-review, transition | Missing or incomplete policy JSON |
| `TRANSITION_REJECTED` | start-implementation, start-review, transition | Guard failure or invalid transition |
| `WP_ALREADY_CLAIMED` | start-implementation, start-review | Another actor owns the WP |

---

## Orchestrator Integration Pattern

A typical external orchestrator loop:

```bash
# 1. Verify contract
spec-kitty orchestrator-api contract-version --provider-version "1.0.0"

# 2. Query ready WPs
spec-kitty orchestrator-api list-ready --feature 017-my-feature

# 3. Start implementation for each ready WP
spec-kitty orchestrator-api start-implementation \
  --feature 017-my-feature --wp WP01 --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch",...}'

# 4. (Agent executes the prompt_file in the worktree the orchestrator created)

# 5. Record history
spec-kitty orchestrator-api append-history \
  --feature 017-my-feature --wp WP01 --actor "ci-bot" --note "Implementation complete"

# 6. Transition to review
spec-kitty orchestrator-api transition \
  --feature 017-my-feature --wp WP01 --to for_review --actor "ci-bot" \
  --policy '{"orchestrator_id":"my-orch",...}'

# 7. (Reviewer reviews the work)

# 8. Transition to done (requires --force because the transition command
#    does not accept reviewer evidence payloads)
spec-kitty orchestrator-api transition \
  --feature 017-my-feature --wp WP01 --to done --actor "reviewer-bot" \
  --force --note "Approved in PR #42"

# 9. When all WPs are done, accept and merge
spec-kitty orchestrator-api accept-feature --feature 017-my-feature --actor "ci-bot"
spec-kitty orchestrator-api merge-feature --feature 017-my-feature --strategy squash --push
```

# Data Model: Feature Status State Model Remediation

**Feature**: 034-feature-status-state-model-remediation
**Date**: 2026-02-08

## Entities

### Lane (Enum)

Canonical 7-lane state machine for work package lifecycle.

| Value | Description | Terminal |
|-------|-------------|----------|
| `planned` | WP defined, not yet claimed | No |
| `claimed` | WP assigned to an actor, not yet started | No |
| `in_progress` | Active implementation underway | No |
| `for_review` | Implementation complete, awaiting review | No |
| `done` | Reviewed and accepted | Yes (unless forced) |
| `blocked` | Blocked by external dependency or issue | No |
| `canceled` | Permanently abandoned | Yes |

**Aliases**:
- `doing` → `in_progress` (accepted at input boundaries, never persisted)

### StatusEvent

Immutable record of a single lane transition. One JSON object per line in `status.events.jsonl`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string (ULID, 26 chars) | Always | Globally unique, lexicographically sortable |
| `feature_slug` | string | Always | Feature identifier (e.g., `034-feature-name`) |
| `wp_id` | string | Always | Work package ID (e.g., `WP01`) |
| `from_lane` | Lane | Always | Lane before transition |
| `to_lane` | Lane | Always | Lane after transition |
| `at` | string (ISO 8601 UTC) | Always | Timestamp of transition |
| `actor` | string | Always | Who initiated the transition (agent name, user ID) |
| `force` | boolean | Always | Whether transition was forced (bypassing guards) |
| `reason` | string | When force=true | Justification for forced transition |
| `execution_mode` | `"worktree"` \| `"direct_repo"` | Always | How the WP is being implemented |
| `review_ref` | string | When `for_review → in_progress` | Reference to review feedback (PR comment, review ID) |
| `evidence` | DoneEvidence | When `to_lane = done` (unless forced) | Completion evidence |

**Validation rules**:
- `event_id` must be valid ULID (26 chars, Crockford base32)
- `from_lane` and `to_lane` must be canonical Lane values (never aliases)
- `(from_lane, to_lane)` must be in `ALLOWED_TRANSITIONS` unless `force=true`
- `at` must be valid ISO 8601 UTC timestamp
- `reason` required when `force=true`
- `review_ref` required when transition is `for_review → in_progress`
- `evidence` required when `to_lane = done` unless `force=true`

### DoneEvidence

Structured completion evidence required for `done` transitions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repos` | list[RepoEvidence] | Optional | Implementation repositories |
| `verification` | list[VerificationResult] | Optional | Test/verification results |
| `review` | ReviewApproval | Always | Reviewer identity and verdict |

#### RepoEvidence

| Field | Type | Description |
|-------|------|-------------|
| `repo` | string | Repository name or path |
| `branch` | string | Branch name |
| `commit` | string | Commit SHA |
| `files_touched` | list[string] | Optional list of changed files |

#### VerificationResult

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | Verification command run (e.g., `pytest tests/`) |
| `result` | `"pass"` \| `"fail"` \| `"skip"` | Outcome |
| `summary` | string | Human-readable summary |

#### ReviewApproval

| Field | Type | Description |
|-------|------|-------------|
| `reviewer` | string | Reviewer identity |
| `verdict` | `"approved"` \| `"changes_requested"` | Review outcome |
| `reference` | string | PR URL, review comment ID, or similar |

### StatusSnapshot

Materialized current state of all WPs in a feature. Stored as `status.json`.

```json
{
  "feature_slug": "034-feature-status-state-model-remediation",
  "materialized_at": "2026-02-08T12:00:00Z",
  "event_count": 15,
  "last_event_id": "01HXYZ...",
  "work_packages": {
    "WP01": {
      "lane": "in_progress",
      "actor": "claude",
      "last_transition_at": "2026-02-08T11:30:00Z",
      "last_event_id": "01HXYW...",
      "force_count": 0
    },
    "WP02": {
      "lane": "planned",
      "actor": null,
      "last_transition_at": "2026-02-08T10:00:00Z",
      "last_event_id": "01HXYV...",
      "force_count": 0
    }
  },
  "summary": {
    "planned": 1,
    "claimed": 0,
    "in_progress": 1,
    "for_review": 0,
    "done": 0,
    "blocked": 0,
    "canceled": 0
  }
}
```

**Determinism contract**: Given the same event log, `json.dumps(snapshot, sort_keys=True, indent=2, ensure_ascii=False) + "\n"` always produces identical bytes.

## Transition Matrix

### Allowed Transitions (Default)

```
planned ──→ claimed
claimed ──→ in_progress
in_progress ──→ for_review
for_review ──→ done
for_review ──→ in_progress  (changes requested)
in_progress ──→ planned     (abandon/reassign)
any* ──→ blocked            (*except done, canceled)
blocked ──→ in_progress
any** ──→ canceled           (**except done)
```

### Guard Conditions

| Transition | Guard | Error if Violated |
|------------|-------|-------------------|
| `planned → claimed` | `actor` must be set, no conflicting active claim for this WP | "WP already claimed by {actor}" |
| `claimed → in_progress` | Active workspace context established (worktree exists or direct_repo mode) | "No workspace context for {wp_id}" |
| `in_progress → for_review` | All required subtasks complete OR `force=true` with reason; implementation evidence present | "Unchecked subtasks: {list}" |
| `for_review → done` | Reviewer identity + approval evidence in `evidence.review` | "Missing review approval evidence" |
| `for_review → in_progress` | `review_ref` must be provided | "Missing review feedback reference" |
| Any forced transition | `actor` and `reason` must be provided | "Force transitions require actor and reason" |

### Force Override

- Any transition can be forced with `force=true` + `actor` + `reason`
- Forced transitions from `done` (terminal state) require explicit acknowledgment
- All force events are recorded with full audit trail in the event log
- `status validate` reports force usage statistics

## State Diagrams

### Normal Lifecycle

```
planned → claimed → in_progress → for_review → done
                                       ↓
                                  in_progress  (changes requested, loops back)
```

### Blocking

```
any* → blocked → in_progress
(*except done, canceled)
```

### Cancellation

```
any** → canceled
(**except done — done is terminal)
```

### Force Override

```
done → any  (force only, requires actor + reason)
```

## File Layout (per feature)

```
kitty-specs/<feature>/
├── status.events.jsonl    # Canonical: append-only event log
├── status.json            # Derived: materialized snapshot (regenerable)
├── meta.json              # Feature metadata (includes status_phase override)
├── tasks/
│   ├── WP01.md            # Derived: frontmatter lane is compatibility view
│   ├── WP02.md
│   └── ...
└── tasks.md               # Derived: status sections regenerated from snapshot
```

**Authority hierarchy**:
1. `status.events.jsonl` — canonical truth (append-only)
2. `status.json` — derived snapshot (regenerable via `status materialize`)
3. WP frontmatter `lane` — compatibility view (regenerable via legacy bridge)
4. `tasks.md` status sections — human view (regenerable)

## Phase Configuration

### Config Schema Addition

```yaml
# .kittify/config.yaml
status:
  phase: 1  # 0, 1, or 2
```

### meta.json Schema Addition

```json
{
  "status_phase": 2
}
```

### Resolution Logic

```python
def resolve_phase(repo_root: Path, feature_slug: str) -> tuple[int, str]:
    """Returns (phase_number, source_description)."""
    # 1. Check per-feature override
    meta = load_meta(repo_root, feature_slug)
    if meta and "status_phase" in meta:
        return (meta["status_phase"], f"meta.json override for {feature_slug}")

    # 2. Check global config
    config = load_config(repo_root)
    if config and "status" in config and "phase" in config["status"]:
        return (config["status"]["phase"], "global default from .kittify/config.yaml")

    # 3. Built-in default
    return (1, "built-in default (Phase 1: dual-write)")
```

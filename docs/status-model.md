# Status Model: Operator Documentation

**Feature**: 034-feature-status-state-model-remediation
**Since**: 2.x (3.0 cleanup: feature 060)

**Terminology note**
- Canonical 2.x model: `Mission Type -> Mission -> Mission Run`
- Status commands now use `--mission` as the canonical tracked-mission selector. Legacy `--feature` remains a hidden deprecated alias for compatibility only.
- As of mission `083-mission-id-canonical-identity-migration`, a mission's canonical machine identity is `mission_id` (a ULID). The `--mission` flag accepts `mission_id`, `mid8` (first 8 chars of the ULID), or `mission_slug`. The numeric prefix in slug examples below (e.g. `034-feature-name`) is display-only metadata — the event log's aggregate key is `mission_id`, not the prefix. See the [mission identity migration runbook](migration/mission-id-canonical-identity.md).

## Overview

The status model uses a single canonical append-only event log per mission as the sole authority for work package status. Every lane transition is an immutable `StatusEvent` in `status.events.jsonl`. A deterministic reducer produces `status.json` snapshots.

**Key principles (3.0)**:
- `status.events.jsonl` is the **sole source of truth** for WP lane state
- `status.json` is a **derived** materialized snapshot (regenerable)
- WP frontmatter is for **static definition only** (title, dependencies, subtasks) -- the `lane` field is no longer written or read by active runtime code
- `finalize-tasks` is the **canonical bootstrap point** -- it creates initial WP definitions; status transitions are tracked exclusively in the event log
- Frontmatter `lane` is a **historical/migration-only** concept retained in migration code paths for backward compatibility

**3.1.0 addition**: Read-only status commands (including `materialize()` and `spec-kitty agent status materialize`) no longer dirty the git working tree. `status.json` is only written when there is a new event to materialize. The `materialized_at` field in `status.json` reflects the timestamp of the last event in the log, not the wall clock at the time the command was run.

## CLI Commands

All status commands live under `spec-kitty agent status`.

### `spec-kitty agent status emit`

Record a lane transition event for a work package.

```bash
# Move WP01 to claimed (assigns to an actor)
spec-kitty agent status emit WP01 --to claimed --actor claude

# Move WP01 to in_progress (begin implementation)
spec-kitty agent status emit WP01 --to in_progress --actor claude

# "doing" is accepted as an alias for "in_progress"
spec-kitty agent status emit WP01 --to doing --actor claude

# Move to for_review (submit for review)
spec-kitty agent status emit WP01 --to for_review --actor claude

# Move to done with reviewer evidence (required unless forced)
spec-kitty agent status emit WP01 --to done --actor claude \
  --evidence-json '{"review": {"reviewer": "alice", "verdict": "approved", "reference": "PR#42"}}'

# Return from review to in_progress (changes requested -- requires review_ref)
spec-kitty agent status emit WP01 --to in_progress --actor reviewer \
  --review-ref "PR#42-comment-7"

# Force a transition that bypasses guard conditions (requires actor + reason)
spec-kitty agent status emit WP01 --to in_progress --actor admin \
  --force --reason "Reopening after incorrectly marked done"

# Block a work package
spec-kitty agent status emit WP01 --to blocked --actor claude \
  --reason "Waiting on upstream dependency"

# Machine-readable JSON output
spec-kitty agent status emit WP01 --to claimed --actor claude --json
```

**Options**:

| Option | Required | Description |
|--------|----------|-------------|
| `WP_ID` (argument) | Yes | Work package ID (e.g., `WP01`) |
| `--to` | Yes | Target lane (canonical or alias) |
| `--actor` | Yes | Who is making this transition |
| `--mission` | No | Mission slug |
| `--force` | No | Bypass guard conditions |
| `--reason` | When `--force` | Reason for forced transition |
| `--evidence-json` | When `--to done` | JSON string with DoneEvidence |
| `--review-ref` | When `for_review -> in_progress` | Review feedback reference |
| `--execution-mode` | No | `worktree` (default) or `direct_repo` |
| `--json` | No | Machine-readable JSON output |

### `spec-kitty agent status materialize`

Rebuild `status.json` from the canonical event log.

```bash
# Rebuild snapshot (auto-detects mission)
spec-kitty agent status materialize

# Specify mission explicitly
spec-kitty agent status materialize --mission 034-feature-name

# JSON output (full snapshot)
spec-kitty agent status materialize --mission 034-feature-name --json
```

**When to use**: After manual edits to `status.events.jsonl`, after resolving merge conflicts in the event log, or after running `status validate` reports materialization drift.

### `spec-kitty agent status validate`

Check event log integrity, transition legality, done-evidence completeness, and drift detection.

```bash
# Validate event log for a mission
spec-kitty agent status validate --mission 034-feature-name

# JSON output for CI integration
spec-kitty agent status validate --mission 034-feature-name --json
```

**Checks performed**:
1. **Schema validation**: All required fields present, ULID format, canonical lane values, ISO 8601 timestamps
2. **Transition legality**: Every `(from_lane, to_lane)` pair is in the allowed transitions set (force transitions are always legal)
3. **Done-evidence completeness**: Every done transition has evidence or force flag
4. **Materialization drift**: Compares `status.json` on disk with reducer output from event log
5. **Derived-view drift**: Compares materialized `status.json` against canonical event log (error if diverged)

### `spec-kitty agent status reconcile`

Scan target repositories for WP-linked branches and commits, detect planning-vs-implementation drift, and optionally emit reconciliation events.

```bash
# Preview reconciliation suggestions (dry-run is the default)
spec-kitty agent status reconcile --mission 034-feature-name --dry-run

# Scan a specific target repository
spec-kitty agent status reconcile --mission 034-feature-name \
  --target-repo /path/to/implementation-repo --dry-run

# Apply reconciliation events (2.x only; disabled on 0.1x)
spec-kitty agent status reconcile --mission 034-feature-name --apply
```

**How it works**:
1. Scans target repos for branches matching `*<feature-slug>*WP##*`
2. Scans commit messages containing `WP##`
3. Checks which lane or mission branches are merged into the target branch
4. Compares implementation evidence against canonical snapshot state
5. Generates legal transition events to align planning with reality

**Limitations on 0.1x**: `--apply` is disabled. Reconciliation is dry-run only.

### `spec-kitty agent status doctor`

Run health checks detecting stale claims, orphan workspaces, and unresolved drift.

```bash
# Run all health checks for a mission
spec-kitty agent status doctor --mission 034-feature-name
```

**Health checks**:

| Check | Severity | Description |
|-------|----------|-------------|
| Stale claims | Warning | WPs in `claimed` for >7 days or `in_progress` for >14 days |
| Orphan workspaces | Warning | Worktrees existing for features where all WPs are terminal (done/canceled) |
| Materialization drift | Warning | `status.json` does not match reducer output |
| Derived-view drift | Error | Materialized snapshot differs from canonical event log |

### `spec-kitty agent status migrate`

Bootstrap canonical event logs from existing frontmatter lane state.

```bash
# Preview migration for a single feature
spec-kitty agent status migrate --mission 034-feature-name --dry-run

# Execute migration for a single feature
spec-kitty agent status migrate --mission 034-feature-name

# Migrate all features
spec-kitty agent status migrate --all

# Preview all migrations
spec-kitty agent status migrate --all --dry-run
```

**Migration behavior** (for pre-3.0 features):
- Reads current frontmatter `lane` values from all WP files in the feature
- Resolves aliases (`doing` -> `in_progress`) before creating events
- Generates one bootstrap event per WP: `from_lane=planned, to_lane=<current_lane>`
- WPs already at `planned` produce no events (no transition occurred)
- Idempotent: features with existing non-empty `status.events.jsonl` are skipped
- Verification: reads back persisted events and confirms count matches

**For new features (3.0+)**: `finalize-tasks` bootstraps WP definitions. All subsequent status transitions are emitted directly to the event log via `emit_status_transition()`. No frontmatter lane is written.

### Legacy Compatibility

The existing `move-task` command still works and internally delegates to the status emit pipeline:

```bash
# This still works -- delegates to status emit internally
spec-kitty agent tasks move-task WP01 --to doing
# "doing" is accepted as alias, persists as "in_progress" in the event log
```

## 9-Lane State Machine

### Canonical Lanes

| Lane | Description | Terminal |
|------|-------------|----------|
| `planned` | WP defined, not yet claimed | No |
| `claimed` | WP assigned to an actor, not yet started | No |
| `in_progress` | Active implementation underway | No |
| `for_review` | Implementation complete, awaiting review | No |
| `in_review` | Reviewer actively examining implementation | No |
| `approved` | Review passed, awaiting merge | No |
| `done` | Merged and accepted | Yes (unless forced) |
| `blocked` | Blocked by external dependency or issue | No |
| `canceled` | Permanently abandoned | Yes |

**Alias**: `doing` -> `in_progress` (resolved at input boundaries, never persisted in events)

**Display**: The kanban board shows 6 columns (Planned, Doing, For Review, In Review, Approved, Done). `claimed` WPs appear in the Planned column, `in_progress` appears as "Doing", and `blocked`/`canceled` WPs are shown separately below the board.

### Allowed Transitions (27 pairs)

```
# Normal flow (implementation progression)
planned     -> claimed         (requires actor)
claimed     -> in_progress     (workspace context)
in_progress -> for_review      (subtasks check)

# Review progression
for_review  -> in_review       (reviewer claims; actor required with conflict detection)
in_review   -> approved        (ReviewResult required)
in_review   -> done            (ReviewResult required)

# Direct approval paths (legacy, kept for backward compat)
in_progress -> approved        (direct approval path)
approved    -> done            (merge verified)

# Feedback loops
in_review   -> in_progress     (changes requested, ReviewResult required)
in_review   -> planned         (rejection with feedback, ReviewResult required)
approved    -> in_progress     (rework after approval, requires review_ref)
approved    -> planned         (rejection after approval, requires review_ref)
in_progress -> planned         (abandon/reassign, requires reason)

# Blocking
planned     -> blocked
claimed     -> blocked
in_progress -> blocked
for_review  -> blocked
in_review   -> blocked         (ReviewResult required)
approved    -> blocked
blocked     -> in_progress

# Cancellation
planned     -> canceled
claimed     -> canceled
in_progress -> canceled
for_review  -> canceled
in_review   -> canceled        (ReviewResult required)
approved    -> canceled
blocked     -> canceled
```

**Force override**: Any transition can be forced with `--force --actor <name> --reason <text>`. Forced transitions from terminal states (done, canceled) are allowed. All force events carry a full audit trail.

### Guard Conditions

| Transition | Guard | Error if Violated |
|------------|-------|-------------------|
| `planned -> claimed` | Actor identity required | "Transition planned -> claimed requires actor identity" |
| `claimed -> in_progress` | Workspace context (placeholder, always passes) | "No workspace context" |
| `in_progress -> for_review` | Subtask completion check (placeholder) | "Unchecked subtasks" |
| `in_progress -> approved` | Reviewer approval evidence required | "Missing review approval evidence" |
| `for_review -> in_review` | Actor identity required (conflict detection) | "Transition for_review -> in_review requires actor identity" |
| `in_review -> *` (all outbound) | ReviewResult required in TransitionContext | "in_review outbound transitions require ReviewResult" |
| `approved -> done` | Reviewer approval evidence required | "Missing review approval evidence" |
| `approved -> in_progress` | Review feedback reference required | "Missing review feedback reference" |
| `approved -> planned` | Review feedback reference required | "Missing review feedback reference" |
| `in_progress -> planned` | Reason required | "Transition in_progress -> planned requires reason" |
| Any forced transition | Actor AND reason required | "Force transitions require actor and reason" |

## Migration Phases

The status model used a phased rollout. As of 3.0, **Phase 2 is the active and only supported model**. Phases 0 and 1 are historical and no longer apply to new features.

| Phase | Name | Behavior | Status |
|-------|------|----------|--------|
| 0 | Hardening | Transition matrix enforced, no event log. Frontmatter was sole authority. | **Historical** |
| 1 | Dual-write | Events AND frontmatter updated on every transition. Reads came from frontmatter. | **Historical** |
| 2 | Read-cutover | `status.events.jsonl` is sole authority. `status.json` is derived snapshot. | **Active (3.0)** |

**Default**: Phase 2 (event-log authority). Frontmatter lane is no longer written or read by active runtime commands.

### Configuration

**Global default** (`.kittify/config.yaml`):

```yaml
status:
  phase: 1  # 0=hardening, 1=dual-write, 2=read-cutover
```

**Per-feature override** (`kitty-specs/<feature>/meta.json`):

```json
{
  "status_phase": 2
}
```

**Precedence**: meta.json > config.yaml > built-in default (1)

**On 0.1x branches**: Phase is capped at 2 (maximum). Reconcile `--apply` is disabled.

### Migration Workflow

To migrate existing features to the canonical event log:

1. **Preview**: Run `spec-kitty agent status migrate --all --dry-run` to see what would happen
2. **Execute**: Run `spec-kitty agent status migrate --all` to bootstrap event logs from frontmatter
3. **Verify**: Run `spec-kitty agent status validate --mission <slug>` for each mission to confirm integrity
4. **Optionally advance to Phase 2**: Set `status.phase: 2` in config.yaml or per-feature in meta.json

## Canonical Event Log Format

Events are stored in `kitty-specs/<feature>/status.events.jsonl` as one JSON object per line:

```json
{"actor":"claude","at":"2026-02-08T12:00:00+00:00","event_id":"01HXYZ...","evidence":null,"execution_mode":"worktree","mission_slug":"034-feature-name","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
```

Keys are always sorted (`sort_keys=True`) for deterministic, merge-friendly output.

## File Layout (per feature)

```
kitty-specs/<feature>/
  status.events.jsonl    # CANONICAL: append-only event log
  status.json            # DERIVED: materialized snapshot (regenerable)
  meta.json              # Feature metadata (includes optional status_phase)
  tasks/
    WP01-name.md         # DERIVED: frontmatter lane is compatibility view
    WP02-name.md
  tasks.md               # DERIVED: status sections from snapshot
```

**Authority hierarchy** (3.0):
1. `status.events.jsonl` -- canonical truth (append-only, immutable events)
2. `status.json` -- derived snapshot (regenerable via `status materialize`)
3. WP frontmatter -- static definition only (title, dependencies, subtasks); `lane` field is historical/migration-only
4. `tasks.md` status sections -- human view (regenerable)

## Troubleshooting

**"Illegal transition" error**: The transition is not in the allowed transitions matrix. Use `--force --actor <name> --reason <text>` to override, or check that the from_lane matches what you expect (run `status materialize --json` to see current state).

**Materialization drift detected**: Run `spec-kitty agent status materialize` to regenerate `status.json` from the event log.

**Frontmatter lane drift** (legacy missions only): Frontmatter lane is no longer part of the active status model. For pre-3.0 missions that still have frontmatter lane values, run `spec-kitty agent status migrate --mission <slug>` to bootstrap the event log, then status is managed exclusively via events.

**"No event log found"**: Run `spec-kitty agent status migrate --mission <slug>` to bootstrap from existing frontmatter state.

**Stale claims reported by doctor**: Either continue work on the WP or release the claim by moving it back to `planned` (requires reason).

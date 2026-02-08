# Status Model: Operator Documentation

**Feature**: 034-feature-status-state-model-remediation
**Since**: 2.x (backport to 0.1x planned)

## Overview

The status model replaces spec-kitty's scattered status authority (frontmatter, meta.json, tasks.md) with a single canonical append-only event log per feature. Every lane transition becomes an immutable `StatusEvent`. A deterministic reducer produces `status.json` snapshots and human-readable compatibility views.

**Key principle**: `status.events.jsonl` is the single source of truth. Everything else is derived and regenerable.

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
| `--feature` | No | Feature slug (auto-detected from worktree if omitted) |
| `--force` | No | Bypass guard conditions |
| `--reason` | When `--force` | Reason for forced transition |
| `--evidence-json` | When `--to done` | JSON string with DoneEvidence |
| `--review-ref` | When `for_review -> in_progress` | Review feedback reference |
| `--execution-mode` | No | `worktree` (default) or `direct_repo` |
| `--json` | No | Machine-readable JSON output |

### `spec-kitty agent status materialize`

Rebuild `status.json` from the canonical event log.

```bash
# Rebuild snapshot (auto-detects feature)
spec-kitty agent status materialize

# Specify feature explicitly
spec-kitty agent status materialize --feature 034-feature-name

# JSON output (full snapshot)
spec-kitty agent status materialize --feature 034-feature-name --json
```

**When to use**: After manual edits to `status.events.jsonl`, after resolving merge conflicts in the event log, or after running `status validate` reports materialization drift.

### `spec-kitty agent status validate`

Check event log integrity, transition legality, done-evidence completeness, and drift detection.

```bash
# Validate event log for a feature
spec-kitty agent status validate --feature 034-feature-name

# JSON output for CI integration
spec-kitty agent status validate --feature 034-feature-name --json
```

**Checks performed**:
1. **Schema validation**: All required fields present, ULID format, canonical lane values, ISO 8601 timestamps
2. **Transition legality**: Every `(from_lane, to_lane)` pair is in the allowed transitions set (force transitions are always legal)
3. **Done-evidence completeness**: Every done transition has evidence or force flag
4. **Materialization drift**: Compares `status.json` on disk with reducer output from event log
5. **Derived-view drift**: Compares WP frontmatter `lane` fields against canonical snapshot (Phase 1: warning, Phase 2: error)

### `spec-kitty agent status reconcile`

Scan target repositories for WP-linked branches and commits, detect planning-vs-implementation drift, and optionally emit reconciliation events.

```bash
# Preview reconciliation suggestions (dry-run is the default)
spec-kitty agent status reconcile --feature 034-feature-name --dry-run

# Scan a specific target repository
spec-kitty agent status reconcile --feature 034-feature-name \
  --target-repo /path/to/implementation-repo --dry-run

# Apply reconciliation events (2.x only; disabled on 0.1x)
spec-kitty agent status reconcile --feature 034-feature-name --apply
```

**How it works**:
1. Scans target repos for branches matching `*<feature-slug>*WP##*`
2. Scans commit messages containing `WP##`
3. Checks which WP branches are merged into main/master
4. Compares implementation evidence against canonical snapshot state
5. Generates legal transition events to align planning with reality

**Limitations on 0.1x**: `--apply` is disabled. Reconciliation is dry-run only.

### `spec-kitty agent status doctor`

Run health checks detecting stale claims, orphan workspaces, and unresolved drift.

```bash
# Run all health checks for a feature
spec-kitty agent status doctor --feature 034-feature-name
```

**Health checks**:

| Check | Severity | Description |
|-------|----------|-------------|
| Stale claims | Warning | WPs in `claimed` for >7 days or `in_progress` for >14 days |
| Orphan workspaces | Warning | Worktrees existing for features where all WPs are terminal (done/canceled) |
| Materialization drift | Warning | `status.json` does not match reducer output |
| Derived-view drift | Warning/Error | Frontmatter lanes differ from canonical state (Warning in Phase 1, Error in Phase 2) |

### `spec-kitty agent status migrate`

Bootstrap canonical event logs from existing frontmatter lane state.

```bash
# Preview migration for a single feature
spec-kitty agent status migrate --feature 034-feature-name --dry-run

# Execute migration for a single feature
spec-kitty agent status migrate --feature 034-feature-name

# Migrate all features
spec-kitty agent status migrate --all

# Preview all migrations
spec-kitty agent status migrate --all --dry-run
```

**Migration behavior**:
- Reads current frontmatter `lane` values from all WP files in the feature
- Resolves aliases (`doing` -> `in_progress`) before creating events
- Generates one bootstrap event per WP: `from_lane=planned, to_lane=<current_lane>`
- WPs already at `planned` produce no events (no transition occurred)
- Idempotent: features with existing non-empty `status.events.jsonl` are skipped
- Verification: reads back persisted events and confirms count matches

### Legacy Compatibility

The existing `move-task` command still works and internally delegates to the status emit pipeline:

```bash
# This still works -- delegates to status emit internally
spec-kitty agent tasks move-task WP01 --to doing
# "doing" is accepted as alias, persists as "in_progress" in the event log
```

## 7-Lane State Machine

### Canonical Lanes

| Lane | Description | Terminal |
|------|-------------|----------|
| `planned` | WP defined, not yet claimed | No |
| `claimed` | WP assigned to an actor, not yet started | No |
| `in_progress` | Active implementation underway | No |
| `for_review` | Implementation complete, awaiting review | No |
| `done` | Reviewed and accepted | Yes (unless forced) |
| `blocked` | Blocked by external dependency or issue | No |
| `canceled` | Permanently abandoned | Yes |

**Alias**: `doing` -> `in_progress` (resolved at input boundaries, never persisted in events)

### Allowed Transitions

```
planned     -> claimed         (requires actor)
claimed     -> in_progress     (workspace context)
in_progress -> for_review      (subtasks check)
for_review  -> done            (requires reviewer evidence)
for_review  -> in_progress     (changes requested, requires review_ref)
in_progress -> planned         (abandon/reassign, requires reason)

planned     -> blocked
claimed     -> blocked
in_progress -> blocked
for_review  -> blocked
blocked     -> in_progress

planned     -> canceled
claimed     -> canceled
in_progress -> canceled
for_review  -> canceled
blocked     -> canceled
```

**Force override**: Any transition can be forced with `--force --actor <name> --reason <text>`. Forced transitions from terminal states (done, canceled) are allowed. All force events carry a full audit trail.

### Guard Conditions

| Transition | Guard | Error if Violated |
|------------|-------|-------------------|
| `planned -> claimed` | Actor identity required | "Transition planned -> claimed requires actor identity" |
| `claimed -> in_progress` | Workspace context (placeholder, always passes) | "No workspace context" |
| `in_progress -> for_review` | Subtask completion check (placeholder) | "Unchecked subtasks" |
| `for_review -> done` | Reviewer approval evidence required | "Missing review approval evidence" |
| `for_review -> in_progress` | Review feedback reference required | "Missing review feedback reference" |
| `in_progress -> planned` | Reason required | "Transition in_progress -> planned requires reason" |
| Any forced transition | Actor AND reason required | "Force transitions require actor and reason" |

## Migration Phases

The status model uses a phased rollout to minimize risk:

| Phase | Name | Behavior |
|-------|------|----------|
| 0 | Hardening | Transition matrix enforced, no event log. Frontmatter is sole authority. |
| 1 | Dual-write | Events AND frontmatter updated on every transition. Reads still come from frontmatter. |
| 2 | Read-cutover | `status.json` is sole authority. Frontmatter is a generated compatibility view. |

**Default**: Phase 1 (dual-write).

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
3. **Verify**: Run `spec-kitty agent status validate --feature <slug>` for each feature to confirm integrity
4. **Optionally advance to Phase 2**: Set `status.phase: 2` in config.yaml or per-feature in meta.json

## Canonical Event Log Format

Events are stored in `kitty-specs/<feature>/status.events.jsonl` as one JSON object per line:

```json
{"actor":"claude","at":"2026-02-08T12:00:00+00:00","event_id":"01HXYZ...","evidence":null,"execution_mode":"worktree","feature_slug":"034-feature-name","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
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

**Authority hierarchy**:
1. `status.events.jsonl` -- canonical truth (append-only, immutable events)
2. `status.json` -- derived snapshot (regenerable via `status materialize`)
3. WP frontmatter `lane` -- compatibility view (regenerable via legacy bridge)
4. `tasks.md` status sections -- human view (regenerable)

## Troubleshooting

**"Illegal transition" error**: The transition is not in the allowed transitions matrix. Use `--force --actor <name> --reason <text>` to override, or check that the from_lane matches what you expect (run `status materialize --json` to see current state).

**Materialization drift detected**: Run `spec-kitty agent status materialize` to regenerate `status.json` from the event log.

**Frontmatter lane drift**: In Phase 1 this is a warning (frontmatter is still authoritative for reads). In Phase 2 this is an error. Run `status materialize` to resync the compatibility views.

**"No event log found"**: Run `spec-kitty agent status migrate --feature <slug>` to bootstrap from existing frontmatter state.

**Stale claims reported by doctor**: Either continue work on the WP or release the claim by moving it back to `planned` (requires reason).

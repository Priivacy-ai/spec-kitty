# Quickstart: Feature Status State Model Remediation

## What This Feature Does

Replaces spec-kitty's scattered status authority (frontmatter, meta.json, tasks.md) with a single canonical append-only event log per feature. Every lane transition becomes an immutable event. A deterministic reducer produces snapshots and human-readable views.

## New Commands

```bash
# Emit a status transition (validates against state machine)
spec-kitty agent status emit WP01 --to claimed --actor claude

# Force a transition (requires reason)
spec-kitty agent status emit WP01 --to in_progress --actor claude --force --reason "Reopening after review"

# Rebuild snapshot and views from canonical log
spec-kitty agent status materialize --feature 034-feature-name

# Validate event log integrity, transition legality, evidence, drift
spec-kitty agent status validate --feature 034-feature-name

# Detect planning vs implementation drift (dry-run)
spec-kitty agent status reconcile --feature 034-feature-name --dry-run

# Health check: stale claims, orphan workspaces, unresolved drift
spec-kitty agent status doctor --feature 034-feature-name
```

## Legacy Compatibility

```bash
# This still works — delegates to status emit internally
spec-kitty agent tasks move-task WP01 --to doing
# "doing" is accepted as alias → persists as "in_progress"
```

## 7-Lane State Machine

```
planned → claimed → in_progress → for_review → done
                                       ↓
                                  in_progress (changes requested)

any* → blocked → in_progress    (*except done, canceled)
any** → canceled                (**except done)
done → any                      (force only, requires actor + reason)
```

## File Layout

```
kitty-specs/<feature>/
├── status.events.jsonl    # CANONICAL: append-only event log
├── status.json            # DERIVED: materialized snapshot
├── tasks/WP01.md          # DERIVED: frontmatter lane is compatibility view
└── tasks.md               # DERIVED: status sections from snapshot
```

## Migration Phases

| Phase | Behavior | Default |
|-------|----------|---------|
| 0 | Hardening only (transition matrix, no event log) | — |
| 1 | Dual-write (events + frontmatter). Reads from frontmatter. | Yes |
| 2 | Canonical read. Frontmatter is generated view only. | — |

Configure globally:
```yaml
# .kittify/config.yaml
status:
  phase: 1
```

Or per-feature:
```json
// kitty-specs/<feature>/meta.json
{ "status_phase": 2 }
```

## Migrating Existing Features

```bash
# Bootstrap event log from current frontmatter state
spec-kitty agent status migrate --feature 034-feature-name

# Verify migration
spec-kitty agent status validate --feature 034-feature-name
```

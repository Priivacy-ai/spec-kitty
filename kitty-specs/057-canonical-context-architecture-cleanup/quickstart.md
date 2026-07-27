# Quickstart: Canonical Context Architecture Cleanup

**Feature**: 057-canonical-context-architecture-cleanup
**Date**: 2026-03-27

## What Changed

Spec Kitty 3.0 replaces four broken architectural patterns with clean alternatives:

| Old pattern | New pattern |
|-------------|-------------|
| Heuristic feature/WP detection from branches, env vars, cwd | Opaque context token bound once, used everywhere |
| Mutable status in WP frontmatter + status.json + event log | Event log is sole authority; everything else is derived |
| All WPs use sparse-checkout worktrees | `code_change` WPs use worktrees; `planning_artifact` WPs work in-repo |
| Merge operates on checked-out branch | Merge uses dedicated workspace under `.kittify/runtime/merge/` |
| Full workflow logic in agent command files | 3-line thin shims calling `spec-kitty agent shim <command>` |

## Upgrade

```bash
# Any command on an unmigrated project will tell you to upgrade:
spec-kitty status
# → "Project requires migration. Run `spec-kitty upgrade` to continue."

# Run the one-shot migration:
spec-kitty upgrade

# What it does:
# 1. Assigns project_uuid, mission_id, work_package_id to all entities
# 2. Infers execution_mode and owned_files for each WP
# 3. Rebuilds canonical event log from legacy state
# 4. Strips mutable fields from WP frontmatter
# 5. Rewrites agent command files as thin shims
# 6. Sets schema_version to 3
```

## Context Tokens

```bash
# Resolve context for a WP (done automatically by shim entrypoints):
spec-kitty agent context resolve --wp WP03 --feature 057-canonical-context-architecture-cleanup
# → ctx-01HVXYZ...

# All subsequent commands use the token:
spec-kitty agent tasks move-task --context ctx-01HVXYZ... --to for_review
spec-kitty review --context ctx-01HVXYZ...
spec-kitty merge --context ctx-01HVXYZ...

# Inspect a context token:
spec-kitty agent context show --context ctx-01HVXYZ...
```

## WP Frontmatter (Post-Migration)

```yaml
# ONLY static metadata — no lane, review_status, reviewed_by, progress
---
work_package_id: "01HVXYZ..."
wp_code: "WP03"
mission_id: "01HVXYZ..."
title: "Implement MissionContext resolver"
dependencies: ["WP01", "WP02"]
execution_mode: code_change
owned_files:
  - "src/specify_cli/context/**"
  - "tests/specify_cli/context/**"
authoritative_surface: "src/specify_cli/context/"
---
```

## Status (Event Log Only)

```bash
# Board state comes from event log, not frontmatter:
spec-kitty status

# Force-regenerate derived views (for CI or debugging):
spec-kitty materialize

# Derived files live in .kittify/derived/ (gitignored):
# .kittify/derived/<feature_slug>/status.json
# .kittify/derived/<feature_slug>/progress.json
# .kittify/derived/<feature_slug>/board-summary.json
```

## Merge

```bash
# Merge uses a dedicated workspace — does NOT touch your checkout:
spec-kitty merge --feature 057-canonical-context-architecture-cleanup

# Resume an interrupted merge:
spec-kitty merge --resume

# Merge workspace location:
# .kittify/runtime/merge/<mission_id>/workspace/
# .kittify/runtime/merge/<mission_id>/state.json
```

## Agent Shims

All 12 agent command files now look like this:

```markdown
Run this exact command and treat its output as authoritative.
Do not rediscover context from branches, files, or prompt contents.

`spec-kitty agent shim implement --agent claude --raw-args "$ARGUMENTS"`
```

The CLI shim entrypoint handles context resolution internally:
1. Parse raw args
2. Resolve context if no `--context` token present
3. Persist token
4. Execute workflow

## Filesystem Layout

```
.kittify/
├── metadata.yaml              # TRACKED — project_uuid, schema_version
├── config.yaml                # TRACKED — agent config
├── derived/                   # GITIGNORED — regenerable projections
│   └── <feature_slug>/
│       ├── status.json
│       ├── progress.json
│       └── board-summary.json
└── runtime/                   # GITIGNORED — ephemeral state
    ├── contexts/              # Opaque context token files
    ├── merge/<mission_id>/    # Dedicated merge workspace + state
    └── workspaces/            # WP workspace context files

kitty-specs/<feature_slug>/
├── status.events.jsonl        # TRACKED — sole mutable-state authority
├── meta.json                  # TRACKED — immutable mission identity
├── tasks/*.md                 # TRACKED — static frontmatter only
└── [spec.md, plan.md, ...]    # TRACKED — human-authored artifacts
```

## What Was Deleted

- `feature_detection.py` (668 lines) — heuristic slug/branch/WP detection
- `legacy_bridge.py` — dual-write to frontmatter and tasks.md
- `phase.py` — Phase 0/1/2 resolution
- `reconcile.py` — cross-authority drift detection
- `executor.py` (old merge) — merge on checked-out branch
- `forecast.py`, `status_resolver.py` — absorbed into new merge engine
- `agent_context.py` — tech-stack parsing for agent templates
- All full command templates (~56 markdown files across 4 missions)
- Sparse checkout policy enforcement
- Frontmatter lane/status read/write throughout codebase
- Move-task contamination heuristics
- Prompt-specific recovery instructions
- Git-noise filtering for generated artifacts

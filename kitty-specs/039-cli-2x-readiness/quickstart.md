# Quickstart: CLI 2.x Readiness Sprint

**Feature**: 039-cli-2x-readiness
**Date**: 2026-02-12

## Prerequisites

- Python 3.11+
- Git
- Access to the 2.x branch: `git checkout 2.x`
- spec-kitty-events library installed (vendored or via pip)

## Branch Setup

All work targets the **2.x branch**. Do NOT work on main for this sprint.

```bash
git checkout 2.x
git pull origin 2.x
```

## Work Package Implementation Order

### Wave 1 (Parallel — no dependencies)

These WPs can be implemented simultaneously by different agents:

| WP | Title | Effort | Key File(s) |
|----|-------|--------|-------------|
| WP01 | Fix setup-plan NameError | Small | `src/specify_cli/cli/commands/agent/feature.py` |
| WP02 | Fix batch error surfacing | Medium | `src/specify_cli/sync/batch.py`, `sync/queue.py` |
| WP03 | Fix sync status --check | Small | `src/specify_cli/sync/` or `cli/commands/sync.py` |
| WP05 | Extend sync status | Medium | `src/specify_cli/sync/queue.py` |
| WP06 | Lane mapping tests | Small | `src/specify_cli/sync/emitter.py` |
| WP08 | Global runtime convergence | Medium | `src/specify_cli/core/project_resolver.py` |

### Wave 2 (Depends on Wave 1)

| WP | Title | Depends On | Key File(s) |
|----|-------|------------|-------------|
| WP04 | Sync diagnose command | WP02 | `src/specify_cli/sync/diagnose.py` (new) |
| WP07 | SaaS handoff doc | WP02, WP06 | `kitty-specs/039-cli-2x-readiness/contracts/` |

### Wave 3 (Integration)

| WP | Title | Depends On | Key File(s) |
|----|-------|------------|-------------|
| WP09 | E2E smoke test | WP01, WP02 | `tests/e2e/test_cli_smoke.py` (new) |

## Running Tests

```bash
# Run all sync-related tests (baseline: 93+ should pass)
python -m pytest tests/specify_cli/sync/ -x -q

# Run planning workflow tests
python -m pytest tests/integration/test_planning_workflow.py -x -q

# Run task workflow tests
python -m pytest tests/integration/test_task_workflow.py -x -q

# Run full test suite (expect ~50 pre-existing failures from cross-test pollution)
python -m pytest tests/ -x -q
```

## Key Reference Documents

- **Spec**: `kitty-specs/039-cli-2x-readiness/spec.md`
- **Plan**: `kitty-specs/039-cli-2x-readiness/plan.md`
- **Batch ingest contract**: `kitty-specs/039-cli-2x-readiness/contracts/batch-ingest.md`
- **Lane mapping contract**: `kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md`
- **Data model**: `kitty-specs/039-cli-2x-readiness/data-model.md`
- **Constitution**: `.kittify/memory/constitution.md`

## Key Decisions

1. **Delivery branch**: 2.x (not main)
2. **Credential path**: `~/.spec-kitty/credentials` stays separate from `~/.kittify/`
3. **Lane mapping**: 7→4 collapse is lossy by design (BLOCKED→doing, CANCELED→done)
4. **No main changes**: Main remains offline-only, sync-free during this sprint

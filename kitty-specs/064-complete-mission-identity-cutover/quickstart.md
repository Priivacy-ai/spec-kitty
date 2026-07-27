# Quickstart: Complete Mission Identity Cutover

**Feature**: 064-complete-mission-identity-cutover
**Date**: 2026-04-06

## What This Feature Does

Completes and cleans up a partially-landed mission/build identity cutover on `main`. After this feature, all live runtime paths, machine-facing APIs, and event contracts use canonical mission-era terminology exclusively. Feature-era naming is confined to migration/upgrade code only.

## Implementation Phases

### Phase A: Foundation

**Compatibility gate** — Create a single validation function that checks payloads against the 3.0.0 contract shape. Insert at 6 chokepoints:
1. `EventEmitter._emit()` (emitter.py:579)
2. `batch_sync()` (batch.py:363)
3. `OfflineBodyUploadQueue.enqueue()` (body_queue.py:125)
4. `push_content()` (body_transport.py:42)
5. `SaaSTrackerClient._request()` (saas_client.py:159)
6. `WebSocketClient.send_event()` (client.py:229)

**meta.json canonical writes** — Update the create-feature scaffolding to write `mission_slug`, `mission_number`, `mission_type` instead of `feature_slug`, `feature_number`, `mission`.

### Phase B: Core Renames

Rename modules via `git mv` and update all imports:

```
feature_creation.py    → mission_creation.py    (2 prod + 3 test imports)
feature_metadata.py    → mission_metadata.py    (10 prod + 3 test imports)
agent/feature.py       → agent/mission.py       (1 prod + 35 test imports)
identity_aliases.py    → DELETED                (7 prod imports, 27 call sites)
```

### Phase C: Contract Cleanup

**Orchestrator API**: Rename 3 commands, 2 error codes, purge `feature_slug` from all response payloads.

**Body sync**: Rename `NamespaceRef` and `BodyUploadTask` fields. Migrate SQLite queue schema. Update transport payload.

**Tracker bind**: Add `build_id` to the project_identity dict.

**Status/progress/views**: Remove `with_tracked_mission_slug_aliases()` calls, emit `mission_slug` directly.

### Phase D: Validation

Shape conformance tests against upstream contracts. End-to-end grep audit for `feature_slug` on live paths.

### Phase E: Release

Blocked until Priivacy-ai/spec-kitty-orchestrator#6 is updated and validated.

## How to Verify

```bash
# After implementation, this grep must return zero results
# (excluding tests/ and explicit migration modules)
grep -r "feature_slug" src/specify_cli/ \
  --include="*.py" \
  -l \
  | grep -v "upgrade/" \
  | grep -v "migration/" \
  | grep -v "migrate"

# Run conformance tests
pytest tests/contract/ -v

# Run full test suite
pytest tests/ -v
```

## Key Files to Watch

| File | What Changes |
|------|-------------|
| `src/specify_cli/sync/namespace.py` | NamespaceRef field renames |
| `src/specify_cli/sync/body_queue.py` | BodyUploadTask field renames + queue schema |
| `src/specify_cli/sync/body_transport.py` | Request payload field renames |
| `src/specify_cli/cli/commands/tracker.py` | Add build_id to bind payload |
| `src/specify_cli/orchestrator_api/commands.py` | Command + error code renames, payload cleanup |
| `src/specify_cli/core/identity_aliases.py` | DELETED |
| `src/specify_cli/core/feature_creation.py` | RENAMED to mission_creation.py |
| `src/specify_cli/feature_metadata.py` | RENAMED to mission_metadata.py |
| `src/specify_cli/cli/commands/agent/feature.py` | RENAMED to agent/mission.py |

## Release Gate

This feature is not shippable until:
1. Priivacy-ai/spec-kitty-orchestrator#6 is resolved
2. The updated orchestrator is validated against the renamed contract
3. Both repos ship in lockstep (or orchestrator ships first)

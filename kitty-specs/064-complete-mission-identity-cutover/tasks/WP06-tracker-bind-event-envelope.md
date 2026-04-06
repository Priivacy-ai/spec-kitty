---
work_package_id: WP06
title: Tracker Bind + Event Envelope Verification
dependencies: [WP01, WP02]
requirement_refs:
- FR-002
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-012
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
- T037
- T038
- T039
- T040
- T041
phase: Phase C - Contract Cleanup
assignee: ''
agent: "opencode:gpt-5.4:python-reviewer:reviewer"
shell_pid: "89646"
history:
- timestamp: '2026-04-06T05:39:39Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/cli/commands/tracker.py
execution_mode: code_change
owned_files:
- src/specify_cli/tracker/saas_client.py
- src/specify_cli/cli/commands/tracker.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/client.py
- src/specify_cli/spec_kitty_events/models.py
- tests/sync/tracker/**
---

# Work Package Prompt: WP06 – Tracker Bind + Event Envelope Verification

## Objective

Add `build_id` to tracker bind payload (FR-009). Insert compatibility gate at tracker, event emitter, batch sync, and WebSocket chokepoints (FR-012). Audit all event emission and serialization paths for `build_id` preservation (FR-008).

## Context

**Tracker bind** currently sends `uuid`, `slug`, `node_id`, `repo_slug` but omits `build_id`. The upstream contract requires `build_id` on tracker bind payloads. `ProjectIdentity` already carries `build_id` — it just isn't included in the dict sent during bind.

**Event emission** already includes `build_id` on envelope construction, but it may be dropped during serialization, queue storage, or replay. This WP audits the full lifecycle to ensure end-to-end preservation.

See `kitty-specs/064-complete-mission-identity-cutover/contracts/tracker-bind.md` and `contracts/event-envelope.md` for post-cutover contracts.

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`

## Implementation

### T033: Add build_id to Tracker Bind

**Purpose**: Tracker bind must send build_id (FR-009).

**Steps**:
1. In `src/specify_cli/cli/commands/tracker.py` (line ~355-360), the `project_identity` dict:
   ```python
   project_identity = {
       "uuid": str(identity.project_uuid),
       "slug": identity.project_slug,
       "node_id": identity.node_id,
       "repo_slug": identity.repo_slug,
       "build_id": identity.build_id,  # ADD THIS
   }
   ```
2. Verify `identity.build_id` is populated (ProjectIdentity already generates and persists it)
3. Check if `build_id` needs to be added to other tracker operations (bind_resolve, bind_confirm, bind_validate)

### T034: Insert Gate at Tracker Chokepoint

**Purpose**: All tracker HTTP calls validated before send.

**Steps**:
1. In `src/specify_cli/tracker/saas_client.py`, find the `_request()` method (line ~159)
2. If the method handles all HTTP calls, insert gate there:
   ```python
   from specify_cli.core.contract_gate import validate_outbound_payload
   # Only validate on relevant endpoints (bind calls include project_identity)
   if payload and "build_id" in payload.get("project_identity", {}):
       validate_outbound_payload(payload["project_identity"], "tracker_bind")
   ```
3. Alternatively, insert gate specifically in `bind_resolve()`, `bind_confirm()`, `bind_validate()` before the HTTP call

### T035: Insert Gate at Event Emission Chokepoints

**Purpose**: All events validated before WebSocket send or queue storage.

**Steps**:
1. **`EventEmitter._emit()`** (emitter.py, line ~579):
   - This is the central dispatch — all events pass through here
   - Insert gate validation on the event envelope:
     ```python
     validate_outbound_payload(event_envelope, "envelope")
     ```
2. **`batch_sync()`** (batch.py, line ~363):
   - Before the HTTP POST to events/batch
   - Validate each event in the batch
3. **`WebSocketClient.send_event()`** (client.py, line ~229):
   - Before WebSocket transmission
   - Validate the event envelope

### T036: Audit Event Emission for build_id Presence

**Purpose**: Verify build_id is set on every emitted event.

**Steps**:
1. Read `EventEmitter._emit()` and trace how the envelope is constructed
2. Verify `build_id` is sourced from `ProjectIdentity.build_id` (not None, not empty)
3. Check each `emit_*` method (there are 9: wp_status_changed, wp_created, wp_assigned, feature_created, feature_completed, history_added, error_logged, dependency_resolved, mission_origin_bound)
4. **Note**: `emit_feature_created` and `emit_feature_completed` must either be renamed to `emit_mission_created`/`emit_mission_closed` or verified as already using the correct event types. Check the event_type strings.

### T037: Audit Serialization/Deserialization for build_id

**Purpose**: build_id must survive storage and replay (FR-008).

**Steps**:
1. Check offline queue storage: when events go to the SQLite queue, is `build_id` stored?
2. Check offline queue replay: when events are replayed from the queue, is `build_id` included?
3. Check batch sync: when events are batched for HTTP POST, is `build_id` preserved in the batch payload?
4. Check any event deserialization (e.g., `StatusEvent.from_dict()`) — does it read `build_id`?
5. Fix any path where `build_id` is silently dropped

### T038: Verify aggregate_type is "Mission"

**Purpose**: No emitted event may have `aggregate_type: "Feature"` (FR-018).

**Steps**:
1. Search: `grep -r "aggregate_type" src/specify_cli/sync/` — find all places where aggregate_type is set
2. Verify each occurrence uses `"Mission"`, never `"Feature"`
3. Search for any `FeatureCreated` or `FeatureCompleted` event type strings in emitter.py
4. If found, rename to `MissionCreated` / `MissionClosed` or verify they're already canonical

### T039: Update Tracker Integration Tests

**Purpose**: Tests must verify build_id in bind payloads.

**Steps**:
1. Update `tests/sync/tracker/test_origin.py` and `test_origin_integration.py`
2. Add assertion that `project_identity` dict contains `build_id`
3. Add assertion that `build_id` is a non-empty string (UUID format)
4. Run: `pytest tests/sync/tracker/ -v`

### T040: Rename FeatureCreated / FeatureCompleted Event Surfaces

**Purpose**: The codebase still defines and emits `FeatureCreated` and `FeatureCompleted` event types. These are forbidden on live surfaces (FR-002).

**Steps**:
1. In `src/specify_cli/sync/events.py` (lines ~243, ~266):
   - Rename `emit_feature_created()` → `emit_mission_created()` (or verify MissionCreated is already the live emitter and remove the legacy helper)
   - Rename `emit_feature_completed()` → `emit_mission_closed()` (or remove)
2. In `src/specify_cli/sync/emitter.py`:
   - `_PAYLOAD_RULES` dict (lines ~152, ~162): rename keys `"FeatureCreated"` → `"MissionCreated"`, `"FeatureCompleted"` → `"MissionClosed"`
   - `emit_feature_created()` method (line ~433): rename to `emit_mission_created()`, change `event_type="FeatureCreated"` → `event_type="MissionCreated"`
   - `emit_feature_completed()` method (line ~458): rename to `emit_mission_closed()`, change `event_type="FeatureCompleted"` → `event_type="MissionClosed"`
3. Update all callers of these methods across the codebase: `grep -rn "emit_feature_created\|emit_feature_completed" src/`
4. Verify no `FeatureCreated` or `FeatureCompleted` string remains in active sync paths

### T041: Update Vendored Event Model with build_id and schema_version

**Purpose**: The vendored `spec_kitty_events/models.py` has no `build_id` or `schema_version` fields. The envelope must carry both (FR-007).

**Steps**:
1. Read `src/specify_cli/spec_kitty_events/models.py` to understand the current Event/Envelope model
2. Add `build_id: str` field to the envelope/event model
3. Add `schema_version: str` field to the envelope/event model (default `"3.0.0"`)
4. Ensure the fields are included in serialization (`.to_dict()`, `.to_json()`, or however the model serializes)
5. Ensure the fields are read during deserialization (`.from_dict()`, etc.)
6. Update any model validation to require these fields on construction
7. Run model-level tests to verify

## Definition of Done

- [ ] Tracker bind payload includes `build_id`
- [ ] Gate validates at tracker, emitter, batch sync, and WebSocket chokepoints
- [ ] `build_id` present on every emitted event envelope
- [ ] `build_id` preserved through queue storage and replay
- [ ] `aggregate_type` is `"Mission"` everywhere
- [ ] No `FeatureCreated` or `FeatureCompleted` event types in active paths
- [ ] `emit_feature_created()` / `emit_feature_completed()` renamed or removed from events.py and emitter.py
- [ ] Vendored event model in `spec_kitty_events/models.py` includes `build_id` and `schema_version`
- [ ] Tracker integration tests assert `build_id`
- [ ] `grep -rn "FeatureCreated\|FeatureCompleted" src/specify_cli/sync/` returns zero results

## Risks

- Gate insertion at `_emit()` may be too strict if some events don't carry all envelope fields — use context-appropriate validation
- `emit_feature_created()` may coexist with a canonical `emit_mission_created()` — check both events.py and emitter.py for the canonical path before renaming
- Vendored model changes must not break existing event deserialization — add fields as optional with defaults for backward compatibility during migration

## Activity Log

- 2026-04-06T07:48:29Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=85565 – Started implementation via action command
- 2026-04-06T08:08:32Z – claude:sonnet-4.6:python-implementer:implementer – shell_pid=85565 – Ready for review: tracker bind build_id, event envelope verification, rename FeatureCreated/Completed to MissionCreated/MissionClosed
- 2026-04-06T08:09:26Z – opencode:gpt-5.4:python-reviewer:reviewer – shell_pid=89646 – Started review via action command
- 2026-04-06T08:17:13Z – opencode:gpt-5.4:python-reviewer:reviewer – shell_pid=89646 – Fixed: removed legacy aliases, added build_id to heartbeat (cycle 2)

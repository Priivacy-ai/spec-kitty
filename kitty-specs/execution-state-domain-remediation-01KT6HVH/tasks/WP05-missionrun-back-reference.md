---
work_package_id: WP05
title: MissionRun → Mission Back-Reference
dependencies:
- WP01
requirement_refs:
- FR-024
- FR-025
- FR-026
- FR-027
- FR-029
- FR-030
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-execution-state-domain-remediation-01KT6HVH
base_commit: 8501abd1b9a0dd95272290bcda1e0ce4d3c94845
created_at: '2026-06-03T12:06:17.834015+00:00'
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "66734"
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: python-pedro
authoritative_surface: src/runtime/next/_internal_runtime/
execution_mode: code_change
owned_files:
- src/runtime/next/_internal_runtime/schema.py
- src/runtime/next/_internal_runtime/engine.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `python-pedro` before reading further.

---

## Objective

Add optional `mission_id` and `mission_slug` fields to `MissionRunSnapshot` and `MissionRunRef` so that a runtime run can name its concrete mission without an external index scan. All new fields default to `None` for backward-compatibility with existing on-disk `state.json` files.

## Branch Strategy

- **Planning base**: `main` | **Merge target**: `main`
- **Prerequisite**: WP01 (ADRs) must be merged; can run in parallel with WP02, WP03, WP04
- Start with: `spec-kitty agent action implement WP05 --agent claude`

## Context

**Root problem**: `MissionRunSnapshot` stores `run_id` and `mission_key` (the mission type, e.g., "software-dev") but has no `mission_id` (the concrete mission ULID) or `mission_slug`. Given only a run, code cannot resolve which concrete mission it belongs to without an external index scan.

**Key existing function**: `_resolve_mission_ulid(mission_slug, repo_root)` at `src/runtime/next/runtime_bridge.py:95` — reads `meta.json` and returns the ULID. This is called at `runtime_bridge.py:145`. It should be called at `start_mission_run` time to populate the new fields.

**Scope boundary (C-005)**: `MissionRunStartedPayload` in `spec_kitty_events` is **out of scope** — do not modify external event types.

**Blast radius in `engine.py`**: The following sites reconstruct snapshot fragments and must carry the new fields through:
- ~Line 207: `MissionRunRef(run_id=..., mission_key=...)` constructor
- ~Line 227: `return MissionRunRef(...)` 
- ~Lines 282–283: snapshot-copy block
- ~Lines 368–369: snapshot-copy block
- ~Lines 393–394: snapshot-copy block
- ~Line 448: partial snapshot ref

**Backward-compatibility**: Pydantic's `Optional[str] = None` default means existing on-disk `state.json` files load without error. No migration file needed.

---

## Subtask T026 — Add Fields to MissionRunSnapshot

**File**: `src/runtime/next/_internal_runtime/schema.py`

**Steps**:
1. Read `schema.py` — find the `MissionRunSnapshot` class (around line 523)
2. Add two optional fields with `None` defaults:
   ```python
   class MissionRunSnapshot(BaseModel):
       # ... existing fields unchanged ...
       run_id: str
       mission_key: str
       # ... other existing fields ...

       # NEW — back-references to the concrete Mission
       mission_id: str | None = None   # canonical ULID from meta.json
       mission_slug: str | None = None  # human-readable slug
   ```
3. Do NOT change any existing field order or types — only append the new fields at the end

**Validation**: `MissionRunSnapshot(run_id="x", mission_key="software-dev")` works (new fields default to `None`). `MissionRunSnapshot.model_fields` includes both new fields.

---

## Subtask T027 — Add Fields to MissionRunRef

**File**: `src/runtime/next/_internal_runtime/engine.py`

**Steps**:
1. Read `engine.py` — find `class MissionRunRef` (around line 92)
2. Add two optional fields with `None` defaults:
   ```python
   class MissionRunRef(BaseModel):
       run_id: str
       run_dir: str
       mission_key: str
       # NEW
       mission_id: str | None = None
       mission_slug: str | None = None
   ```
3. Do NOT change existing fields

**Validation**: `MissionRunRef(run_id="x", run_dir="/tmp", mission_key="software-dev")` works. New fields default to `None`.

---

## Subtask T028 — Plumb Fields Through start_mission_run

**File**: `src/runtime/next/_internal_runtime/engine.py`, `start_mission_run` function (~line 196)

**Steps**:
1. Read the `start_mission_run` function in full
2. It currently creates `run_id = uuid4().hex` and constructs `MissionRunRef` with `run_id`, `run_dir`, `mission_key`
3. The `mission_slug` is available because the bridge calls `start_mission_run(template, inputs={"mission_slug": ...})` — but note: `inputs["mission_slug"]` at line 216 is a **write-only dead field** (T030 will remove it). Instead, `mission_slug` should come from the `template` or a new parameter.

4. **Determine how `mission_slug` reaches `start_mission_run`**:
   - Read `runtime_bridge.py` around line 145 where `_resolve_mission_ulid` is called and `start_mission_run` is invoked
   - The bridge already has `mission_slug` available at call time
   - Add `mission_slug: str | None = None` and `mission_id: str | None = None` parameters to `start_mission_run`

5. Update `start_mission_run` signature:
   ```python
   def start_mission_run(
       template: ...,
       actor: ...,
       inputs: dict | None = None,
       mission_slug: str | None = None,   # NEW
       mission_id: str | None = None,     # NEW
   ) -> MissionRunRef:
   ```

6. Inside `start_mission_run`, use the new params when constructing the initial snapshot and `MissionRunRef`:
   ```python
   run_ref = MissionRunRef(
       run_id=run_id,
       run_dir=str(run_dir),
       mission_key=template.mission.key,
       mission_id=mission_id,     # NEW
       mission_slug=mission_slug, # NEW
   )
   ```

7. In `runtime_bridge.py` at the call site (~line 145), pass the values:
   ```python
   mission_id = _resolve_mission_ulid(mission_slug, repo_root)
   ref = engine.start_mission_run(
       template=template,
       actor=actor,
       mission_slug=mission_slug,  # NEW
       mission_id=mission_id,      # NEW
   )
   ```
   Note: `runtime_bridge.py` is owned by WP06. Coordinate the bridge call-site change with WP06, OR make the change in this WP since it's a necessary plumbing step. Discuss with the WP06 implementer if there's a conflict.

**Validation**: After implementing, a new run created via the bridge has non-None `mission_id` and `mission_slug` in the snapshot.

---

## Subtask T029 — Update All 6 In-Engine Snapshot-Copy Sites

**File**: `src/runtime/next/_internal_runtime/engine.py`

**Purpose**: Ensure no snapshot-copy site silently drops the new fields.

**Steps**:
1. Search for all places that construct a `MissionRunRef` or copy snapshot data:
   ```bash
   grep -n "MissionRunRef\|run_id=snapshot\|mission_key=snapshot" src/runtime/next/_internal_runtime/engine.py
   ```
2. For each site found, verify it passes `mission_id` and `mission_slug` through:
   - If constructing a new `MissionRunRef` or snapshot fragment: add the two new fields
   - If copying from an existing snapshot: copy `mission_id=snapshot.mission_id, mission_slug=snapshot.mission_slug`
3. The six approximate locations to check (verify against actual line numbers):
   - Line ~207: `MissionRunRef` constructor (primary creation) ← T028 handles this
   - Line ~227: `return MissionRunRef(...)` ← covered by T028
   - Line ~282: snapshot-copy block
   - Line ~368: snapshot-copy block  
   - Line ~393: snapshot-copy block
   - Line ~448: partial snapshot ref
4. For each: add `mission_id=snapshot.mission_id, mission_slug=snapshot.mission_slug`

**Important**: Line 465 constructs `MissionRunStartedPayload` — this is **out of scope** (C-005, external event type). Do NOT modify it.

**Validation**: `grep -n "MissionRunRef\|MissionRunSnapshot" src/runtime/next/_internal_runtime/engine.py` — every construction site includes `mission_id` and `mission_slug`.

---

## Subtask T030 — Remove Dead inputs["mission_slug"] Field

**File**: `src/runtime/next/_internal_runtime/engine.py`, ~line 216

**Purpose**: The `inputs={"mission_slug": ...}` in `start_mission_run` is a write-only dead field — nothing ever reads `inputs["mission_slug"]` back. Remove it.

**Steps**:
1. Find line ~216: `inputs={"mission_slug": mission_slug}` or similar
2. Verify with grep that `inputs["mission_slug"]` is never read anywhere in `engine.py` or `schema.py`:
   ```bash
   grep -n 'inputs\["mission_slug"\]\|inputs\.get.*mission_slug' src/runtime/next/_internal_runtime/
   ```
3. If confirmed dead: remove the write. If `inputs` parameter itself has other uses, only remove the `"mission_slug"` key.
4. If `inputs` dict is now empty after removal, consider removing the parameter entirely (check call sites first)

**Validation**: No write to `inputs["mission_slug"]` remains. `grep -n 'mission_slug.*inputs' src/runtime/next/_internal_runtime/engine.py` returns zero hits.

---

## Subtask T031 — Verify Backward-Compatibility

**Purpose**: Prove that existing on-disk `state.json` files with no `mission_id`/`mission_slug` fields load without error.

**Steps**:
1. Write a unit test (or extend an existing one) in `tests/unit/runtime/` or equivalent:
   ```python
   def test_mission_run_snapshot_loads_without_mission_id():
       """Existing state.json files (no mission_id/mission_slug) load with None defaults."""
       legacy_json = {
           "run_id": "abc123",
           "mission_key": "software-dev",
           # ... other existing fields ...
           # mission_id and mission_slug are absent
       }
       snapshot = MissionRunSnapshot(**legacy_json)
       assert snapshot.mission_id is None
       assert snapshot.mission_slug is None

   def test_mission_run_ref_loads_without_mission_id():
       ref = MissionRunRef(run_id="x", run_dir="/tmp", mission_key="software-dev")
       assert ref.mission_id is None
       assert ref.mission_slug is None
   ```
2. Run the full test suite: `pytest tests/ -x -q`
3. Verify no existing tests fail due to the new fields

**Validation**: Both backward-compat tests pass. No existing tests regress.

---

## Definition of Done

- [ ] `MissionRunSnapshot` has `mission_id: str | None = None` and `mission_slug: str | None = None`
- [ ] `MissionRunRef` has `mission_id: str | None = None` and `mission_slug: str | None = None`
- [ ] `start_mission_run` accepts and plumbs `mission_id` and `mission_slug` into the snapshot
- [ ] All 6 snapshot-copy sites in `engine.py` carry the new fields through
- [ ] Dead `inputs["mission_slug"]` write removed
- [ ] Backward-compat test: existing JSON without new fields loads with `None` defaults
- [ ] `pytest tests/ -x` passes — no regressions

## Risks

- `start_mission_run` may not receive `mission_slug` directly — trace the call chain from `runtime_bridge.py` before modifying
- Line numbers in `engine.py` are approximate — grep to find the actual locations
- The bridge call-site change (passing `mission_slug=` to `start_mission_run`) touches `runtime_bridge.py`, which is owned by WP06 — coordinate with the WP06 implementer or handle it here if WP06 has not started

## Reviewer Guidance

- Verify `MissionRunStartedPayload` at ~line 465 is UNCHANGED (out of scope)
- Check that all 6 snapshot-copy sites now carry `mission_id` and `mission_slug`
- Confirm backward-compat test is present and passes with a snapshot that has no `mission_id` key

## Activity Log

- 2026-06-03T12:06:19Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=66734 – Assigned agent via action command

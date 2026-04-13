---
work_package_id: WP02
title: Remove emitter drift-window fallback and fix callers
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus:reviewer:reviewer"
shell_pid: "80162"
history:
- at: '2026-04-13T04:59:36Z'
  by: spec-kitty.tasks
  note: WP created during task generation
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
owned_files:
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/events.py
- src/specify_cli/core/mission_creation.py
- src/specify_cli/tracker/origin.py
tags: []
---

# WP02: Remove emitter drift-window fallback and fix callers

## Objective

Make `mission_id` a mandatory parameter on all three sync emitter methods and their wrapper functions. Remove the `effective_aggregate_id` slug fallback pattern. Fix the two call sites that don't currently pass `mission_id`.

## Context

Three emitter methods (`emit_mission_created`, `emit_mission_closed`, `emit_mission_origin_bound`) currently have `mission_id: str | None = None` and fall back to using `mission_slug` as the `aggregate_id` when `mission_id` is `None`. This drift-window compatibility pattern is no longer needed.

**Call-site audit findings** (from research.md):
- `emit_mission_created`: wrapper in `events.py` accepts and forwards `mission_id`. Caller in `mission_creation.py` passes `meta.get("mission_id")` — always non-None for new missions.
- `emit_mission_closed`: wrapper in `events.py` does **not** accept `mission_id` (gap). No external callers yet.
- `emit_mission_origin_bound`: called directly from `tracker/origin.py` **without** `mission_id` (gap).

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Implementation

### Subtask T004: Make mission_id mandatory in emit_mission_created

**File**: `src/specify_cli/sync/emitter.py`

**Current signature** (line 468-476):
```python
def emit_mission_created(
    self,
    mission_slug: str,
    mission_number: int | None,
    target_branch: str,
    wp_count: int,
    created_at: str | None = None,
    causation_id: str | None = None,
    mission_id: str | None = None,
) -> dict[str, Any] | None:
```

**Changes**:
1. Change `mission_id: str | None = None` → `mission_id: str` and move it before optional params:
   ```python
   def emit_mission_created(
       self,
       mission_slug: str,
       mission_id: str,
       mission_number: int | None,
       target_branch: str,
       wp_count: int,
       created_at: str | None = None,
       causation_id: str | None = None,
   ) -> dict[str, Any] | None:
   ```
2. Remove the `effective_aggregate_id` fallback pattern (lines 497-505):
   ```python
   # REMOVE:
   effective_aggregate_id = mission_slug
   if mission_id is not None:
       payload["mission_id"] = mission_id
       effective_aggregate_id = mission_id
   ```
   Replace with:
   ```python
   payload["mission_id"] = mission_id
   ```
3. Change `aggregate_id=effective_aggregate_id` → `aggregate_id=mission_id` in the `_emit` call

### Subtask T005: Make mission_id mandatory in emit_mission_closed

**File**: `src/specify_cli/sync/emitter.py`

**Current signature** (line 514-522). Apply the same pattern as T004:
1. Change `mission_id: str | None = None` → `mission_id: str`, move before optional params
2. Remove `effective_aggregate_id` fallback (lines 540-544)
3. Always put `mission_id` in payload and use as `aggregate_id`

### Subtask T006: Make mission_id mandatory in emit_mission_origin_bound

**File**: `src/specify_cli/sync/emitter.py`

**Current signature** (line 628-638). Apply the same pattern as T004:
1. Change `mission_id: str | None = None` → `mission_id: str`, move before optional params
2. Remove `effective_aggregate_id` fallback (lines 656-660)
3. Always put `mission_id` in payload and use as `aggregate_id`

### Subtask T007: Update wrapper emit_mission_created in events.py

**File**: `src/specify_cli/sync/events.py`

**Current wrapper** (line 248-267):
```python
def emit_mission_created(
    mission_slug: str,
    mission_number: int | None,
    target_branch: str,
    wp_count: int,
    created_at: str | None = None,
    causation_id: str | None = None,
    mission_id: str | None = None,
) -> dict[str, Any] | None:
```

**Changes**:
1. Change `mission_id: str | None = None` → `mission_id: str` and move before optional params
2. Update the forwarding call to match the new emitter signature (positional order)

### Subtask T008: Add mission_id to wrapper emit_mission_closed in events.py

**File**: `src/specify_cli/sync/events.py`

**Current wrapper** (line 275-290) — **missing mission_id entirely**:
```python
def emit_mission_closed(
    mission_slug: str,
    total_wps: int,
    completed_at: str | None = None,
    total_duration: str | None = None,
    causation_id: str | None = None,
) -> dict[str, Any] | None:
```

**Changes**:
1. Add `mission_id: str` parameter (mandatory, before optional params)
2. Forward it to `get_emitter().emit_mission_closed(... mission_id=mission_id)`

### Subtask T009: Update caller in mission_creation.py

**File**: `src/specify_cli/core/mission_creation.py`

**Current call** (line 345-351):
```python
emit_mission_created(
    mission_slug=mission_slug_formatted,
    mission_number=None,
    target_branch=planning_branch,
    wp_count=0,
    mission_id=meta.get("mission_id"),
)
```

**Changes**:
1. At this point in the flow, `meta["mission_id"]` is always set (minted during creation). Replace `meta.get("mission_id")` with `meta["mission_id"]` to match the mandatory type.
2. Adjust keyword argument position if the emitter signature changed parameter order.

### Subtask T010: Update caller in tracker/origin.py

**File**: `src/specify_cli/tracker/origin.py`

**Current call** (line 265-272) — **missing mission_id**:
```python
emitter.emit_mission_origin_bound(
    mission_slug=mission_slug,
    provider=provider,
    external_issue_id=candidate.external_issue_id,
    external_issue_key=candidate.external_issue_key,
    external_issue_url=candidate.url,
    title=candidate.title,
)
```

**Changes**:
1. The function already has access to the mission's meta dict (or can load it). Find where `mission_slug` is obtained and extract `mission_id` from the same source.
2. Look at the function's caller chain to identify where `mission_id` is available. It may need to be threaded through as a parameter to the function.
3. Add `mission_id=mission_id` to the `emit_mission_origin_bound` call.

**Investigation needed**: Trace the call stack to find where `mission_id` is available. The function likely has access to `meta.json` data since it knows the `mission_slug`. Check for a `meta` dict in scope or a `feature_dir` that can be used to load it.

### Subtask T011: Update docstrings in all modified methods

**Files**: `src/specify_cli/sync/emitter.py`, `src/specify_cli/sync/events.py`

**Changes for each method**:
1. Remove references to "backward compat", "drift window", and optional `mission_id` semantics
2. Update to reflect that `mission_id` is the mandatory aggregate identity
3. Remove phrases like "when provided" or "when present" for `mission_id` — it is always present
4. Keep `mission_slug` described as "human display string"

## Definition of Done

- [ ] All three emitter methods require `mission_id: str` (not `str | None`)
- [ ] No `effective_aggregate_id` variable exists in `emitter.py`
- [ ] Both wrapper functions in `events.py` accept and forward `mission_id: str`
- [ ] `mission_creation.py` passes `mission_id` without `get()` fallback
- [ ] `tracker/origin.py` passes `mission_id` to `emit_mission_origin_bound`
- [ ] All docstrings updated — no drift-window or backward-compat references
- [ ] `mypy --strict` passes for all modified files

## Risks

- **Medium**: Changing function signatures from optional to mandatory can break callers not identified in the audit. The audit found all production call sites, but test files may also call these methods directly — verify with grep.
- **T010 investigation**: The `origin.py` caller may need `mission_id` threaded through from a higher call frame. This is the most complex subtask.

## Reviewer Guidance

- Verify every call site for the three emitter methods compiles (mypy) and passes `mission_id`
- Verify `aggregate_id` in `_emit()` calls is always `mission_id`, never `mission_slug`
- Check that test call sites (if any) also pass `mission_id` — they may need updating in WP03

## Activity Log

- 2026-04-13T05:24:30Z – claude:opus:implementer:implementer – shell_pid=71359 – Started implementation via action command
- 2026-04-13T05:31:03Z – claude:opus:implementer:implementer – shell_pid=71359 – Ready for review
- 2026-04-13T05:31:27Z – claude:opus:reviewer:reviewer – shell_pid=80162 – Started review via action command
- 2026-04-13T05:33:17Z – claude:opus:reviewer:reviewer – shell_pid=80162 – Review passed: All three emitter methods now require mission_id: str (mandatory). effective_aggregate_id fully removed. Both events.py wrappers accept and forward mission_id. mission_creation.py uses meta[mission_id] (no get fallback). tracker/origin.py extracts mission_id from meta with guard and passes to emit_mission_origin_bound. All docstrings cleaned. No out-of-scope changes. Force: dirty file is gitignored dossier snapshot.

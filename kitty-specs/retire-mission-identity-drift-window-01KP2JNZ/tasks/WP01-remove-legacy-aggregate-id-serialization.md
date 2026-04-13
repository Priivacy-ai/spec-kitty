---
work_package_id: WP01
title: Remove legacy_aggregate_id from StatusEvent serialization
dependencies: []
requirement_refs:
- FR-001
- FR-008
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
history:
- at: '2026-04-13T04:59:36Z'
  by: spec-kitty.tasks
  note: WP created during task generation
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/models.py
- src/specify_cli/status/emit.py
tags: []
---

# WP01: Remove legacy_aggregate_id from StatusEvent serialization

## Objective

Remove the `legacy_aggregate_id` drift-window compatibility field from `StatusEvent.to_dict()` and clean up related docstrings and comments in the status package. After this WP, new status events will no longer emit `legacy_aggregate_id`.

## Context

The `legacy_aggregate_id` field was added as a drift-window shim (T025 in mission 083) so that downstream SaaS consumers indexing by `mission_slug` could still find events during the transition to `mission_id` (ULID) as the canonical identity. The SaaS side has completed its migration to `mission_id` (`spec-kitty-saas#66`), so this field is now dead code.

**Constraint C-002**: The `mission_id: str | None = None` field on the `StatusEvent` dataclass must remain optional because legacy events on disk (written before the identity migration) lack `mission_id`. Only the *write path* changes — read tolerance is preserved.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`. Do not create branches or worktrees manually.

## Implementation

### Subtask T001: Remove legacy_aggregate_id emission from to_dict()

**Purpose**: Stop emitting the `legacy_aggregate_id` field when serializing new status events.

**File**: `src/specify_cli/status/models.py`

**Current code** (lines 218-224):
```python
if self.mission_id is not None:
    d["mission_id"] = self.mission_id
    # Drift-window shim (T025): legacy_aggregate_id carries mission_slug
    # so downstream SaaS consumers that index by slug can still find events.
    # Remove after SaaS side migrates to mission_id (tracked in WP12).
    d["legacy_aggregate_id"] = self.mission_slug
return d
```

**Target code**:
```python
if self.mission_id is not None:
    d["mission_id"] = self.mission_id
return d
```

**Steps**:
1. Open `src/specify_cli/status/models.py`
2. Locate the `to_dict()` method in the `StatusEvent` dataclass
3. Remove lines 220-223 (the drift-window comment and `legacy_aggregate_id` assignment)
4. Keep the `if self.mission_id is not None: d["mission_id"] = self.mission_id` guard — it is still needed for events that carry `mission_id`
5. Do NOT remove the `mission_id` field from the dataclass — it must stay `str | None` for legacy read tolerance (C-002)

**Validation**:
- `legacy_aggregate_id` does not appear in `to_dict()` output when `mission_id` is set
- `mission_id` still appears in `to_dict()` output when set
- `mission_id` is still absent from `to_dict()` output for legacy events (where `mission_id is None`)

### Subtask T002: Update StatusEvent docstring

**Purpose**: Remove the drift-window field documentation from the `StatusEvent` class docstring.

**File**: `src/specify_cli/status/models.py`

**Current docstring excerpt** (lines 175-183):
```python
    Wire-format evolution (FR-023, ADR 2026-04-09-1):
    - Legacy events: carry only ``mission_slug`` for mission identity.
    - New events (post-WP05): carry both ``mission_slug`` AND ``mission_id``
      (the ULID from meta.json).  ``mission_id`` becomes the canonical
      machine-facing identity; ``mission_slug`` is retained for human
      readability and backward compatibility.
    - ``legacy_aggregate_id``: drift-window compat field, equals ``mission_slug``
      on new writes, absent on legacy events.  Readers ignore it.
```

**Steps**:
1. Remove the `legacy_aggregate_id` bullet entirely (lines 181-182)
2. Update the description to reflect the final state: `mission_id` is the canonical identity, `mission_slug` is human-readable, no compatibility shim remains
3. Keep the legacy/new event distinction — legacy events still lack `mission_id` on disk

### Subtask T003: Remove T025 comment in emit.py

**Purpose**: Remove the comment referencing the drift-window shim in the emit module.

**File**: `src/specify_cli/status/emit.py`

**Current code** (lines 384-386):
```python
    # T023: New events carry mission_id alongside mission_slug.
    # T025: to_dict() emits legacy_aggregate_id=mission_slug as a drift-window
    # compatibility shim for downstream SaaS consumers (removable after WP12).
```

**Steps**:
1. Remove lines 385-386 (the T025 comment about `legacy_aggregate_id`)
2. Keep the T023 comment on line 384 — it is still accurate (new events carry `mission_id`)

## Definition of Done

- [ ] `StatusEvent.to_dict()` no longer emits `legacy_aggregate_id`
- [ ] `mission_id` is still emitted when present
- [ ] Legacy events (no `mission_id`) still serialize correctly
- [ ] Docstring updated — no drift-window references
- [ ] T025 comment removed from `emit.py`
- [ ] `mypy --strict` passes for modified files

## Risks

- **Low**: This is a 4-line deletion with a docstring update. The only risk is if downstream code reads `legacy_aggregate_id` from the serialized dict — but that's the SaaS side (confirmed migrated via C-001).

## Reviewer Guidance

- Verify that `to_dict()` still conditionally emits `mission_id` (the `if self.mission_id is not None` guard must remain)
- Verify the dataclass field `mission_id: str | None = None` is untouched
- Verify no other code in `src/specify_cli/status/` references `legacy_aggregate_id`

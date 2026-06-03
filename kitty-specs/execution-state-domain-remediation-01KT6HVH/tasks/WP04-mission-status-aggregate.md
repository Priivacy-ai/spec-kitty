---
work_package_id: WP04
title: MissionStatus Aggregate — Mission Management Domain
dependencies:
- WP02
requirement_refs:
- FR-015
- FR-016
- FR-017
- FR-018
- FR-019
- FR-020
- FR-021
- FR-022
- FR-023
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-execution-state-domain-remediation-01KT6HVH
base_commit: 24a9a43e0bb553e9a6c4a2a242a7bfc89247eed8
created_at: '2026-06-03T12:05:54.419299+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
- T024
- T025
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "66364"
history:
- date: '2026-06-03'
  event: created
  author: spec-kitty
agent_profile: python-pedro
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/status/__init__.py
- src/specify_cli/cli/commands/agent/status.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load` and specify profile `python-pedro` before reading further.

---

## Objective

Introduce `MissionStatus` as the authoritative read/write owner of mission WP lane state within the Mission Management domain. Migrate `cli/commands/agent/status.py` from raw path construction to `MissionStatus.load().claim()`.

## Branch Strategy

- **Planning base**: `main` | **Merge target**: `main`
- **Prerequisite**: WP02 (e2e ratchet) must be merged and green
- Start with: `spec-kitty agent action implement WP04 --agent claude`

## Context

Currently `cli/commands/agent/status.py` hardcodes:
```python
status_dir = main_repo_root / "kitty-specs" / mission_slug
```
This bypasses both the coord-aware resolver and the `status/` facade. After this WP, it becomes:
```python
ms = MissionStatus.load(repo_root=main_repo_root, mission_slug=mission_slug)
wp_status = ms.claim(wp_id)
lane = wp_status.current_lane
```

**Key constraint (C-004)**: `BookkeepingTransaction` internals in `coordination/transaction.py` must NOT be changed. `MissionStatus` calls it internally.

**Key constraint**: `MissionStatus` does NOT replace `BookkeepingTransaction`. It wraps it.

**Existing code to reuse**:
- `status/__init__.py` exports: `read_events`, `reduce`, `materialize`, `get_wp_lane`, `emit_status_transition`
- `status/transitions.py`: `validate_transition`, `resolve_lane_alias`
- `status/models.py`: `Lane`, `StatusEvent`, `TransitionRequest`
- `coordination/transaction.py`: `BookkeepingTransaction.acquire()`
- `coordination/types.py`: `CommitReceipt` (return type of `save()`)
- `coordination/status_transition.py`: `emit_status_transition_transactional` (becomes implementation of `transition()`)
- `missions/_resolve_planning_branch.py`, `workspace/root_resolver.py`: topology resolution

---

## Subtask T018 — Create aggregate.py: ActiveWPStatus

**File**: `src/specify_cli/status/aggregate.py` (new)

**Steps**:
1. Create the file with `ActiveWPStatus` as a frozen dataclass:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass
   from pathlib import Path
   from typing import Literal

   from specify_cli.status import Lane, StatusEvent, TransitionRequest
   from specify_cli.coordination.types import CommitReceipt

   @dataclass(frozen=True)
   class ActiveWPStatus:
       """Current lane state for a single WorkPackage within a Mission (read projection)."""
       wp_id: str
       current_lane: Lane
       last_event: StatusEvent | None
   ```

2. Do NOT yet create `MissionStatus` — that is T019. Keep `ActiveWPStatus` simple.

**Validation**: `from specify_cli.status.aggregate import ActiveWPStatus` works without errors.

---

## Subtask T019 — Implement MissionStatus.load()

**Purpose**: Implement the aggregate root with topology-aware resolution. `load()` is the most critical method.

**Steps**:
1. In `aggregate.py`, define `MissionStatus`:
   ```python
   @dataclass(frozen=True)
   class MissionStatus:
       mission_slug: str
       mission_id: str | None
       mid8: str           # first 8 chars of mission_id, or "" if None
       topology: Literal["legacy", "coordination"]
       read_dir: Path      # authoritative status directory

       @classmethod
       def load(cls, repo_root: Path, mission_slug: str) -> "MissionStatus":
           """Resolve topology once and return the authoritative status aggregate."""
           ...
   ```

2. Implement `load()`:
   - Read `meta.json` from `repo_root / "kitty-specs" / mission_slug / "meta.json"` to get `mission_id`
   - Determine topology: check if a coordination branch exists for this mission (use `missions/_resolve_planning_branch.py` or equivalent — grep the codebase for how other callers detect coord-topology)
   - For `legacy` topology: `read_dir = repo_root / "kitty-specs" / mission_slug`
   - For `coordination` topology: `read_dir = <coord_branch_checkout_path>`. If the coord path is unavailable, raise `CoordAuthorityUnavailable` — **do NOT fall back to legacy path** (fail-closed)
   - Compute `mid8 = mission_id[:8] if mission_id else ""`
   - Return `cls(mission_slug=..., mission_id=..., mid8=..., topology=..., read_dir=...)`

3. Define `CoordAuthorityUnavailable(RuntimeError)` in `aggregate.py`

**Topology detection approach**: Search the codebase for how coord-topology is detected elsewhere:
```bash
grep -rn "coord\|coordination.*branch\|topology" src/specify_cli/missions/ src/specify_cli/workspace/ --include="*.py" | head -30
```
Use the same detection pattern.

**Validation**: `MissionStatus.load(repo_root, slug)` returns correct topology for:
- A mission with no coordination branch → `topology="legacy"`
- A mission with a coordination branch → `topology="coordination"`

---

## Subtask T020 — Implement MissionStatus.claim()

**Purpose**: Return the current lane state for a WP from the coord-aware read path.

**Steps**:
1. Implement `claim()` in `MissionStatus`:
   ```python
   def claim(self, wp_id: str) -> ActiveWPStatus:
       """Return the current lane state for a WP from the coord-aware read path."""
       from specify_cli.status import get_wp_lane, read_events

       events = read_events(self.read_dir)
       current_lane = get_wp_lane(self.read_dir, wp_id)
       # Get the last event for this WP
       wp_events = [e for e in events if e.wp_id == wp_id]
       last_event = wp_events[-1] if wp_events else None
       return ActiveWPStatus(
           wp_id=wp_id,
           current_lane=current_lane,
           last_event=last_event,
       )
   ```

2. Note: `read_events` and `get_wp_lane` are already in `status/__init__.py` — import from the facade, not from submodules.

**Validation**: `ms.claim("WP01").current_lane` returns the correct lane for test fixtures.

---

## Subtask T021 — Implement MissionStatus.transition()

**Purpose**: Validate and apply a lane transition, calling `BookkeepingTransaction` internally.

**Steps**:
1. Implement `transition()` in `MissionStatus`:
   ```python
   def transition(self, request: TransitionRequest) -> StatusEvent:
       """Validate and apply a lane transition via BookkeepingTransaction internally."""
       from specify_cli.status import validate_transition
       from specify_cli.coordination.status_transition import emit_status_transition_transactional

       # Validate the transition first (domain invariant — does not belong in BookkeepingTransaction)
       ok, error = validate_transition(request.from_lane, request.to_lane, actor=request.actor)
       if not ok:
           from specify_cli.status import InvalidTransitionError
           raise InvalidTransitionError(error)

       # Apply via the transactional path (calls BookkeepingTransaction internally)
       return emit_status_transition_transactional(
           feature_dir=self.read_dir,
           feature_slug=self.mission_slug,
           wp_id=request.wp_id,
           to_lane=request.to_lane,
           actor=request.actor,
       )
   ```

2. If `emit_status_transition_transactional` signature differs, grep for its actual signature:
   ```bash
   grep -n "def emit_status_transition_transactional" src/specify_cli/coordination/status_transition.py
   ```

**Validation**: `ms.transition(request)` applies the transition and returns a `StatusEvent`.

---

## Subtask T022 — Implement MissionStatus.save()

**Purpose**: Persist staged transitions via `BookkeepingTransaction`.

**Steps**:
1. Implement `save()` in `MissionStatus`:
   ```python
   def save(self, *, operation: str) -> CommitReceipt:
       """Persist staged transitions via BookkeepingTransaction."""
       from specify_cli.coordination.transaction import BookkeepingTransaction

       with BookkeepingTransaction.acquire(self.read_dir, operation=operation) as txn:
           return txn.commit()
   ```

2. Verify `BookkeepingTransaction.acquire()` signature and `CommitReceipt` import. Do NOT change `BookkeepingTransaction` internals (C-004).

**Validation**: `ms.save(operation="test")` returns a `CommitReceipt` without modifying `coordination/transaction.py`.

---

## Subtask T023 — Export MissionStatus + ActiveWPStatus in __init__.py

**Purpose**: Add `MissionStatus`, `ActiveWPStatus`, and `CoordAuthorityUnavailable` to `status/__init__.py`'s `__all__`.

**Steps**:
1. Open `src/specify_cli/status/__init__.py`
2. Find the `__all__` list (currently ~35 symbols)
3. Add at the appropriate alphabetical position:
   ```python
   from specify_cli.status.aggregate import (
       ActiveWPStatus,
       CoordAuthorityUnavailable,
       MissionStatus,
   )
   ```
4. Add all three to `__all__`

**Validation**: `from specify_cli.status import MissionStatus, ActiveWPStatus, CoordAuthorityUnavailable` works.

---

## Subtask T024 — Migrate agent/status.py

**Purpose**: Replace the raw path construction in `cli/commands/agent/status.py` with `MissionStatus.load()` + `claim()`.

**Steps**:
1. Read `src/specify_cli/cli/commands/agent/status.py` in full
2. Find the line(s) that construct `status_dir = main_repo_root / "kitty-specs" / mission_slug`
3. Replace with:
   ```python
   from specify_cli.status import MissionStatus

   ms = MissionStatus.load(repo_root=main_repo_root, mission_slug=mission_slug)
   wp_status = ms.claim(wp_id)
   lane = wp_status.current_lane
   ```
4. Adjust surrounding logic as needed (the function may pass `status_dir` into other calls — those need to use `ms.read_dir` instead)
5. Run `pytest tests/ -x` to confirm no regressions

**Validation**: `grep -n 'main_repo_root.*kitty-specs\|kitty-specs.*mission_slug' src/specify_cli/cli/commands/agent/status.py` returns zero hits.

---

## Subtask T025 — Write Unit Tests

**Purpose**: Unit tests for `MissionStatus` covering load, claim, topology, and fail-closed behavior.

**Steps**:
1. Create or extend `tests/unit/status/test_mission_status_aggregate.py` (or follow existing test file naming)
2. Tests to write:
   ```python
   def test_load_legacy_mission(tmp_path):
       # Setup: mission dir without coordination branch
       # Assert: topology="legacy", read_dir=repo_root/"kitty-specs"/slug

   def test_load_coord_mission(tmp_path):
       # Setup: mission with coordination branch
       # Assert: topology="coordination", read_dir=coord_path

   def test_load_coord_unavailable_fails_closed(tmp_path):
       # Setup: coord-topology mission but coord path missing
       # Assert: raises CoordAuthorityUnavailable (not falls back to legacy)

   def test_claim_returns_correct_lane(tmp_path):
       # Setup: mission with WP01 in "in_progress" lane
       # Assert: ms.claim("WP01").current_lane == Lane.in_progress

   def test_active_wp_status_fields(tmp_path):
       # Assert: ActiveWPStatus has wp_id, current_lane, last_event
   ```

**Validation**: All unit tests pass. `pytest tests/ -x -k "mission_status"` is green.

---

## Definition of Done

- [ ] `src/specify_cli/status/aggregate.py` exists with `ActiveWPStatus`, `MissionStatus`, `CoordAuthorityUnavailable`
- [ ] `MissionStatus.load()` resolves topology correctly for both legacy and coord missions
- [ ] `MissionStatus.load()` fails closed (raises `CoordAuthorityUnavailable`) when coord path unavailable
- [ ] `MissionStatus.claim()` returns `ActiveWPStatus` with correct lane
- [ ] `MissionStatus.transition()` calls `BookkeepingTransaction` internally (not exposed to callers)
- [ ] `MissionStatus.save()` returns `CommitReceipt`
- [ ] `status/__init__.py` exports `MissionStatus`, `ActiveWPStatus`, `CoordAuthorityUnavailable`
- [ ] `agent/status.py` contains no raw `main_repo_root / "kitty-specs"` construction
- [ ] Unit tests pass
- [ ] e2e ratchet (WP02) still green
- [ ] `BookkeepingTransaction` internals unchanged (verify: `git diff src/specify_cli/coordination/transaction.py` is empty)

## Risks

- Topology detection logic may not have a single canonical source — grep broadly before writing `load()`
- `emit_status_transition_transactional` signature may differ from expected — check before using
- `agent/status.py` may pass `status_dir` to many downstream calls — each must be updated to use `ms.read_dir`

## Reviewer Guidance

- Verify `BookkeepingTransaction` in `coordination/transaction.py` is UNCHANGED
- Verify `topology="coordination"` raises `CoordAuthorityUnavailable` when coord dir missing (not falls back)
- Check that `agent/status.py` zero raw path constructions remain
- Confirm `MissionStatus` and `ActiveWPStatus` appear in `status/__init__.py.__all__`

## Activity Log

- 2026-06-03T12:05:56Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=66364 – Assigned agent via action command
- 2026-06-03T12:23:59Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=66364 – Implementation complete. Lint: exit 0. Tests: 1038 passed (2 pre-existing failures in test_context_validation_unit.py unrelated to this WP; dead_modules pre-existing failure for m_3_2_0rc35_spk_skill_pack also pre-existing). aggregate.py is properly wired via __init__.py and no longer dead. coordination/transaction.py unchanged (C-004 verified).

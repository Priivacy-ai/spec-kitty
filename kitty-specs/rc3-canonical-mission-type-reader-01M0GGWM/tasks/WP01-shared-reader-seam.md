---
work_package_id: WP01
title: Shared canonical reader seam + M3↔M5 reconciliation + red gate
dependencies: []
requirement_refs:
- FR-001
- FR-004
- FR-010
planning_base_branch: rc3-canonical-mission-type-reader-01M0GGWM
merge_target_branch: rc3-canonical-mission-type-reader-01M0GGWM
branch_strategy: Planning artifacts for this mission were generated on rc3-canonical-mission-type-reader-01M0GGWM. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-canonical-mission-type-reader-01M0GGWM unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
history:
- at: '2026-08-22T04:16:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_read_mission_type.py
- tests/architectural/test_mission_type_reader_invariants.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/mission_type_key.py
- src/charter/mission_type_profiles.py
- src/specify_cli/mission.py
- tests/charter/test_read_mission_type.py
- tests/architectural/test_mission_type_reader_invariants.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Shared canonical reader seam + M3↔M5 reconciliation + red gate

## Objectives & Success Criteria

- Introduce **`read_mission_type(meta: dict) -> str | None`** beside
  `canonical_mission_type_key` in `src/charter/mission_type_key.py` — reads the
  canonical `mission_type` field → `canonical_mission_type_key` → `None`. **No
  legacy `mission` fallback. No `software-dev` default.** (FR-001, FR-004.)
- Collapse `_canonical_meta_mission_type` (`src/specify_cli/mission.py:542`) to a
  thin delegate to the seam, **dropping its legacy `mission` read** (FR-002).
- Make the charter read path (`_read_meta_mission_type` / `_resolve_type_key` in
  `src/charter/mission_type_profiles.py`) delegate its field-extract+canon to the
  shared seam — the load-bearing **M3↔M5 reconciliation** so the two readers
  cannot re-diverge. This is behavior-parity (the charter path is already
  canonical-only after M3), not a behavior change.
- Author the **FR-010 structural invariant test** (`tests/architectural/`) RED:
  a table of in-scope readers asserting each equals `read_mission_type(meta)`,
  plus a source-scan asserting no in-scope module carries a `software-dev`
  fallback or a legacy `mission` read (with an encoded, rationale-carrying
  allow-list path — tolerate the file being absent as empty until WP03 creates it).

## Context & Constraints

- Charter: `.kittify/charter/charter.md`; plan: `../plan.md`; census: `../research.md`.
- **Layer rule (C-001):** `charter` must not import `specify_cli`
  (`tests/architectural/test_layer_rules.py`). The seam lives in `charter/` so
  both layers import it downward — verify AC-4 stays green.
- `canonical_mission_type_key` is reused **as-is** (pure, no default, strip-only).
  Do not re-derive normalization.
- File I/O stays per-reader — the seam is **dict-in**. `_read_meta_mission_type`
  keeps its own `meta.json` load, then delegates the field read to the seam.
- Keep `__all__` correct on `mission_type_key.py` (dead-symbol gate). New test
  files need a `pytestmark`; avoid bare `len(x) == N` (golden-count-ban).

## Branch Strategy

- **Merge target branch**: `rc3-canonical-mission-type-reader-01M0GGWM`
- Populated by `finalize-tasks`; do not edit manually.

## Subtasks & Detailed Guidance

### Subtask T001 – Add the `read_mission_type` seam
- **Steps**: In `src/charter/mission_type_key.py`, add `read_mission_type(meta: dict[str, Any]) -> str | None` returning `canonical_mission_type_key(meta.get("mission_type") if isinstance(meta.get("mission_type"), str) else None)`. Export in `__all__`.
- **Files**: `src/charter/mission_type_key.py`.

### Subtask T002 – Seam unit table
- **Steps**: `tests/charter/test_read_mission_type.py` — canonical value, whitespace, blank→None, absent→None, non-string→None, and **legacy-only `{"mission": "software-dev"}` → None** (the retirement pin).
- **Files**: `tests/charter/test_read_mission_type.py` (create).

### Subtask T003 – `_canonical_meta_mission_type` → delegate
- **Steps**: Replace the `("mission_type", "mission")` loop at `mission.py:542` with `return read_mission_type(meta)`. Confirm `get_mission_type` (returns `... or ""`) still behaves at its boundary.
- **Files**: `src/specify_cli/mission.py`.

### Subtask T004 – Charter path delegates to the seam
- **Steps**: Refactor `_resolve_type_key`/`_read_meta_mission_type` so the raw-field-read + canon go through `read_mission_type(data)` after the file load. Pin byte-parity vs. current output for canonical, blank, absent, malformed inputs.
- **Files**: `src/charter/mission_type_profiles.py`.

### Subtask T005 [P] – FR-010 structural invariant test (RED first)
- **Steps**: `tests/architectural/test_mission_type_reader_invariants.py`: (a) table-driven parity — enumerate every in-scope reader (dict-in adapters) and assert `== read_mission_type(meta)` across a shared fixture matrix; (b) source-scan each in-scope module for a `software-dev` mission-type fallback / legacy `mission` read, consulting an encoded allow-list (`tests/architectural/inline_meta_read_allowlist.yaml`, treat-absent-as-empty). Author RED — it fails against the not-yet-converted readers in WP02/WP03.
- **Files**: `tests/architectural/test_mission_type_reader_invariants.py` (create).

### Subtask T006 [P] – Layer rules stay green
- **Steps**: Run `pytest tests/architectural/test_layer_rules.py::test_charter_does_not_import_specify_cli`.

## Test Strategy

- `pytest tests/charter/test_read_mission_type.py tests/architectural/test_mission_type_reader_invariants.py tests/architectural/test_layer_rules.py -q`
- T005 is expected RED until WP02/WP03 land; T002/T004/T006 green in this WP.

## Risks & Mitigations

- Charter path is already canonical-only (M3) → parity refactor; pin byte-parity.
- Seam must stay pure/dict-in; do not add I/O.

## Review Guidance

- Seam has no default and no legacy read; `__all__` updated; layer test green; FR-010 test genuinely exercises every reader (not a stub).

## Activity Log

- 2026-08-22T04:16:17Z – system – Prompt created.

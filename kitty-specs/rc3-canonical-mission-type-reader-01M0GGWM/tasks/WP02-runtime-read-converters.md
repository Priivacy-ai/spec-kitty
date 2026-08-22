---
work_package_id: WP02
title: Runtime READ converters — legacy + default drop
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-005
- FR-006
planning_base_branch: rc3-canonical-mission-type-reader-01M0GGWM
merge_target_branch: rc3-canonical-mission-type-reader-01M0GGWM
branch_strategy: Planning artifacts for this mission were generated on rc3-canonical-mission-type-reader-01M0GGWM. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into rc3-canonical-mission-type-reader-01M0GGWM unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 2 - Convergence
history:
- at: '2026-08-22T04:16:17Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
create_intent:
- tests/specify_cli/test_mission_type_read_converters.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dashboard/handlers/features.py
- src/specify_cli/dashboard/diagnostics.py
- src/specify_cli/mission_metadata.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/retrospective/reader.py
- src/specify_cli/retrospective/writer.py
- src/specify_cli/context/resolver.py
- src/specify_cli/verify_enhanced.py
- tests/specify_cli/test_mission_type_read_converters.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Runtime READ converters — legacy + default drop

## Objectives & Success Criteria

- Route every in-scope runtime **read** through `read_mission_type` (WP01),
  dropping legacy `mission` and the silent `software-dev` default. One reader per
  test-pinned step (FR-002, FR-003, FR-006).
- **FR-005 visible change**: `dashboard/handlers/features.py` reads the canonical
  field via the helper — `{"mission_type":"research"}` shows `research`;
  `{"mission":"software-dev"}`-only shows typeless (AC-1 dashboard pin).
- Each converted reader returns exactly `read_mission_type(meta)` for the same
  dict → the FR-010 parity rows go green.

## Context & Constraints

- Depends on **WP01** (the seam). Load: `../plan.md` (IC-03), `../research.md`
  (re-grounded census — the READ-path rows).
- **Caller boundaries**: some callers expected a concrete `software-dev` default;
  each converter must confirm the caller degrades on typeless (`None`/`""`). The
  `get_mission_type(...) -> ... or ""` precedent shows the neutral pattern.
- **Same-file cross-mission coordination**: `retrospective/generator.py` — own
  **only** the mission-type reader at `:1319`; **M8** owns the read-side degrade
  at `:271` (different lines). Do not touch `:271`.
- `mission_metadata.py`: convert the **read** path (`:255`), classify the
  **build/create** path (`:216`) as a write-boundary (create-time default is
  retained; document it inline — it is not a runtime meta read).

## Branch Strategy

- **Merge target branch**: `rc3-canonical-mission-type-reader-01M0GGWM`

## Subtasks & Detailed Guidance

### Subtask T007 – Dashboard features → helper (FR-005)
- **Steps**: Replace `meta.get("mission", "software-dev")` at `features.py:68` with the helper; handle typeless (`Unknown (…)` / neutral). Regression pin: `research` shown; legacy-only → typeless.

### Subtask T008 [P] – mission_metadata read/build
- **Steps**: `:255` → `read_mission_type(meta)` (drop `or meta.get("mission")`, drop `or "software-dev"`); ensure the caller tolerates typeless. Leave `:216` build-path default; add an inline note that it is a create-time writer, not a reader.

### Subtask T009 [P] – retrospective/generator :1319
- **Steps**: `str(meta.get("mission_type") or "software-dev")` → helper; drop the default. Touch only `:1319`.

### Subtask T010 [P] – context/resolver :94
- **Steps**: `data.get("mission_type") or data.get("mission") or ""` → helper; drop legacy read (default already neutral `None`).

### Subtask T011 [P] – verify_enhanced :28/31
- **Steps**: Collapse the two-field read to the helper; drop the `legacy_mission` branch.

### Subtask T012 [P] – dashboard/diagnostics :31/34
- **Steps**: Same shape as verify_enhanced — collapse to the helper; drop the legacy branch.

### Subtask T013 [P] – retrospective reader/writer parity
- **Steps**: `reader.py:312` & `writer.py:408` read `mission_type` with `""` default — already canonical-only; route through the helper for shared-authority parity (preserve `""`-neutral at the record boundary).

### Subtask T014 – Per-reader regression pins
- **Steps**: `tests/specify_cli/test_mission_type_read_converters.py` — one focused case per converter (T007–T013), including the dashboard visible-change pins and legacy-only→typeless.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/test_mission_type_read_converters.py -q`
- Re-run the FR-010 gate: its parity rows for these readers must now be green.

## Risks & Mitigations

- Typeless-intolerant caller → inspect each caller's degrade path before converting.
- Dashboard/retrospective are user-visible → changelog lines land in WP05.

## Review Guidance

- No legacy `mission` read and no `software-dev` default remains in any converted reader; build/create writers are documented, not accidentally converged; `:271` untouched.

## Activity Log

- 2026-08-22T04:16:17Z – system – Prompt created.

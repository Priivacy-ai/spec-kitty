---
work_package_id: WP03
title: Pydantic Response Models
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-019
- NFR-006
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: python-pedro
authoritative_surface: src/dashboard/api/models.py
execution_mode: code_change
owned_files:
- src/dashboard/api/models.py
- tests/test_dashboard/test_typeddict_pydantic_parity.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Define every Pydantic v2 response model the FastAPI routers will need. Maintain shape parity with the existing TypedDicts in `src/dashboard/api_types.py` so existing consumers keep working.

## Subtasks

### T011 — `src/dashboard/api/models.py`

For every TypedDict in `src/dashboard/api_types.py`, declare an equivalent Pydantic v2 `BaseModel`. See `data-model.md` for the canonical mapping. Mirror field names exactly. `Optional[T]` becomes `T | None = None`.

### T012 — Discriminated union for `SyncTriggerResponse`

Four-variant union (Scheduled, Skipped, Unavailable, Failed). `SyncTriggerResult.body()` already produces the right dict per status — the Pydantic models just give FastAPI a type to declare on `response_model=`.

### T013 — Adapter test `tests/test_dashboard/test_typeddict_pydantic_parity.py`

For each TypedDict, write a literal that satisfies its shape; instantiate the equivalent Pydantic model via `Model.model_validate(literal)`; assert `model.model_dump_json(sort_keys=True) == json.dumps(literal, sort_keys=True)`.

## Definition of Done

- [ ] Every TypedDict in `src/dashboard/api_types.py` has a Pydantic equivalent.
- [ ] Parity test passes for every model.
- [ ] No new `# type: ignore` directives.
- [ ] No `Any` in route-handler-facing types (NFR-006).

## Reviewer guidance

- Confirm field names and types match the TypedDict source.
- Confirm `from __future__ import annotations` is set so forward references work cleanly.
- Confirm the discriminated union uses `Literal[...]` discriminators where applicable.

## Risks

- TypedDict uses `Dict[str, Any]` for unbounded shapes (e.g., `KanbanResponse.lanes`); Pydantic preserves this with `dict[str, list[Any]]` — accept the `Any` here, this is the only place it's tolerated.

## Activity Log

- 2026-05-02T20:12:13Z – claude – Moved to claimed
- 2026-05-02T20:12:16Z – claude – Moved to in_progress
- 2026-05-02T20:15:39Z – claude – Moved to for_review
- 2026-05-02T20:15:42Z – claude – Moved to in_review
- 2026-05-02T20:15:46Z – claude – Moved to approved
- 2026-05-02T20:15:49Z – claude – Done override: Lane-less mission run on the parent feature/650-dashboard-ui-ux-overhaul branch

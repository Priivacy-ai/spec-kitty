---
work_package_id: WP09
title: Dead-symbol deletion (status_service)
dependencies:
- WP02
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
phase: Phase 3 - Cleanup
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3763005"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/coordination/status_service.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/status_service.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Dead-symbol deletion

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/coordination/status_service.py`.

---

## Objectives & Success Criteria
- Delete the 5 dead symbols in `coordination/status_service.py` (#1622/#391): `EventLogWriteTarget`, `StatusContractError`, `StatusReadSource`, `append_event_log_batch`, `read_wp_lane_actor`.
- **Strangler-ordered** (C-004): delete only AFTER WP02 has consumers on the facade and zero live callers remain.
- **Done when:** grep shows zero live callers; symbols removed; suite + `tests/architectural/` green; net LOC down (NFR-005).

## Context & Constraints
- Design: `spec.md` FR-013; `plan.md` IC-09; `research.md` R-B (confirmed 5 dead symbols).
- Do NOT migrate these symbols — they are pre-facade scaffolding. If the whole file becomes empty, delete the file and drop its `__init__` export.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T029 — Confirm zero live callers
- `rg -n "EventLogWriteTarget|StatusContractError|StatusReadSource|append_event_log_batch|read_wp_lane_actor" src tests` — expect only the definitions + this file's own references. Confirm at deletion time (not plan time).
### T030 — Delete the 5 symbols (strangler-ordered)
- Remove the symbols; update `__all__`/exports; run full suite + `tests/architectural/`.

## Test Strategy
- Full suite + architectural tests green after deletion; `ruff`+`mypy` zero issues (no unused-import residue).

## Risks & Mitigations
- *Hidden dynamic caller* → grep tests + string references; rely on import-time + type-check failures.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm zero callers before approving; confirm LOC subtraction.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T20:26:00Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Assigned agent via action command
- 2026-06-09T20:34:25Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Dead-symbol burn-down (#1622/#391). T029 zero-caller proof: rg over src+tests shows NO external src/ importer of any of the 5 symbols. 2 truly-dead (append_event_log_batch, read_wp_lane_actor) had zero callers anywhere -> DELETED. 3 (StatusReadSource, EventLogWriteTarget, StatusContractError) are load-bearing internals of the kept facade (EventLogReadContract/EventLogWriteContract/read_event_log/append_event_log) + exercised by live tests in test_status_transition.py -> DE-EXPORTED from __all__ (gate's prescribed fix), definitions retained. Removed resolved _CATEGORY_C_UPSTREAM_STATUS_SERVICE allowlist + baselines note. Net -45 LOC. Gates: ruff 0, mypy 0 on changed lines (2 pre-existing no-any-return in untouched read_event_log on base HEAD), 89 coordination+gate tests pass, 317 architectural pass. Commit be932d19a.
- 2026-06-09T20:45:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=3763005 – Started review via action command
- 2026-06-09T20:49:39Z – user – shell_pid=3763005 – Review passed (reviewer-renata): Dead-symbol burn-down sound. 2 truly-dead funcs (append_event_log_batch, read_wp_lane_actor) DELETED — rg over src+tests shows zero callers anywhere (only baselines comment). 3 types (StatusReadSource/EventLogWriteTarget/StatusContractError) DE-EXPORTED not deleted: genuinely load-bearing internals — StatusReadSource/EventLogWriteTarget are the .source/.target field types of the live EventLogReadContract/EventLogWriteContract and drive read_event_log/_validate_write_contract dispatch; StatusContractError is raised by the live read_event_log/append_event_log facade AND imported by live test_status_transition.py. Deleting any of the 3 breaks the live facade + tests. De-export is exactly the dead-symbol gate's prescribed remedy for an orphan-__all__ entry that has internal callers. Deviation justified — only 2 were truly dead; spec/issue-matrix should note this. Gates: 405 coordination+architectural tests pass (incl test_no_dead_symbols + test_ratchet_baselines); ruff 0; the 2 mypy no-any-return at lines 155/177 confirmed pre-existing on base in untouched read_event_log (identical on base file). Net -45 LOC (NFR-005). Scope clean: WP09 commit be932d19a touches only owned status_service.py + justified gate allowlist removal + baselines note. C-004/C-005 upheld. No forbidden terms.

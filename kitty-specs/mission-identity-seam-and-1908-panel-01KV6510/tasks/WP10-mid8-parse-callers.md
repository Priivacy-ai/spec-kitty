---
work_package_id: WP10
title: Route remaining mid8_from_slug parse-callers to resolve_mid8 (#1918 fallout)
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
phase: Phase 2 - Route call sites
assignee: ''
agent: claude
shell_pid: '1073121'
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/test_mid8_caller_routing.py
execution_mode: code_change
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/cli/commands/decision.py
- src/specify_cli/cli/commands/agent/mission.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/agent/context.py
- tests/specify_cli/test_mid8_caller_routing.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Route remaining mid8_from_slug parse-callers

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load` → `python-pedro` (implementer, claude).

---

## Objectives & Success Criteria
WP01 demotes `mid8_from_slug` **in place** to a non-authoritative heuristic (declines on a coincidental
8-char tail with no `mission_id`) and adds an authoritative `resolve_mid8(slug, *, mission_id)`. This
WP closes the **squad-verified blast radius**: audit every remaining `mid8_from_slug` caller in the
files it owns and route the **correctness-path / value-uses** to `resolve_mid8`, leaving pure
boolean-detector uses only where provably correct under the stricter decline. Read [spec.md](../spec.md)
FR-004/FR-001/FR-009. ("Own all callers" — operator decision 2026-06-15.)

**Done when:** no owned file uses `mid8_from_slug`'s *value* on a correctness path (those go through
`resolve_mid8` with the declared `mission_id`); any retained detector-use is justified + regression-
covered; the stricter decline introduces no new fail-close or mis-resolution; tests green.

## Context & Constraints
- **Depends on WP01** (`resolve_mid8` must exist). TDD-first. Only the 6 named files + the new test.
- **Other owners route their own callers** (do NOT touch their files): `runtime_bridge.py`→WP02;
  `orchestrator_api/commands.py` + `agent/tasks.py`→WP05; `acceptance/__init__.py`→WP08;
  `coordination/surface_resolver.py` + `missions/_read_path_resolver.py` + `feature_dir_resolver.py`→WP06.
  This WP owns the remaining six: `status/aggregate.py`, `cli/commands/decision.py`,
  `cli/commands/agent/{mission,workflow,status,context}.py`.
- **Two distinct caller semantics ride `mid8_from_slug`** (the squad's finding): (a) a *boolean
  "does this slug embed a mid8"* detector, and (b) a *value used directly as the resolution mid8*. Only
  (b) must move to `resolve_mid8`; (a) may stay IF the stricter decline doesn't change its answer for
  real inputs — prove that with a test.
- `status/aggregate.py` is the ONLY `status/` file in NFR-001's surface — WP09's NFR-001 diff-scan
  carves it out explicitly. Keep the edit minimal (just the mid8 caller); do NOT touch reducer/store.

## Subtasks
### T041 — Route `status/aggregate.py` (:480/:486) + `cli/commands/decision.py` (:419)
Audit each `mid8_from_slug` use. Value-uses → `resolve_mid8(slug, mission_id=…)` with the declared
`mission_id` in scope (read from meta where needed). Boolean-detector uses → keep only if a test proves
the stricter decline is answer-preserving for real slugs.

### T042 — Route `cli/commands/agent/{mission,workflow,status,context}.py`
Same audit-and-route across the four agent command modules (`mission.py:1229`, `workflow.py:300`,
`status.py:41/51`, `context.py:76`). Prefer the declared `mission_id` (these commands resolve a
mission handle, so `mission_id` is available) → `resolve_mid8`.

### T043 — Tests + gates
Create `tests/specify_cli/test_mid8_caller_routing.py`: for each routed caller, a focused test that
(a) a genuine embedded-mid8 slug resolves correctly via `resolve_mid8`, and (b) a coincidental-8-char
tail no longer mis-resolves (the #1918 win) — i.e. the stricter decline does NOT regress the caller.
`ruff`+`mypy`; `PWHEADLESS=1 pytest tests/specify_cli/test_mid8_caller_routing.py
tests/specify_cli/cli/commands/ -q`.
- [ ] all value-uses in the 6 files routed to `resolve_mid8`; [ ] retained detector-uses justified +
  tested; [ ] no new fail-close / mis-resolution; [ ] aggregate.py edit minimal (no reducer/store
  hunks); [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
The six owned files no longer use the demoted `mid8_from_slug` on a correctness path; value-uses route
through `resolve_mid8`; the stricter decline is regression-proven non-regressing; ruff/mypy clean.

## Reviewer Guidance
Confirm: (1) every value-use is routed to `resolve_mid8` with a declared `mission_id`, not the
heuristic; (2) any kept `mid8_from_slug` call is a true boolean detector with a test proving the
decline doesn't change its real-input answer; (3) `status/aggregate.py` has only the mid8-caller hunk
(no reducer/store creep — NFR-001); (4) tests prove both the embedded-resolves and coincidental-declines
cases per caller.

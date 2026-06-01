---
work_package_id: WP14
title: Wire OperationalContext at runtime entry points
dependencies:
- WP13
requirement_refs:
- FR-017
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts were generated on mission/org-doctrine-profile-integrity-activation-closure. During implement this WP runs in its computed lane; completed changes merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human redirects the landing branch.
subtasks:
- T062
- T063
- T064
- T065
agent: claude
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/runtime_bridge.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/next/runtime_bridge.py
- tests/specify_cli/test_operational_context_wiring.py
role: implementer
tags: []
---

# WP14 — Wire OperationalContext at runtime entry points

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Populate `OperationalContext` at the WP-claim paths and the `next` runtime decision boundary so it is no longer a dead extension point (FR-017), with no worktree/status side-effects on precondition failure (NFR-004). This wiring is the precondition for FR-019 (WP15 prunes the allowlist after this lands).

## Context

- Spec FR-017, NFR-004; research R-011-E (call sites: `implement.py:740`, `agent/workflow.py:1234`, `runtime_bridge.decide_next_via_runtime:1980`; inputs: `--agent`, `_resolve_step_agent_profile`, `step_id`/`mission_state`, claim actor, charter/meta). C-006 safe (these are `specify_cli`).
- Data model §7. Contract C4.1, C4.2.

### Code map

- `src/specify_cli/cli/commands/implement.py:740` (`start_implementation_status` claim), `effective_actor` ~:702.
- `src/specify_cli/cli/commands/agent/workflow.py:1234` (claim), `_actor` ~:1238.
- `src/specify_cli/next/runtime_bridge.py:1980` `decide_next_via_runtime` (already `# noqa: C901`); `_resolve_step_agent_profile` ~:991.
- Builder: `charter.invocation_context.build_operational_context` (WP13).

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. Depends on WP13.

## Subtasks

### T062 — Wire OC at `implement.py` claim

**Steps**: At the claim path, build `OperationalContext` via the WP13 assembler using available inputs (active_model=`--agent`, active_profile via `_resolve_step_agent_profile`, active_role=claim actor, current_activity=`implement`/step, tech_stack from charter/meta). Pass/consume it where the claim needs context. Do not build OC inside the side-effect-free `next/discovery.py`.

**Validation**: - [ ] populated context at the implement claim; no all-None.

### T063 — Wire OC at `agent/workflow.py` claim

**Steps**: Mirror T062 at the workflow claim site, reusing a single shared helper (avoid forking OC-construction logic between the two claim sites).

**Validation**: - [ ] populated context at the workflow claim.

### T064 — Wire OC at `runtime_bridge.decide_next`

**Steps**: Extract a small `_build_operational_context_for_decision(agent, run_ref, feature_dir)` helper (resolving current_activity from `mission_state`/`step_id`, profile via `_resolve_step_agent_profile`) and call the charter builder from it — do NOT inline into the already-`C901` `decide_next_via_runtime`.

**Validation**: - [ ] populated context at the next decision; `decide_next_via_runtime` complexity not increased.

### T065 — Tests

**Steps**: `tests/specify_cli/test_operational_context_wiring.py` — assert populated context (active model/profile/role/activity) at each site; assert NFR-004: an inactive-profile / missing-context precondition failure creates zero new worktree paths and zero new status events.

**Validation**: - [ ] green; NFR-004 observed (no worktree/status on failure).

## Definition of Done

- [ ] OC populated at all three sites via a shared helper; NFR-004 holds; tests green. CC-2 + C-006 (no doctrine→charter inversion) preserved.

## Risks

- `decide_next_via_runtime` is large and complex — extract a helper, do not inline.
- NFR-004: ensure precondition checks run before any worktree/status side-effect.

## Reviewer Guidance (reviewer-renata)

- Confirm all three sites build populated context via the shared helper.
- Confirm NFR-004 (no worktree/status on precondition failure) is actually asserted.
- This must land before WP15 prunes the OC allowlist entries (FR-019 ordering).

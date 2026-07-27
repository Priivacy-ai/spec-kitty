---
work_package_id: WP07
title: StatusSurfaceFragment threading (MissionStatus.load + status_transition)
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T14:50:26.167691+00:00'
subtasks:
- T028
- T029
- T030
phase: Phase 1 - Independent lanes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "92560"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/coordination/status_transition.py
- tests/architectural/test_execution_context_parity.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – StatusSurfaceFragment threading

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Close the latent SC-4 drift (#1821, flagged by the 01KTPKST closeout): two surfaces re-derive the status
surface instead of reading the carried `StatusSurfaceFragment` from the resolved `MissionExecutionContext`.
Both hit the same authority TODAY (correct behavior) — this is **threading, not a behavior change**.
- `MissionStatus.load` consumes a passed/carried `StatusSurfaceFragment` (or the resolved context) instead of hand-rolling its coord-path composition.
- `coordination/status_transition` likewise consumes the fragment instead of re-invoking `resolve_status_surface` locally.
- The 01KTPKST parity ratchet gains an assertion that the fragment IS the source (e.g. a spy/static assertion that no local composition remains).
- **Done when:** parity ratchet (extended) green; grep shows no local coord-path composition in either file.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-005), plan.md (IC-06), contracts/ (C-STAT-1)}` + ticket #1821 + the 01KTPKST closeout notes (`kitty-specs/execution-context-unification-01KTPKST/research/closeout-debugger-debby.md` flagged `MissionStatus.load`'s hand-rolled composition).
- The fragment + `resolve_status_surface` + `resolve_action_context` all exist (01KTPKST). Strangler: keep behavior identical; only the SOURCE of the paths changes.
- Some `MissionStatus.load` callers may lack a resolved context — give `load` an optional `surface:` parameter defaulting to resolving via the canonical helper ONCE (not a re-derivation), so callers thread it progressively. Document the default as the canonical path, not a parallel one.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T028 — `MissionStatus.load`
- Replace the hand-rolled coord-path composition with the fragment/`resolve_status_surface` product; add the optional `surface` parameter; convert direct callers that already hold a context to pass it.

### T029 — `status_transition`
- The WP02-of-01KTPKST work made `_identity_for_request` consume the resolver output; finish the threading: accept/carry the fragment rather than re-invoking the resolver per call where a context exists. Delete the now-dead local composition lines (deletions ledger).

### T030 — Parity ratchet extension
- Extend `tests/architectural/test_execution_context_parity.py` (EXTEND — never fork; C-005) with the fragment-is-the-source assertion: e.g. monkeypatch-spy `resolve_status_surface` and assert call-count/threading shape, or a static `rg`-based architectural test that no `compose.*coord` pattern remains in the two files.

## Definition of Done
- Parity suite green (incl. new assertion); no behavior change (`tests/specify_cli/status` + `tests/specify_cli/coordination` green); `ruff`+`mypy` clean.

## Risks & Mitigations
- *Hidden caller without a context* → the optional-parameter default keeps them working through the SAME canonical helper (no parallel path).

## Review Guidance
- Recommended: **reviewer-renata**. Verify threading (no local composition remains — grep) and that the optional default routes through the canonical helper.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T15:10:44Z – user – shell_pid=38158 – Threaded StatusSurfaceFragment through MissionStatus.load (optional surface= param, consumes canonical resolve_status_surface; deleted hand-rolled CoordinationWorkspace.worktree_path+_compose_mission_dir composition) + status_transition._canonical_primary_feature_dir (consumes new single-pass resolve_status_surface_with_anchor; deleted validate-then-rederive double resolution). #1821 threading, behavior-preserving. T030 extended parity ratchet (C-005) with fragment-is-the-source: static no-local-coord-composition gate + spy proving load(surface=...) doesn't re-resolve. Gates: status+coordination+parity green (429 passed); ruff clean; mypy at pre-existing baseline (no new errors). Commit dc9abd108.
- 2026-06-10T15:17:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=92560 – Started review via action command
- 2026-06-10T15:27:10Z – user – shell_pid=92560 – Review passed (reviewer-renata): behavior preserved 1:1 across 4 topology cases; double-resolution deleted; single-pass refactor of the SAME authority (C-005 holds); parity 23 green; mypy baseline-parity

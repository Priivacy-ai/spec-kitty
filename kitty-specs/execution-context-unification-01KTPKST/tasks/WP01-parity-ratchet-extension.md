---
work_package_id: WP01
title: Parity ratchet extension (ATDD-first regression guard)
dependencies: []
requirement_refs:
- FR-011
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 0 - Regression Guard
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3616089"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: tests/architectural/
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_execution_context_parity.py
- tests/architectural/parity_fixtures/**
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Parity ratchet extension

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in frontmatter (or pick the best match for
`task_type: implement` + `authoritative_surface: tests/architectural/`). If none set, run
`spec-kitty agent profile list` and choose an implementer profile.

---

## Objectives & Success Criteria

- **EXTEND** `tests/architectural/test_execution_context_parity.py` (existing **1,323 LOC** — do NOT fork; a second parity test is a C-005 parallel-mechanism violation) so it asserts **CWD invariance** of the resolved `MissionExecutionContext`.
- This WP is the **ATDD-first** regression guard (charter C-011): the assertions are authored **before** the conversions; they are `xfail(strict=True)` per cluster until that cluster converts, then each conversion WP flips its assertion to passing.
- **Done when:** the dual-CWD harness + flattened-topology fixture exist; the suite runs deterministically; conversion-dependent assertions are `xfail` with a documented convergence map.

## Context & Constraints

- Design: `kitty-specs/execution-context-unification-01KTPKST/{spec.md (FR-011),plan.md (IC-08),data-model.md,contracts/context-composite-and-facade-adoption.md (C-CTX-2)}`.
- The context fragments to compare: Identity, BranchRef (incl. `destination_ref`/CommitTarget), StatusSurface, Workspace (`primary_root`), ArtifactPlacement, PromptSource. See `data-model.md`.
- Determinism (NFR-003): no `Date.now`/random; fixtures must be reproducible across both CWDs and repeated runs.

## Branch Strategy

- **Planning base / merge target**: `fixups/code-engine-stabilization` (flattened). Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T001 — Dual-CWD parity harness
- **Purpose**: prove the context resolves identically from the primary checkout and from a lane/coord CWD.
- **Steps**: add a parametrized harness that resolves the context for a mission from (a) the repo-root primary checkout and (b) a lane/coord worktree CWD, then asserts fragment-by-fragment equality across `specify → plan → tasks → analyze → implement → review → status`.
- **Files**: `tests/architectural/test_execution_context_parity.py` (extend existing module/classes; reuse its fixtures).

### T002 — Flattened-topology synthetic fixture
- **Purpose**: prove C-001 (flatten) rather than assume it.
- **Steps**: build a synthetic mission with NO separate coordination branch; assert `CommitTarget.kind == flattened`, `coordination_branch is None`, `status_read_dir == status_write_dir`, and primary==coord parity trivially holds.
- **Notes**: do NOT leak `test-feature-*` missions or `kitty/mission-test-feature-*` branches (known E2E leak) — clean up in fixture teardown.

### T003 — xfail-gate + convergence docstring
- **Purpose**: keep the suite green while conversions are in flight.
- **Steps**: mark cluster-specific assertions `pytest.mark.xfail(strict=True, reason="converges in WPnn")`; add a module docstring table mapping each xfail to the WP that flips it (WP02 status, WP03 identity/branch, WP04 read-path, WP05 workspace, WP06 placement, WP07 runtime, WP08 retrospect/merge).

## Test Strategy
- `pytest tests/architectural/test_execution_context_parity.py -q` runs clean (xfails counted, no errors).
- `ruff` + `mypy` zero issues on the changed test module.

## Risks & Mitigations
- *Flaky fixtures* → make the synthetic topology fully deterministic; no network/clock.
- *Accidental fork* → confirm you are EDITING the existing file, not adding a new parity test module.

## Review Guidance
- Recommended sign-off: **architect-alphonso** (parity-as-proof) + **reviewer-renata** (standard).
- Confirm no second parity test was introduced (C-005); confirm xfail convergence map is complete.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T18:21:26Z – claude:opus:python-pedro:implementer – shell_pid=3598297 – Assigned agent via action command
- 2026-06-09T18:31:01Z – claude:opus:python-pedro:implementer – shell_pid=3598297 – Dual-CWD harness + flattened fixture added; conversion-dependent assertions xfail-gated with convergence map; pytest clean (10 passed, 11 xfailed), ruff exit 0, mypy clean
- 2026-06-09T18:32:34Z – claude:opus:reviewer-renata:reviewer – shell_pid=3616089 – Started review via action command
- 2026-06-09T18:38:57Z – user – shell_pid=3616089 – Review passed (reviewer-renata): extends existing parity test (+690 LOC, no fork); dual-CWD harness + flattened fixture; 11 xfail(strict) RED-for-right-reason with convergence map; 10 passed/11 xfailed, ruff+mypy clean. Matrix follow-up handles added.

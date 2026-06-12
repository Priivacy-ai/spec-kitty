---
work_package_id: WP03
title: MissionExecutionContext composite (doc-09 fragments)
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-012
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 1 - Context
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3720555"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/mission_runtime/
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/context.py
- src/mission_runtime/resolution.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – MissionExecutionContext composite

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on
`src/mission_runtime/`.

---

## Objectives & Success Criteria

- Grow the existing `mission_runtime.ExecutionContext` into the **doc-09 fragment / op-composite** (NOT a flat field bag — see `research.md` C-1 and `docs/engineering_notes/runtime_and_state_overhaul/09-context-decomposition-model.md`).
- Fragments (see `data-model.md`): Identity (`mission_id`, `mid8` derived **once**, `mission_slug`), BranchRef (`target_branch` single-source, `coordination_branch`, `destination_ref` = ADR-2026-06-03-2 **CommitTarget**), Workspace, StatusSurface (consumes WP02's resolved surface), ArtifactPlacement, PromptSource.
- An operation assembles only the fragments it needs (op-composite).
- **Done when:** `resolve_action_context` returns the composite; `mid8`/`target_branch` have exactly one derivation point; WP01 identity/branch parity assertions flip to passing.

## Context & Constraints

- The substrate already carries `feature_dir/target_branch/workspace_path/branch_name/execution_mode/mission_slug` — grow it, don't replace it. This is the ADR-2026-06-03-2 **ExecutionContext-owner**.
- Reuse ADR names: ExecutionContext-owner, CommitTarget — coin none (NFR-004).
- New modules declare `__all__` (C-007).
- Findings F-001/F-003 (mid8/branch resolving differently across surfaces) are symptoms this composite removes — keep them in mind; the actual call-site fixes land in WP04.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T008 — Grow ExecutionContext into the fragment composite
- Define the fragments as cohesive value objects; the StatusSurfaceFragment consumes WP02's resolved surface (do not re-derive). **Fragment-boundary granularity is this WP's key design call** (open question in `research.md`) — cut by which ops co-consume fields; get architect sign-off.

### T009 — Single-derivation `mid8` + `target_branch`
- `mid8 = mission_id[:8]` derived once in IdentityFragment; `target_branch` resolved once in BranchRefFragment. No other site recomputes them (FR-012, C-CTX-3).

### T010 — `resolve_action_context` assembles fragments
- One resolution path (C-CTX-1); op-composite assembly; `__all__` on new modules.

### T011 — Flip WP01 identity/branch parity assertions
- Make the WP01 identity + branch fragment assertions pass from both CWDs.

## Test Strategy
- WP01 identity/branch parity green; unit tests for single-derivation invariants; `ruff`+`mypy` zero issues.

## Risks & Mitigations
- *Over/under-cutting fragments* → validate against doc-09; architect sign-off before wide adoption.
- *Substrate churn* → extend, don't rewrite; keep existing field names/aliases working for consumers not yet converted.

## Review Guidance
- Recommended sign-off: **architect-alphonso** (doc-09 fragment conformance, ADR naming) + **reviewer-renata**.
- C-005 enforcement checkpoint: confirm this is the ONE context resolver.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T19:35:03Z – claude:opus:python-pedro:implementer – shell_pid=3707601 – Assigned agent via action command
- 2026-06-09T19:47:54Z – claude:opus:python-pedro:implementer – shell_pid=3707601 – doc-09 fragment composite built: IdentityFragment (mid8 single-derived via .derive), BranchRefFragment (target_branch single-source + destination_ref=CommitTarget kind primary/coordination), StatusSurfaceFragment (consumes WP02 resolve_status_surface, read==write collapse), all attached by resolve_action_context (one resolver, C-CTX-1). Substrate fields preserved (C-004/NFR-001); to_dict excludes fragments. Workspace/ArtifactPlacement/PromptSource fragment types declared but NOT assembled (WP04-07). Flipped 5 parity xfails: identity, branchref, status_surface, flattened_no_coord_branch, flattened_status_collapse; left WP04/05/06/07/08 xfail (incl WP08 CommitTarget.kind==flattened resolution). Gates: parity+unit+surface+consumer tests green (36 passed/6 xfailed), ruff+mypy clean.
- 2026-06-09T19:48:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=3720555 – Started review via action command
- 2026-06-09T19:52:38Z – user – shell_pid=3720555 – Review passed (reviewer-renata): doc-09 fragment composite conforms — IdentityFragment (mid8 single-derived as mission_id[:8] w/ __post_init__ invariant), BranchRefFragment (target_branch single-source threaded once, destination_ref=CommitTarget), StatusSurfaceFragment consumes WP02 resolve_status_surface (not re-derived), primary root via get_main_repo_root (WP02 carry-forward). CommitTarget/CommitTargetKind match mission data-model.md (cites ADR-2026-06-03-2); names not coined. One resolver (C-CTX-1); resolve_action_context sole path. to_dict byte-identical w/ and w/o fragments (NFR-001 verified). Parity: 5 buckets flipped genuinely PASS (identity/branchref/status_surface/flattened-no-coord/flattened-collapse), 6 remaining xfail correctly RED incl WP08 kind==flattened (PRIMARY assigned, FLATTENED never set in resolution.py — boundary honored). Gates: 32 passed/6 xfailed/0 XPASS, ruff+mypy clean. Anti-patterns: fragments live-called or exported for WP04-07; new helper fallbacks documented; no frozen file touched; no forbidden feature* aliases.

---
work_package_id: WP02
title: Status-facade adoption (Cluster B)
dependencies: []
requirement_refs:
- FR-003
- FR-008
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
- T007
phase: Phase 1 - Facade
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3692986"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/coordination/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/coordination/surface_resolver.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/coordination/workspace.py
- src/specify_cli/status/aggregate.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Status-facade adoption

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on
`src/specify_cli/coordination/`.

---

## Objectives & Success Criteria

- Make the **existing** Mission-Management OHS facade (`status/aggregate.py:MissionStatus`) the **sole** status read/write surface — this is **adoption/strangle**, not construction (the facade already exists).
- Fix the parallel coord-path derivation in `status_transition._identity_for_request` (#1737) so it consumes a **resolved** status surface, not its own re-derivation.
- Lock-serialize `CoordinationWorkspace.resolve` (#1357). Achieve status visibility parity primary↔coord (#1572).
- **Done when:** no raw primary/coord status directory reads remain outside the facade; concurrent resolve is serialized; WP01's status-cluster parity assertion flips to passing.

## Context & Constraints

- This WP runs **first** (operator decision: facade-first) so downstream consumers have one stable status authority.
- Design: `spec.md` FR-003/FR-008; `plan.md` IC-01; `contracts/...` C-FAC-1, C-FAC-2; `data-model.md` StatusSurfaceFragment.
- Status authority model (CLAUDE.md): the append-only `status.events.jsonl` reducer semantics are UNCHANGED — this WP changes *who resolves where the log lives*, not the reducer.
- C-004 strangler: convert one reader at a time; keep the lifecycle working throughout.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T004 — Route raw readers through the facade
- Grep for direct primary/coord status-dir reads; redirect through `MissionStatus`. Leave the reducer/store I/O semantics intact.

### T005 — `_identity_for_request` consumes resolved surface (#1737)
- Remove the independent coord-path derivation in `coordination/status_transition.py`; consume the surface resolved by `resolve_status_surface` (to be carried on the context in WP03 — for now consume the resolver output directly, then WP03/WP04 thread it via the StatusSurfaceFragment).

### T006 — Lock-serialize `CoordinationWorkspace.resolve` (#1357)
- Add serialization (lock) so concurrent resolves cannot materialize divergent surfaces. Keep it deadlock-free; cover with a concurrency test.

### T007 — Visibility parity + flip WP01
- Verify status visible identically from primary and coord CWD (#1572). Flip the WP01 status-cluster xfail to passing.

## Test Strategy
- Concurrency test for T006; parity assertion (WP01) for status surface; `ruff`+`mypy` zero issues on changed paths.

## Risks & Mitigations
- *Highest-traffic surface* → strangle incrementally; run the full lifecycle smoke after each reader is redirected.
- *Lock regressions* → keep critical section minimal; test contended + uncontended paths.

## Review Guidance
- Recommended sign-off: **architect-alphonso** (status authority) + **reviewer-renata**.
- Confirm zero raw status reads remain (grep); confirm no second status surface introduced (C-005).

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T18:56:04Z – claude:opus:python-pedro:implementer – shell_pid=3632724 – Assigned agent via action command
- 2026-06-09T19:17:43Z – claude:opus:python-pedro:implementer – shell_pid=3632724 – WP02 done: routed _identity_for_request through canonical resolve_status_surface authority (#1737/F-007) — anchor is CWD-invariant, no parallel derivation; lock-serialized CoordinationWorkspace.resolve (#1357, path-keyed, deadlock-free); status visibility parity (#1572). 5 new WP02 regression tests + concurrency test green; 214 relevant coordination/status/agent/parity tests pass; ruff+mypy clean on new code (6 no-any-return are pre-existing). NOTE: WP01 status xfail (test_status_surface_fragment_parity) stays xfail — it depends on the StatusSurfaceFragment carried on the context, which is WP03's deliverable; WP02 consumes the resolver output directly per spec, so it does NOT flip. test_merge_status_commit's 4 failures are PRE-EXISTING on the base.
- 2026-06-09T19:18:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3692986 – Started review via action command
- 2026-06-09T19:26:29Z – user – shell_pid=3692986 – Review passed (reviewer-renata). F-007/#1737 root fix verified: _identity_for_request anchors feature_dir on the canonical primary dir via resolve_status_surface + candidate_feature_dir_for_mission (10 refs; no parallel resolver, C-005 OK). Mechanism locked by test_identity_consumes_canonical_surface_resolver which FAILS on the merge-base. Dogfooded flattened path proven: HEAD reads in_progress from both primary and sparse-lane CWD. #1357 lock correct: path-keyed, single non-nesting acquisition, deadlock-free; concurrency test races 8 real threads, asserts one worktree + same path, green x3. Gates: tests/specify_cli/coordination + test_execution_context_parity = 97 passed; status suite 318 passed; ruff clean; 6 mypy no-any-return CONFIRMED pre-existing (present on base at shifted lines, untouched fns); 4 test_merge_status_commit failures CONFIRMED pre-existing on merge-base. Scope confined to 2 owned src + 1 justified test. C-004 graceful degradation preserved (documented except handlers). WP01 test_status_surface_fragment_parity legitimately stays xfail — it asserts context.status_surface (a WP03 fragment-on-context deliverable), absent from lane-b base. NON-BLOCKING NOTES for WP03/WP04: (1) the two parity tests pass on base too because canonicalize_feature_dir already redirects when the canonical dir exists on disk, so they don't isolate WP02's fix in this fixture topology — the spy test carries the real ratchet; (2) repo_root = request.repo_root or canonical_repo_root still trusts a lane-supplied repo_root for coord-topology resolution (not a regression; base did likewise; flattened dogfood path unaffected) — thread the canonical root via the StatusSurfaceFragment in WP03/WP04.

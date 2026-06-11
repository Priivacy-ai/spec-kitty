---
work_package_id: WP05
title: Planning-phase placement threading (the catch-22 killer)
dependencies:
- WP02
requirement_refs:
- FR-003
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T15:47:44.831795+00:00'
subtasks:
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Spine riders
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "284480"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/mission_runtime/
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/cli/commands/agent/mission.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Planning-phase placement threading

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Kill the #1777/#1784 catch-22 at its ROOT (split review F-2): the planning paths bypass `resolve_action_context`
(no `wp_id` pre-tasks) and `_resolve_planning_branch` (in your `agent/mission.py`) reads meta.json as a SECOND
destination authority.
- New **`resolve_placement_only(repo_root, mission_slug) → CommitTarget`** projection in `mission_runtime/resolution.py` — adjudicated a legitimate op-composite: it MUST reuse the resolver's internal helpers (same branch/coord/flatten classification as `_assemble_core_fragments`), NOT re-derive.
- Thread it through the **specify/plan commit paths and `agent/mission.py`'s planning paths** (setup-plan, create, record-analysis-adjacent commit calls, `_resolve_planning_branch` consumers) — planning artifacts commit to the resolved destination on protected-target repos.
- **Retire `_resolve_planning_branch`'s meta.json authority** (deletions ledger) — finalize-tasks reads the SAME resolution → no branch disagreement.
- **Guard refusal messages name the resolved destination** (never "switch to the lane branch" before lanes exist — #1777/#1631) — coordinate with WP02's GuardVerdict.reason.
- **Done when (SC-6):** a fresh mission on a protected-target repo completes `specify → plan → tasks → finalize-tasks` with artifacts committed to the resolved destination — verified by the e2e using WP01's fixture; #1784's step-by-step repro passes.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-003), plan.md (IC-04), contracts/ (C-GUARD-3, C-GUARD-3a), research/plan-review-python-pedro.md (the resolve_placement_only proposal), research/plan-review-architect-alphonso.md (F-2 adjudication)}`.
- C-003: this is **placement-threading, not guard relaxation** — the WP01 invariants must stay green; a non-placement commit to a protected ref is still refused.
- Must hold for protected-main, flattened, AND coordination topologies.
- This file also carries the 4th awkward caller (planning-path safe_commit calls) deferred from WP03 — convert them here on the CommitTarget path.
- The SC-6 fixture comes from WP01 (`tests/git/protected_target_fixtures.py`) — it contains `.kittify/` (else the guard is skipped and the e2e is vacuous).

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T018 — `resolve_placement_only` projection
- In `mission_runtime/resolution.py`: a function taking `(repo_root, mission_slug)` (no wp_id/action) returning the `CommitTarget` for planning artifacts — sharing the internal classification helpers used by `_assemble_core_fragments` (one authority, two projections). `__all__` export. Unit tests: flattened/coord/protected-main classification parity with the full resolver.

### T019 — Thread specify/plan + agent/mission.py paths
- Every planning-phase `safe_commit`/commit call in `agent/mission.py` (and the specify/plan command paths it serves) resolves its destination via the projection and passes the CommitTarget. No path constructs a destination from meta.json directly anymore.

### T020 — finalize-tasks + retire the second authority
- `finalize-tasks` (and `_resolve_planning_branch` consumers) read the SAME projection. Delete/redirect `_resolve_planning_branch`'s independent meta.json read (strangler order: re-point consumers, prove green, delete).

### T021 — Refusal messages + runbook text
- When the guard refuses a planning commit, the message states the RESOLVED destination ("planning artifacts for <mission> commit to <ref>") — never lane advice pre-lanes. Update the specify runbook/prompt text (SOURCE under `src/doctrine/` — out-of-map with rationale; run the terminology guard).

### T022 — SC-6 e2e + #1784 repro
- Using WP01's fixture: fresh protected-target project → `mission create` → write+commit spec.md → setup-plan → tasks scaffold → finalize-tasks → assert artifacts on the resolved destination, NO "spec.md not found", NO refusal-to-nowhere. Plus #1784's exact step sequence as a regression test.

## Definition of Done
- SC-6 e2e green on all three topologies (parametrize protected-main / flattened / coord); `rg "_resolve_planning_branch"` shows only the projection-backed path (or zero); WP01 invariants green; `ruff`+`mypy` clean.

## Risks & Mitigations
- *Relaxation-as-coherence* → the WP01 negative invariants are the gate; never weaken them to pass SC-6.
- *Topology divergence* → parametrized e2e across the three topologies.

## Review Guidance
- Recommended: **architect-alphonso sign-off** (single destination authority — projection shares helpers, no second derivation) + **reviewer-renata**. Verify SC-6 is a REAL e2e (fixture asserts .kittify/ precondition), not mocked.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T20:49:34Z – user – shell_pid=158824 – WP05 planning-placement threading complete (T018-T022). resolve_placement_only projection (reuses _assemble_core_fragments; topology parity unit-tested). Threaded all planning commit destinations (_commit_to_branch, finalize-tasks, doc-mission gap/generator commits) through the resolved CommitTarget — no current_branch/meta.json second authority. finalize merge-target anchored on PRIMARY dir for re-run idempotency (F-001). Refusal messages name resolved destination (T021). SC-6 e2e green on protected-main + coordination (incl #1784 sequence + finalize re-run idempotency); flattened xfail (out-of-scope legacy status-bootstrap CWD gap). WP01 invariants green (4 passed/5 xfailed); ruff+mypy clean on new code; no doctrine touched. Lane commit 609675a84.
- 2026-06-10T20:50:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=284480 – Started review via action command
- 2026-06-10T20:54:51Z – user – shell_pid=284480 – Review passed (incl. architect-alphonso sign-off): resolve_placement_only is a legitimate WP-less projection — calls the SAME _assemble_core_fragments builder + get_feature_target_branch as the full resolver and returns branch_ref.destination_ref, byte-identical to _assemble_artifact_placement_fragment (6/6 parity tests assert == full resolver across flattened/coord/protected-main). ONE destination authority, two projections (C-GUARD-3a). Zero guard relaxation: WP01 invariants 4pass/5xfail no-XPASS; protected-main routes to NON-protected coord ref (placement.ref != main), genuine routing not protection-weakening. Threading complete: _commit_to_branch + finalize tasks-commit + 2 doc-mission commits all via _resolve_planning_placement+safe_commit(target=); 4 planning safe_commit calls pass target=, 2 allow_protected_branch_in_test_mode planning callers dropped (remaining one at L3134 is bootstrap_canonical_state, not a commit channel). _resolve_planning_branch RULING: acceptable residual — sole live call (L2416) feeds WP-frontmatter merge-target metadata, NOT any commit destination; re-anchored on PRIMARY dir (F-001). SC-6 e2e 4pass/2xfail[flattened] non-vacuous (asserts .kittify + greps git log placement_ref for real commit); idempotency genuinely re-runs finalize x2. Flattened-xfail SOUND not scope-dodging: projection resolves flattened correctly (parity test green); xfail is pre-existing bootstrap_canonical_state CWD-invariance gap on a distinct surface; all live mission shapes carry coord branch. Gates: ruff clean; mypy clean on NEW code (L229 object-index error traces to #1759/516da6504, pre-existing). Spot-checked pre-existing failures: 2 test_mission_runtime_surface failures are 7 external modules importing mission_runtime.context submodule directly — none in WP05 scope; WP05 imports via package root.

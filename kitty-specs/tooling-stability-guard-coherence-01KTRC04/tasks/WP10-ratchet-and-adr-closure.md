---
work_package_id: WP10
title: 'Spine closure: import-boundary ratchet + ADR addendum'
dependencies:
- WP03
- WP04
- WP05
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T20:55:33.828558+00:00'
subtasks:
- T038
- T039
phase: Phase 3 - Closure
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "311134"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: tests/architectural/test_safe_commit_import_boundary.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_safe_commit_import_boundary.py
- architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP10 – Spine closure (ratchet + ADR)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; pick the best implementer match if none assigned.

---

## Objectives & Success Criteria
Close the guard spine structurally + on paper:
- **#1355:** tighten `tests/architectural/test_safe_commit_import_boundary.py` now that all callers are converted — the ratchet becomes the permanent C-GUARD-1 enforcement: only the blessed entry point (`git/commit_helpers.safe_commit`) may be imported by commit-creating surfaces; nothing imports protection internals (`core/commit_guard` internals beyond the public API) or re-implements the decision; no module re-derives a destination on a commit path (C-GUARD-3a grep clause if expressible).
- **FR-009 ADR addendum:** amend `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md` with an Addendum section recording: (a) `resolve_action_context`'s actual home is `src/mission_runtime/resolution.py` (the `specify_cli/core/execution_context.py` path is retired — post shared-package-boundary); (b) the delivered `CommitTarget` shape is `(ref, kind)` — a deliberate, now-canonical drift from the ADR's sketched `(worktree_root, destination_ref)`; (c) **Step 7 delivered** by missions 01KTPKST (CommitTarget built) + 01KTRC04 (safe_commit consumes it; five privilege channels folded into GuardCapability; SK policy module `core/commit_guard.py`).
- **Done when:** the tightened ratchet is green AND meaningfully strict (it would FAIL if someone added a rogue `assert_not_protected_branch` import or a second guard); the ADR addendum is committed.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-009, NFR-004), plan.md (IC-09), contracts/ (C-GUARD-1)}` + ticket #1355.
- Depends on WP03/WP04/WP05 — every caller is on the facade before tightening (else the ratchet flags in-flight work).
- ADR edits: append an Addendum, do NOT rewrite history (ADRs are immutable records + addenda).

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T038 — Tighten the ratchet (#1355)
- Read the current test; tighten its allowlist to the post-conversion reality: enumerate the blessed importers (should be ~zero outside the facade itself); assert no `_is_protected_branch_exception`-era symbols exist; assert `commit_guard.evaluate` has exactly one importer (`commit_helpers`). Prove strictness: temporarily add a rogue import locally → test fails → revert.

### T039 — ADR addendum
- Append the Addendum section per the Objectives; cross-reference both missions + the GuardCapability model; run the terminology guard (`pytest tests/architectural/test_no_legacy_terminology.py`).

## Definition of Done
- Ratchet green + strictness-proven; ADR addendum committed; terminology guard green; `ruff` clean.

## Risks & Mitigations
- *Ratchet too loose* (passes trivially) → the rogue-import strictness proof is mandatory evidence in the handoff note.

## Review Guidance
- Recommended: **reviewer-renata**; architect-alphonso may spot-check the ADR addendum wording.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T21:05:01Z – user – shell_pid=298741 – WP10 spine closure complete. T038: tightened tests/architectural/test_safe_commit_import_boundary.py to the C-GUARD-1 ratchet — (1) core.commit_guard.evaluate has exactly 2 blessed importers {git/commit_helpers.py facade, coordination/policy.py delegate}; (2) zero references to the 5 deleted privilege channels anywhere in src/; (3) safe_commit(destination_ref=) two-arg shim allowlisted to the single remaining call site cli/commands/merge.py (implement.py destination_ref is BookkeepingTransaction.acquire, not safe_commit — out of scope). Strictness-proven: rogue evaluate-import, rogue deleted-symbol, and rogue destination_ref safe_commit each FAIL the corresponding test, then reverted clean (7 passed). T039: appended append-only Addendum (2026-06-10) to ADR 2026-06-03-2 recording resolve_action_context home = src/mission_runtime/resolution.py (execution_context.py path retired post shared-package-boundary), CommitTarget delivered as (ref, kind in {PRIMARY,COORDINATION,FLATTENED}) with worktree_root via ProtectionState, and Step 7 delivered by 01KTPKST (built CommitTarget) + 01KTRC04 (safe_commit consumes it; 5 channels folded into GuardCapability; core/commit_guard.py extracted). Gates: ratchet 7 passed; ruff clean; terminology guard 2 passed. 4 unrelated architectural failures (mission_runtime_surface/no_dead_symbols/no_raw_mission_spec_paths) confirmed PRE-EXISTING on the unmodified integration tree. Lane commit 4ba2940d3f.
- 2026-06-10T21:05:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=311134 – Started review via action command
- 2026-06-10T21:10:37Z – user – shell_pid=311134 – Review passed: ratchet meaningfully strict (rogue evaluate-import FAILS, reverted clean); blessed evaluate-importers = exactly {git/commit_helpers.py, coordination/policy.py} (policy delegates, not re-implements); 5 deleted privilege channels have 0 refs in src/; destination_ref= shim allowlist = only cli/commands/merge.py:2322 (transaction.py uses canonical target=CommitTarget). acquire(destination_ref=) ruling CORRECT — it's BookkeepingTransaction.acquire kwarg; its commit() routes through safe_commit(target=CommitTarget(...PRIMARY)), so not a shim site and correctly out of AST scope. ADR addendum strictly append-only (0 deletions; @@ -112,3 +112,70 @@), covers (a) home-path retirement to mission_runtime/resolution.py, (b) CommitTarget (ref,kind) drift + worktree_root via ProtectionState, (c) Step 7 delivered crediting 01KTPKST+01KTRC04. Gates: ratchet 7 passed; WP01 commit_guard suite 15 passed/0 xfail; terminology guard 2 passed; ruff clean; scope = 2 owned files only. PRE-EXISTING integration-tree failures (confirmed on 9c419546b WITHOUT WP10, which touched 0 src/ files): test_mission_runtime_surface::test_no_external_submodule_imports, test_mission_runtime_surface::test_ast_scan_no_external_internal_imports, test_no_dead_symbols::test_no_public_symbol_in_all_is_unimported, test_no_raw_mission_spec_paths::test_constant_based_mission_spec_path_construction_stays_in_constructor_files.

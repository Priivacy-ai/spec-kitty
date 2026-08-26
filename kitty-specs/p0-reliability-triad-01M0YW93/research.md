# Phase 0 Research: fix-approach decisions

No open [NEEDS CLARIFICATION] — the three fix directions were settled by a 4-agent pre-spec investigation (root cause, coherence, related-issues, code-state). This records the chosen approach and the rejected alternatives per WP.

## WP01 — #3282 upgrade pointer-charter activations

- **Decision**: Route `_provision_missing_mission_type_activations` (upgrade.py) through the existing pointer-aware writer `charter.compiler.provision_mission_type_activations` → `charter.pack_manager.resolve_activation_write_target` (returns `charter.yaml` for pointer projects, `config.yaml` for legacy). Rewrite `_mission_type_activation_provisioning_pending` to inspect the resolved write target / `PackContext.from_config(...).activated_mission_types`.
- **Rationale**: The read authority (`PackContext.from_config`) already reads pointer `charter.yaml`; the write side is the only half that is pointer-blind. The correct writer already exists and is used by `charter generate`/`activate`. Minimal, no new migration (repair runs on every upgrade via the rc-tolerant finalizer).
- **Alternatives considered**:
  - *Make `provision_default_mission_type_activations` itself pointer-aware* — rejected: it is also on the fresh-init path (`init.py`), which currently writes a legacy config with no pointer; changing it carries fresh-init blast radius.
  - *Modify `resolve_activation_write_target`/`pack_manager`* — rejected: shared by interview/generate/org_charter (wide blast radius, C-004).
  - *Add a new migration* — rejected: unnecessary; the finalizer already runs every upgrade (NFR-003).

## WP02 — #3579 merge stale-lane recovery guidance

- **Decision**: Make `_stale_remediation` (lanes/stale_check.py, planning-lane branch) name the tool's own recovery: after the `git merge`, `spec-kitty agent status materialize --mission <id> && git add`. Optionally have `consolidate_lane_into_mission` perform the incorporation + rematerialize itself (deferred to implementation judgment; minimal fix is the text).
- **Rationale**: `status.json` is a *derived* projection of `status.events.jsonl`; `materialize` rebuilds it cleanly, converting a git conflict into a deterministic regeneration + `git add`. This reaches a real remedy the raw-git text never named.
- **Alternatives considered**:
  - *Register a `status.json` merge driver* — **rejected (would be a regression)**: `status.json` is in `_NON_DIVERGENT_CANONICAL_ARTIFACTS`; adding a driver fails the T013 completeness guard (`tests/architectural/test_merge_reconciliation_class_guard.py`). This is also the issue's closing question — answered: status.json is intentionally driver-exempt (C-002).
  - *Auto-rebase the planning lane* — rejected: the planning lane has no worktree by construction, so `_try_auto_rebase_if_stale` correctly bails; not the fix surface.

## WP03 — #3281 lane allocation retry + ancestry gate

- **Decision**: (1) In `ensure_workspace_materialized` (workflow_executor.py), stop treating `workspace.exists` as "allocation complete"; on a pre-existing lane worktree, re-enter the allocator's idempotent reuse-path self-heal (which already re-runs `_merge_recorded_planning_commit` + `_merge_dependency_lane_tips`). (2) Make fresh-path allocation atomic — remove the leftover worktree if `_merge_recorded_planning_commit` raises. (3) Extend the claim/dependency gate to assert the recorded planning SHA and every approved dependency lane tip are git ancestors of workspace HEAD before emitting `claimed`.
- **Rationale**: The reuse-path self-heal is already correct and idempotent; the only defect is that retry never reaches it. Atomicity mirrors the existing #1915 dependency-merge rollback. The ancestry gate closes the "approved-but-not-merged" hole that status-lane-only gating leaves open.
- **Alternatives considered**:
  - *Only fix the claim gate* — rejected: leaves the leftover-worktree + skipped-propagation on disk; the retry must actually heal.
  - *Broaden into runtime-selection/evidence-commit symptoms from the comment thread* — rejected: scope-fenced out (C-003); those are split to follow-ups.
  - *Reopen #2993/#1684 lineage* — rejected: #3281 is a post-fix residual, not those bugs.

## Supply-chain adversarial evidence
N/A — no dependency decision in this mission.

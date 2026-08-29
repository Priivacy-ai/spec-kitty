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

---

# Post-plan adversarial squad — evidence & dispositions (2026-08-26)

Three profile-loaded lenses (architecture-scout, QA/red-first, foldable-issue) reviewed the committed plan. Dispositions per `contracts/adversarial-evidence-contract.md` (accepted / changed / deferred_with_rationale). No contested finding dropped silently.

## WP03 (#3281) — reshaped (highest-value findings)

- **[HIGH] Ancestry gate at wrong seam → deadlocks approved same-mission deps** (arch + QA). `implement_check_dependency_gate` runs at `workflow.py:1263`, BEFORE `_ensure_workspace_materialized` (:1297) performs the merges that establish ancestry; and the exists-short-circuit collides with the landed #1832/#1833 single-resolution invariant (`test_implement_single_resolution.py` hard-asserts `_create` must not run when workspace exists). → **CHANGED**: ancestry assertion moves POST-materialize (between :1297 and claim emission); pre-materialize status-lane gate stays as fail-fast; exists-branch invokes a dedicated idempotent self-heal, not a break of the #1832/#1833 invariant (that test's semantics updated with rationale). New C-005/C-006.
- **[MED] Ancestry must key on the merged tip + couple to self-heal** (arch). A live-tip predicate re-creates the moving-tip fragility #3281 fixes. → **CHANGED**: one shared predicate evaluated after self-heal re-runs dep-tip merges; on failure route back into self-heal; hard-refuse only if self-heal cannot establish ancestry. FR-007 revised; FR-005+FR-007 land together.
- **[MED-HIGH] orchestrator-api claim path left ancestry-blind (boundary leak)** (arch). `orchestrator_api/commands.py` emits `claimed` via its own composite, never through `workflow_executor`. Self-heal + fresh-path atomicity reach it (owned `worktree_allocator.py`) but the ancestry gate would not. → **CHANGED**: ancestry belongs at a seam BOTH claim paths cross; promoted `orchestrator_api` from mirror-check to an explicit ancestry-parity task. New C-006.
- **[MED] exists-branch decision tree under-specified** (arch). → **CHANGED**: tasks spell out ancestry-correct→no-op vs stale→self-heal (self-heal needs main-repo context, not worktree cwd); Acceptance Scenario 4 (no-op resume) preserved.
- **[LOW] FR-006 fresh-path atomicity is a nicety, not load-bearing** (arch). Merge helpers already abort-and-clean; conflict leaves the worktree clean-but-registered, so reuse-path validation passes and re-entry (invariant 2) is what heals. → **ACCEPTED (scoped)**: targeted `git worktree remove` on the fresh-path raise + one focused test; do NOT build heavy rollback machinery.
- **[MED] Coordinate #2570 friction #1** (foldable): WP03 reshapes the same fresh-path allocation surface. → **ACCEPTED**: added to the #3432 coordination note (C-003). Not a fold.

## WP02 (#3579)

- **[MED] SC-002 unverifiable vs minimal-fix scope** (QA): SC-002/US2-sc2 assert "merge completes," but the executable recovery is Out-of-Scope (minimal fix = remediation text). → **CHANGED**: SC-002 and US2 scenario 2 narrowed to "remediation names a reachable tool remedy," matching scope.
- **[MED] Remediation text asserted in `test_merge.py` (outside owned set)** (QA): `test_merge.py:218-219` asserts the raw-git substrings via `consolidate_lane_into_mission`. → **CHANGED**: `tests/lanes/test_merge.py` added to WP02's lockstep-update set.
- **[MED] Behavioral dependency on #3531** (foldable): the advertised `status materialize` remedy can emit all-zeros `status.json` on a schema-mismatch log. → **ACCEPTED (coordination note)**: reviewer confirms the remedy holds for the same-schema conflict WP02 targets; #3531 (cross-schema) is out of scope, flagged.
- **[LOW] C-002 citation drift** (arch): `_NON_DIVERGENT_CANONICAL_ARTIFACTS` lives in `tests/architectural/test_merge_reconciliation_class_guard.py`, not `merge.py`. → **CHANGED**: C-002 citation corrected.

## WP01 (#3282)

- **[LOW→MED] pending-predicate must absorb fail-loud pointer contract** (arch): `resolve_activation_write_target` raises `CharterPackConfigError` on a dangling `charter:` pointer; the current predicate swallows and returns False. → **ACCEPTED**: keep a defined, non-crashing dry-run contract for the dangling-pointer preview (+ test).
- **[LOW] authored-empty parity for the charter.yaml path** (QA): existing tests cover only the config.yaml empty-list case. → **ACCEPTED**: add a pointer + authored-empty test.
- **[LOW] stale docstring divergence** (arch): after the fix, init stays pointer-blind while upgrade moves pointer-aware. → **ACCEPTED**: update the `_provision_missing_mission_type_activations` docstring so the intentional divergence isn't read as a regression.
- **[LOW] #3702 write/read authority consistency** (foldable): both write `mission_type_activations`. → **ACCEPTED (reviewer note)**: confirm WP01's write authority matches #3702's read-path validation authority. Not a fold.
- **CLEARED**: "no new migration" is SAFE (finalizer runs every upgrade, independent of the migration set).

## Cross-cutting (reported, deferred with rationale)

- **[MED] #3579 + #3281 share one root** — incomplete recovery for a partial reconciliation at the lane git boundary (derived `status.json` must be rematerialized; git state must be re-merged/rolled-back). A unified "lane-reconciliation contract" could host both. → **DEFERRED_WITH_RATIONALE**: folding two independent release-blocking P0s into one seam multiplies blast radius against C-001/C-003 and small-diff discipline under release pressure. Keep the three-point fix for 3.2.6; recorded as a follow-up tracking candidate (surface to operator; do not auto-file).

---

# Post-tasks squad — evidence & dispositions (2026-08-26)

Two lenses (WP-prompt anti-laziness, Sonar/campsite census) reviewed the committed WP prompts. Verdict: prompts strong, all post-plan corrections faithfully carried, red-first genuine, owned sets complete (no forced out-of-map edits), sizing OK.

- **[MED] WP01 predicate-basis hazard** — CHANGED: T003 must key the dry-run predicate on KEY-PRESENCE in the resolved write target, NOT `activated_mission_types` non-emptiness (which would falsely report pending for an authored-empty `[]` pointer project). Added a dry-run "not pending" assertion for the authored-empty pointer fixture to T001.
- **[LOW] WP02 `--mission <id>` scope** — CHANGED (note): `_stale_remediation` has no slug in scope; use a literal `<id>` placeholder or thread from `check_lane_staleness` (both in-map); don't parse the branch name.
- **[HIGH→campsite] WP03 `transition` at complexity 14** — CHANGED: added a campsite block — extract `_parse_policy_or_fail`; one shared ancestry-predicate helper (in `implement_support.py`) called from all three claim sites with early-return for non-claim lanes; extract the stale self-heal helper; add `_remove_lane_worktree` sibling. Keeps every touched function ≤15 and enforces the boundary-correct single-predicate design.
- **CLEARED**: WP03 owned set is complete; red-first is real for all three; no unrelated-concern mixing.

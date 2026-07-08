# Phase 0 Research — Read-Surface SSOT Completion & #1716 Closeout

Decisions consolidated from the pre-spec 3-scout scoping squad + the post-spec 3-lens squad
(Planner-Priti / Architect-Alphonso / Python-Pedro, 2026-07-08). Each decision records what was chosen, why,
and the alternative rejected.

## C-007 plan-gate results (ground truth, re-measured at plan time)

- **coord_authority live split** (via the gate's own `scan_coord_authority_call_sites`): **32 sites total = 7 WRITE + 25 READ.** Matches spec FR-001/FR-002. The 7 write = the allow-list; 2 permanent by-design (`decisions/emit.py:71`, `widen/state.py:63`), 5 drainable. (The "~71" in #2453's body is stale.)
- **#1716 open children**: exactly **{#2088, #2100}** (enumerated via `sub_issues`). Closing both closes the epic (SC-004). No other open children; the epic's original items 1–4 were rejected and items 5–6 delivered by #2462 (superseded-body note).

## D1 — #2404 fix locus: the SEAM, not per-caller (BINDING, C-006)

- **Decision**: Fix the wrong-kind-commit defect class by making `commit_for_mission` per-file partition-aware (group a batch by partition, commit each group to its own ref) — or guard-reject a mixed-partition batch.
- **Rationale**: The root cause is `commit_for_mission` resolving placement from a single caller-supplied `kind` for the entire multi-file batch (`commit_router.py:152`). This closes `spec_commit_cmd.py` (`kind=SPEC`) and `mission_finalize.py:1320` (`kind=TASKS_INDEX`) **by construction** (Directive-043 — close the class, not the instances).
- **Alternative rejected**: Patch the callers individually (spec's original 2-bug scope). Rejected — the next mixed-partition caller reintroduces the class; Pedro/Alphonso found a *third* instance (`mission_finalize`) already, proving the pattern.

## D2 — #2404 is NOT a partition flip (BINDING, C-002)

- **Decision**: Keep `ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` on the coordination partition; do not re-kind them.
- **Rationale**: The flip reverses the operator-confirmed partition locked by #2462 and fails the pinned `test_write_surface_placement_guard.py` (three independent tests drive the real resolver against a real coord fixture). The read side is already correct (INV-5 symmetry: read_surface == write_surface == PLACEMENT); the matrix is stale only because writes misroute.
- **Alternative rejected**: The issue-body "swappable-locus flip". Rejected as unsound (would also require re-adding the kinds to `auto_rebase._AUTO_REBASE_MANAGED_LAYOUT_KINDS`).

## D3 — accept dirty-detection surface reconciliation (M2)

- **Decision**: In `accept.py`, detect dirty coordination artifacts on the **coord worktree** (where `write_acceptance_matrix(feature_dir=…)` writes under coord topology), not only on the primary `git status`, before routing them through the partition-aware seam.
- **Rationale**: `_spec_artifact_dirty_paths` runs `git_status_lines(repo_root=primary)`; the accept-time matrix write-back lands on the coord worktree, so a primary-only scan never sees the real edits — routing alone would still miss them.
- **Alternative rejected**: Route the primary-detected set only. Rejected — leaves the actual coord-worktree edit uncommitted (the bug persists).

## D4 — #2088 is close-only (0 code WPs)

- **Decision**: Verify `69dd1fa46` on base and close #2088; no code work.
- **Rationale**: `validate_no_overlap` already computes transitive dependency reachability and exempts sequential same-lane pairs; commit is an ancestor of base; 16 targeted tests pass. **This fix is load-bearing for THIS mission's decomposition** — it is what lets the 9 cross-thread collision files be same-lane sequential WPs sharing `owned_files` (D11).
- **Alternative rejected**: Re-implement / treat as open work. Rejected — already fixed.

## D5 — coord_authority per-site read/write adjudication (manual, not the gate flag)

- **Decision**: Drain the 5 sites by the *manual* read/write split, never the gate's function-level `is_write` (which marks all 5 as writes). `implement.py`@1468/1663/1169 → `read_dir`; `workflow.py:2747` (mkdir + `review-cycle-N.md`) → `write_target`. `review` has TWO sites: `@2710` read + `@2747` write. The allow-list locator `2670` is stale → live is `2747`.
- **Rationale**: Routing a genuine write to `read_dir` reproduces the #2404 failure mode.
- **Alternative rejected**: Trust the gate's `is_write` flag. Rejected — function-level heuristic, not use-site accurate.

## D6 — status-write false-negatives: reclassify, NEVER route (FR-003)

- **Decision**: `lanes/recovery.py:755` and `agent_tasks_ports.py:322` are STATUS-WRITE legs mis-scanned as reads → reclassify as writes via `_COORD_WRITE_BY_DESIGN` / widen the write-indicator predicate. **Do not route them to `read_dir`.**
- **Rationale**: `recovery.py:755` feeds `emit_status_transition_transactional` and carries an explicit "MUST stay coord-aware — never route it" directive.
- **Ordering (BINDING)**: FR-003 (predicate widen) **precedes** FR-002 (floor re-pin) — widening changes the live write count, so the 7→2 floor must be re-measured after.

## D7 — the new meta-read ratchet must be non-vacuous (FR-006/NFR-002)

- **Decision**: Establish the gate as a *dedicated* concern (IC-06) mirroring `test_resolution_authority_gates.py`: integer floor + margin + a **routed-count floor** (anti-mass-allow-list) + composite-key allow-list with **stale-entry detection** + per-entry rationale. Every deferred site is an explicit allow-list entry with rationale **and a filed follow-up issue**.
- **Rationale**: A ratchet that exempts deferred sites via a prose note (or a fixed `== N`) is vacuous — the allow-list could silently swallow the census.
- **Alternative rejected**: Fold the gate into a routing WP / defer sites via a note. Rejected (Priti F3).

## D8 — migration deferral narrowed to `m_0_13_*` only

- **Decision**: Defer only the historical-fixture-sensitive `upgrade/migrations/m_0_13_*.py` meta reads. `migration/backfill_*`, `migration/mission_state.py`, `migration/rebuild_state.py` are in-scope (route, or per-site allow-list with rationale + issue).
- **Rationale**: A wholesale `migration/` path-exclude silently drops sites #2100 itself scopes in (Priti F4).

## D9 — transaction.py half-in/half-out (C-004)

- **Decision**: Route `transaction.py`'s meta reads that sit **outside** the 751-771 legacy block; add a byte-unchanged regression guarding 751-771.
- **Rationale**: 751-771 is intentional legacy-mission HEAD-override (#1878); the file's other reads are routable.

## D10 — runtime/next shared-package-boundary gating

- **Decision**: Route `src/runtime/next/` meta reads onto `specify_cli.mission_metadata.load_meta` only where a `specify_cli` import is already sanctioned in that module; otherwise defer or stand up a runtime-local authority (a `/tasks`-time per-site call).
- **Rationale**: Avoid a shared-package-boundary violation (`test_shared_package_boundary.py`).

## D11 — cross-thread linearization (9 collision files)

- **Decision**: The 9 files touched by both IC-04 (feature_dir) and IC-05 (meta) — `implement.py`, `orchestrator_api/commands.py`, `context/resolver.py`, `decisions/service.py`, `doctrine_synthesizer/apply.py`, `lanes/recovery.py`, `_identity_audit.py`, `plan_interview.py`, `specify_interview.py` — must have their A-edit and B-edit **co-owned in one WP or sequenced same-lane**. `acceptance/` files stay file-granular (never dir-level `owned_files`).
- **Rationale**: `owned_files` cannot be A/B-disjoint on these; #2088's dependency-aware overlap validator (D4) is exactly what makes same-lane sequential co-ownership legal.

## D12 — single mission, not split

- **Decision**: Keep all four threads in one mission.
- **Rationale**: The #2462 dependency asymmetry is weak (the seam is already on this base at build time; #2462 is a rebase-before-land constraint). Splitting Thread B out would force by-file carving of the 9 collision files anyway. Priti verdict: keep-as-one, floor at 15–17 WPs.

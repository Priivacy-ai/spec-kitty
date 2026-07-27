# Behavioral Contracts — Write-Side Context-Factory Adoption (Mission B)

Function-over-form contracts per concern. Observable behaviors, not structure. Every contract has a
topology-true test obligation (NFR-002): full 26-char ULID, real coord-worktree + real submodule.
Adoption is proven by **deletion** of the inline re-derivation with the suite green + read and write routed
through the **same existing public pure resolver** (D-12 / SC-002), NOT by threading the composite fragment
(NFR-003). **Idempotency (NFR-004): the bounded cut MUST NOT change any on-disk write target.** Note: the
FR-004 write-target divergence DOES have at least one witnessing contract test
(`tests/unit/status/test_mission_status_aggregate.py::test_save_supports_identity_bearing_legacy_mission`
asserts the buggy git-HEAD value) — WP05 owns updating it before→after; WP01's net adds the topology-true oracle.

## C-ROOT (IC-EMIT / IC-WPL / IC-LE / IC-STORE / IC-COORD-root — FR-001)
- Each adopted root site **MUST** resolve the primary root from `workspace.primary_root` (the factory
  projection), not `feature_dir.parent.parent` / ancestor scans.
- **MUST** be CWD-invariant (resolves the same root from primary checkout, coord worktree, and submodule).
- **Deletion proof:** removing the `.parent.parent` walk keeps the status/lifecycle suite green.
- **MUST NOT** change the lock/anchor root value vs the hand-rolled result (equivalence test, D-5).

## C-PLACEMENT (IC-WT — FR-002)
- The two `core/worktree.py` placement joins **MUST** compose from the factory placement projection;
  naming via the `mission_dir_name` seam (unchanged).
- **MUST NOT** change the on-disk placement path (idempotency).

## C-SURFACE (IC-COORD — FR-003, the highest-risk)
- The status-transition write **MUST** consume `status_surface.status_write_dir`, which **MUST** resolve to
  the **status/coord** authority (coord-worktree feature dir when materialized) and **MUST NOT** degrade to
  `primary_root` (C-007; fail-closed preserved).
- Read and write **MUST** resolve the **same** surface for the same mission across primary/coord/submodule
  (NFR-001).
- **MUST NOT** change which on-disk directory a status event is written to (idempotency, NFR-004). The
  write-**target** branch selection is a **separate** concern owned by **C-TARGET (FR-004, now IN scope per
  the reversed D-2)** — not by this surface contract.

## C-RETIRE (IC-RETIRE — FR-006)
- Deleting the `prompt_source` fragment + the `StatusSurfaceFragment.surface=` read-param **MUST** be
  behavior-neutral (no caller passes `surface=`; `prompt_source` has 0 readers).
- The suite stays green after deletion.

## C-BOUNDARY (FR-005, cross-cutting)
- After adoption, **no** write site in the adopted scope re-derives `mission_id`/`mid8`/`primary_root`
  independently (the boundary contract). An optional `tests/architectural/` ratchet flags write-side
  re-derivation in the adopted modules.

## C-TARGET (IC-COORD — FR-004, the branch-target core)
- The write/merge-**target** **MUST** be sourced from `branch_ref.destination_ref`; the inline
  `coord_branch or _current_branch` derivation is deleted.
- **Coord topology:** `destination_ref` resolves to the coordination branch. **Flat/base topology:** it
  resolves to `target_branch` (the base) — CWD-invariant, NOT git HEAD.
- **MUST** carry a before/after on-disk-target idempotency test (NFR-004): the coord case writes to the same
  on-disk target as before; the flat case writes to `target_branch` (the latent-bug-fix vs the old
  `_current_branch`=HEAD is the intended correction, proven, not silent churn).

## C-LANES (IC-LANES — FR-008, the third artifact family)
- The lanes-dir write (`lanes.json`) **MUST** resolve from the context's coord surface
  (`resolve_lanes_dir(<coord feature dir>)`), the coordination authority (C-LANES-1/#1991) — never
  `primary_root` under coord topology.
- **Deletion proof:** the inline lanes-dir derivation is removed; the suite stays green.

## C-SIMPLECASE (IC-SIMPLECASE — NFR-006, the KEYSTONE)
- On a real single-branch repo (full ULID, **no coordination branch declared, no lane worktree**), the
  context object **MUST** resolve **every** diff-type fragment (root, placement, status surface, lanes,
  write-target) to the **base** branch.
- spec-kitty **MUST** run flat — **zero** `.worktrees/` or coordination-surface paths read or written —
  byte-identical to the historical pre-lane behavior.
- This is the binding guard for C-TARGET: the all-base case proves the branch-target object degrades cleanly
  to the simple case "as it used to be."

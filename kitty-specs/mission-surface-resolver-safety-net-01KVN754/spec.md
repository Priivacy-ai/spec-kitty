# Mission-Surface Resolver Strangler-Finish

**Mission ID**: 01KVN754TY9CVJ8G10ERTMPVRH
**Mission slug**: mission-surface-resolver-safety-net-01KVN754
**Mission type**: software-dev
**Target branch**: feat/mission-surface-resolver-safety-net

## Overview / Context

Spec Kitty decides *which on-disk surface holds a mission's artifacts* (coordination worktree vs primary
checkout). Mission `01KVGCE8` already built the **single-resolver safety net** and made
`coordination/surface_resolver.resolve_status_surface_with_anchor` the canonical selection authority — and
that net is **already green**: the audit/inventory (`tests/architectural/surface_resolution_audit/`), the
single-resolver guard (`tests/architectural/test_single_mission_surface_resolver.py`), and the differential
equivalence gate (`tests/missions/test_surface_resolution_equivalence.py`, 27 passed / 6 documented strict
xfails) all pass.

What remains is the **collapse the net was built to make safe** — and a randy-reducer + architect-alphonso
analysis (in `research/`) shows it is a small *convergence*, not a large deletion:

- The legacy "C-004 shim" (`feature_dir_resolver.py`) **no longer exists** (already retired).
- The mid8-blind low-level read primitive (`resolve_mission_read_path`) has only **two** external callers,
  both of which already pre-compute the canonical mid8 — so rerouting them through the mid8-deriving
  `resolve_handle_to_read_path` is byte-identical, after which the primitive is privatized.
- The aggregate's `CoordAuthorityUnavailable` is reachable **only** through the resolver's fail-closed
  family (coord-empty + coord-deleted) — it is not an independent concept. Under the operator-decided
  **coord-empty → Option B (loud primary fallback)**, the coord-empty half evaporates for free (the
  resolver returns primary, the aggregate inherits it). The only residue is **coord-deleted**, which stays
  hard-fail (data loss) but converges its *exception spelling* to `CoordinationBranchDeleted`.

**This mission finishes the #2040 strangler:** it converges the three resolution legs (read-path, surface,
aggregate) so the documented strict-xfail equivalence cells drain to **13/0**, while preserving every
load-bearing invariant. The differential equivalence gate is the deletion-safety net and **must stay green
at every step**.

**Validation vs selection:** the slug-*validation* seam was consolidated by `01KVFTFV` (FR-009) and is out
of scope. This mission is only the *selection* seam (which divergent surface is authoritative).

## User Scenarios & Testing

### Primary — the three resolution legs agree (the collapse)
For the same `(slug, mid8, topology)` input, the read-path leg (`resolve_handle_to_read_path`), the surface
leg (`resolve_status_surface_with_anchor`), and the aggregate leg (`status.aggregate`) return the
**identical directory or the identical typed error (type AND error_code)**. The differential equivalence
gate goes from 9/4 to **13/0** with no remaining divergence cell, and without weakening its
`type(a) is type(b)` assertion.

### Primary — coord-empty resolves primary, loudly
A coord-topology mission whose coordination worktree is materialized but empty resolves to the **primary
checkout and proceeds**, emitting a clear, operator/agent-visible warning naming the stale-surface risk and
both recovery commands (flatten **or** `worktree repair`). All three legs agree on the primary dir.

### Primary — coord-deleted still hard-fails, uniformly
A mission whose coordination branch is *deleted* (unmerged status = data loss) **hard-fails on all three
legs** with the identical `CoordinationBranchDeleted` / `COORDINATION_BRANCH_DELETED` typed error — the
read-path leg learns the `_coord_branch_exists` discriminator instead of returning a stale primary dir.

### Exception / edge cases
- **create→first-write window** (coord declared, worktree not materialized) still resolves **primary** on
  every leg — the #1718 contract is preserved (a regression that hard-failed here would break first-write).
- **no-coord** → primary, unchanged.
- Privatizing `resolve_mission_read_path` must leave **zero dangling external callers** (the two known
  callers reroute byte-identically; any third caller is a blocker).
- The loud coord-empty warning is **net-new** (the resolver emits no logging today); a test asserting it
  fires on the coord-empty path is binding (the observability is load-bearing).

## Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | Use (do not rebuild) the existing single-resolver safety net — audit/inventory, the single-resolver guard, and the differential equivalence gate — as the **deletion-safety gate**. The gate MUST remain green at every WP boundary; as cells drain, retire the corresponding `_XFAIL_*` constants **without weakening** the gate's `type(a) is type(b)` AND `error_code` equality assertion. | proposed |
| FR-002 | Converge the mid8-blind read primitive: reroute the two external callers of `missions/_read_path_resolver.resolve_mission_read_path` (`acceptance/__init__.py:618`, `mission_runtime/resolution.py:185` — both already pre-compute the mid8) onto `resolve_handle_to_read_path` (byte-identical), then **privatize** the primitive (`resolve_mission_read_path` → `_resolve_mission_read_path`). Drains the read-path mid8-blindness cells. | proposed |
| FR-003 | Apply **coord-empty Option B** at the canonical seam: a materialized-but-empty coordination worktree no longer raises `CoordinationWorktreeEmpty`; it **falls back to the primary checkout and proceeds**, emitting the loud warning (NFR-003). Delete the now-dead `CoordinationWorktreeEmpty` + `_is_coord_empty_condition` + `_canonicalize_or_enrich_coord_empty`. The aggregate inherits primary for coord-empty with **no aggregate code change**. Preserve unchanged: create→first-write window and no-coord both resolve primary. | proposed |
| FR-004 | Converge **coord-deleted** (stays hard-fail — data loss, C-001): propagate `CoordinationBranchDeleted` (`COORDINATION_BRANCH_DELETED`) **verbatim** through `status.aggregate._resolve_read_dir` instead of re-wrapping it in the error-code-less `CoordAuthorityUnavailable`, AND fold the surface's `_coord_branch_exists` discriminator into the read-path leg under `require_exists=True` so it hard-fails coord-deleted instead of returning a stale primary dir. Keep `CoordAuthorityUnavailable` **exported** (do not delete — C-003). Drains the coord-deleted cells. | proposed |
| FR-005 | Ship the public-contract migration in the **same slice** as FR-004: add `CoordinationBranchDeleted` to the two `except` tuples in `cli/commands/agent/status.py`; invert `test_coord_empty_is_a_separate_hard_fail_cell` to assert primary + warning; re-point `test_fail_closed_window_yields_coord_authority_unavailable_for_all_handles`; add a converged coord-deleted aggregate-contract test. (Editing the WP04-frozen `agent status` contract is in scope by operator decision.) | proposed |
| FR-006 | Extract a pure, topology-aware `_resolve_lanes_dir(repo_root, mission_slug) -> Path` seam from the inline assignment in `implement()` (`src/specify_cli/cli/commands/implement.py:~1019`), preferring the coord-worktree surface and falling back to primary for flat/legacy topology. Distinct from `lanes/persistence.resolve_lanes_dir`. **Verify-first:** if the residual is already satisfied behaviorally, the WP is the pure extraction + zero-mock test only (#2052). | proposed |
| FR-007 | Remove the inverted package dependency in `coordination/commit_router.py:303/308` (it imports `path_is_under_worktrees` from `cli/commands/merge.py`) by calling the same-package `coordination/surface_resolver.is_under_worktrees_segment` directly, byte-identical (#2061). | proposed |
| FR-008 | Regression-guard the closed #2046 read-CLI unification: the differential matrix's `coord-*/bare-slug` cells confirm bare-slug → coord (not silent primary) and a mutation reverting the `resolve_handle_to_read_path` mid8 cascade flips a cell. | proposed |

## Non-Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| NFR-001 | The differential equivalence gate is green at **every** WP boundary (deletion-safety): 9/4 → 10/3 → 13/0. No WP may leave a premature green (deleting before a cell legitimately drains) — the strict-xfail machinery turns that into a suite failure. | proposed |
| NFR-002 | The gate's equality assertion (`type(a) is type(b)` AND `error_code` equality) is **not weakened**; only `_XFAIL_*` allowlist entries are retired as cells go green. | proposed |
| NFR-003 | The coord-empty loud fallback warning is **non-silent and test-asserted to fire** (operator/agent-visible; names the stale-surface risk + both recovery commands). It is net-new infrastructure (the resolver emits zero logging today). | proposed |
| NFR-004 | FR-002 reroutes and FR-007 are **byte-identical, zero-behavior-change** refactors, each covered by a focused test; FR-006 is unit-testable with a `tmp_path` and **no infrastructure mocks**. | proposed |
| NFR-005 | The privatized `_resolve_mission_read_path` has **zero** external callers after FR-002 (verified by an import/grep check in the same WP). | proposed |

## Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | **Coord-deleted stays hard-fail.** Option B is for coord-*empty* only. Coord-deleted (`CoordinationBranchDeleted`, #1848) is data loss; FR-004 converges its *spelling*, never softens it to a fallback. | active |
| C-002 | **#1718 create-window preserved.** Coord-declared-but-unmaterialized still resolves primary on every leg; the loud fallback and the `_coord_branch_exists` discriminator must not fire in the create-window. (Fallback if folding the discriminator into the read-path reveals create-window risk: leave the read-path coord-deleted cell as a documented xfail — strictly smaller residue than today.) | active |
| C-003 | **Keep `CoordAuthorityUnavailable` exported.** Deleting it is a separate API-deprecation change, out of scope. FR-004 changes only what the aggregate *raises*, not the type's existence. | active |
| C-004 | **Do not re-route the acceptance lane** (`acceptance` is the FR-010-blessed lenient carve-out) beyond the byte-identical FR-002 reroute; **do not touch the `mission_runtime` error taxonomy** (it auto-propagates codes); **do not re-do #2046** (closed/fixed — FR-008 only regression-guards it); **do not generalize the loud warning** beyond coord-empty. | active |
| C-005 | **Canonical-sources discipline + no version prescription.** Reuse the existing audit/guard/differential; the PO assigns release numbers. | active |

## Success Criteria

- **SC-001** The differential equivalence gate reads **13 passed / 0 xfailed** with the `_XFAIL_*` constants
  retired and the `type`-AND-`error_code` assertion unchanged.
- **SC-002** `resolve_mission_read_path` is privatized with zero external callers; the two rerouted callers
  are byte-identical (test-proven).
- **SC-003** A coord-empty mission resolves primary on all three legs and emits the loud recovery-naming
  warning (test-asserted); `CoordinationWorktreeEmpty` and its two helpers are deleted.
- **SC-004** A coord-deleted mission hard-fails on all three legs with identical
  `CoordinationBranchDeleted` / `COORDINATION_BRANCH_DELETED`; `CoordAuthorityUnavailable` remains exported;
  the `agent status` CLI + migrated tests are green in the same slice.
- **SC-005** The create→first-write window and no-coord still resolve primary (regression tests green).
- **SC-006** `_resolve_lanes_dir` is a pure function with a zero-mock unit test (or the residual is shown
  already satisfied and only the extraction + test land).
- **SC-007** `coordination/commit_router.py` has zero `coordination/ → cli/` reach-ins, byte-identical.
- **SC-008** The closed #2046 read-CLI unification is regression-guarded (a mutation flips a `coord-*/bare`
  cell).

## Key Entities

- **Resolution leg** — one of the three entry points (read-path / surface / aggregate) the differential
  gate compares.
- **Differential equivalence gate** — `test_surface_resolution_equivalence.py`; the deletion-safety net.
- **Coordination-empty / coordination-deleted** — the two fail-closed topology states; empty → loud
  primary fallback, deleted → hard-fail (converged spelling).

## Domain Language

- **Selection** (canonical) — choosing the authoritative on-disk surface. *This mission.*
- **Validation** — slug-is-a-safe-segment. *Already consolidated (`01KVFTFV`); not this mission.*
- **Convergence** — routing the three legs through one body so they agree; the collapse is convergence, not
  a large deletion.

## Assumptions

- The existing differential gate genuinely observes resolver output (the 6 xfails are real divergences),
  so draining them proves convergence — confirmed by the randy/alphonso live reads in `research/`.
- The two external callers of the mid8-blind primitive pre-compute the canonical mid8, making FR-002
  byte-identical (verified in `research/collapse-reduction-map-randy.md`).
- `CoordAuthorityUnavailable` is reachable only via the resolver fail-closed family, so coord-empty's
  aggregate half evaporates under Option B with no aggregate code (verified in
  `research/collapse-boundary-analysis-alphonso.md`).

## Issue Matrix (referenced issues)

| Issue | Relationship |
| --- | --- |
| #2040 | Driver — this mission is its strangler-**finish** (converge the legs; drain all 4 xfails to 13/0). |
| #2010 | Parent (closed) — its read/write desync is closed on the read path by this convergence; bug #15 typed-error pass-through already landed and is regression-guarded. |
| #1716 | Coordination topology coherence — the coord-empty policy (Option B) is decided + applied (FR-003; ADR `2026-06-19-1` amended); coord-deleted converged (FR-004). |
| #1848 | `CoordinationBranchDeleted` — preserved as the coord-deleted hard-fail and converged across legs (FR-004). |
| #2046 | Verified-already-fixed; FR-008 regression-guards the read-CLI unification. |
| #2052 | Folded — `_resolve_lanes_dir` pure extraction (FR-006). |
| #2061 | Folded — `commit_router` inverted-layering fix (FR-007). |
| #1868 | Canonical-seams epic — the single-resolver guard binds it; this mission completes the adoption. |
| #1993 | Extraction-without-adoption — this mission is the adoption (route+delete the duplicate primitive). |
| #2007 | Epic. |

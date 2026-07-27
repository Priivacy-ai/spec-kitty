# Mission-Surface-Resolver COLLAPSE — Reduction/Deletion Blueprint

**Author:** randy-reducer (semantic-compression: fewer paths, same behavior, proven)
**Mission:** mission-surface-resolver-safety-net-01KVN754 (#2040 strangler-finish)
**Branch:** feat/mission-surface-resolver-safety-net
**Mode:** boundary → reduction → equivalence

---

## 0. Behavioral envelope (what must NOT change)

The differential gate `tests/missions/test_surface_resolution_equivalence.py` is the
deletion-safety contract. It feeds the SAME `(topology, handle)` matrix to three
entry points and asserts identical dir OR identical typed error (class + `error_code`):

- **Leg A** `resolve_handle_to_read_path(..., require_exists=True)` — the mid8-deriving seam
- **Leg B** `resolve_status_surface_with_anchor(...).read_dir` — the surface authority
- **Leg C** `MissionStatus.load(...).read_dir` (via `_resolve_read_dir`) — the aggregate boundary

Current state: 27 passed, 6 strict-xfails (the matrix labels them; assertion
discipline `type(a) is type(b)` and `error_code` equality is load-bearing — never weaken it).

**Operator-binding decisions:**
- coord-EMPTY → **Option B LOUD PRIMARY FALLBACK** (ADR `2026-06-19-1-coord-empty-surface-fallback.md`, amended to B). No longer hard-fail.
- coord-DELETED → **STAYS HARD-FAIL** (data loss, #1848 `CoordinationBranchDeleted`). Do NOT soften.

The protected externally-observable behavior is: **every read entry point resolves a bare
`--mission <slug>` to the SAME surface a `<slug>-<mid8>` handle does, and surfaces the SAME
typed error.** The collapse makes that true by construction (one resolution body), which is
what drains the 6 xfails.

---

## A. DELETE-LIST (ordered smallest-blast-radius first)

The headline finding: **there is no large duplicate-resolver thicket left to delete.** R1/R2
already strangled the parallel resolvers. The collapse is a *convergence* (route the 3 legs
through one body), and the deletions that fall out of it are small and gated.

| # | Delete / collapse | File:line | Precondition (xfail cell green first) | Blast radius |
|---|---|---|---|---|
| **A1** | The mid8-blindness *branch* inside `resolve_mission_read_path` — i.e. make the public primitive route through the mid8-deriving cascade so the slug-vs-`<slug>-<mid8>` divergence disappears. NOT a file delete; a behavioral collapse of the "literal-slug → primary" path. | `_read_path_resolver.py:289` (`_resolve_existing_for_slug` literal call) + the bare-slug path through `resolve_mission_read_path` | The 4 `_XFAIL_READPATH_MID8_OUT_OF_SCOPE` cells (coord-fresh/bare, coord-behind/bare are already GREEN; the RED ones are coord-empty/bare, coord-deleted/bare which now carry `_XFAIL_BARE_AGGREGATE_*` — see drain matrix) must go green. | LOW: the 2 external direct callers already pre-derive mid8. |
| **A2** | `mission_read_path.py` back-compat shim (the whole module). | `src/specify_cli/mission_read_path.py` (39 lines) | After A1 lands AND a repo-wide grep proves zero importers of `specify_cli.mission_read_path`. Last production importer (`runtime/next/runtime_bridge.py`) already re-pointed (per the shim docstring). | LOW: shim-only; verify no external import remains, else keep one release cycle. |
| **A3** | `CoordinationWorktreeEmpty` class + `_canonicalize_or_enrich_coord_empty` + `_is_coord_empty_condition` (the entire coord-empty HARD-FAIL apparatus). | `surface_resolver.py:176-245` (class), `:527-585` (`_is_coord_empty_condition`, `_canonicalize_or_enrich_coord_empty`), `:735-743` (the raise site) | **Option B drain**: coord-empty cells go green when all three legs → PRIMARY (loud warn). This is a genuine DELETION enabled by the operator's Option-B decision. | MEDIUM: `CoordinationWorktreeEmpty` is referenced by `test_surface_resolver_collapse.py` (mutation-verified) — that test must be rewritten to assert the loud-primary-fallback contract in the same WP. |
| **A4** | `CoordAuthorityUnavailable` translation *divergence* in the aggregate — collapse leg C onto the same typed-error leg A/B emit, so the `type(a) is type(b)` gate passes for coord-empty/coord-deleted slug-mid8 cells. | `aggregate.py:69-90` (class), `:349-354` (the `StatusReadPathNotFound → CoordAuthorityUnavailable` re-raise in `_resolve_read_dir`) | The 2 `_XFAIL_COORD_EMPTY_SEAM_*` + `_XFAIL_COORD_DELETED_SEAM_*` slug-mid8 cells. Closing requires deciding the converged boundary type (see drain matrix D-§ caveat). | **HIGH**: `CoordAuthorityUnavailable` is public API, caught by `agent status` CLI, asserted in 3 non-owned tests (`test_aggregate_surface_resolution`, `test_mission_status_aggregate`, `test_handle_equivalence_matrix`). Touch LAST, with those tests in the same WP. |

**Not deletable / already gone:**
- `missions/feature_dir_resolver.py` — **already retired (WP07/FR-007).** The file does not exist; functions relocated into `_read_path_resolver.py` (`resolve_feature_dir_for_slug`, `resolve_feature_dir_for_mission`). The "C-004 shim" named in the brief is already dead. Nothing to do.
- The aggregate `_find_meta_path` glob (`aggregate.py:453`) routes through the shared `resolve_bare_modern_mission_dir_name` seam (`_read_path_resolver.py:645`) — single definition, NOT a duplicate. Keep.
- `resolve_status_surface` (thin wrapper over `_with_anchor`) — keep; it's the canonical accessor, not a duplicate.

---

## B. REROUTE-LIST (every callsite of a to-be-deleted resolver → canonical entrypoint)

Only **2 external direct callers** of the mid8-blind primitive `resolve_mission_read_path`
remain (all others are docstring mentions or the shim). Both already pre-compute the
canonical mid8, so the reroute is mechanical and behavior-preserving:

| Callsite | Current call | Reroute to | Why safe |
|---|---|---|---|
| `acceptance/__init__.py:618` | `resolve_mission_read_path(repo_root, feature, mid8)` where `mid8 = resolve_declared_mid8(meta, feature)` (line 616) | `resolve_handle_to_read_path(repo_root, feature)` — the seam re-derives the SAME `resolve_declared_mid8` cascade internally (it calls `read_primary_meta`→`resolve_declared_mid8`). | The pre-computed mid8 is **byte-identical** to what the seam derives. Drop the local `resolve_declared_mid8` import too (now dead here). |
| `mission_runtime/resolution.py:185` | `resolve_mission_read_path(repo_root, slug, mid8)` where `mid8 = mid8_from_slug(slug)` then `_mid8_from_primary_meta(repo_root, slug)` fallback (lines 166-174) | `resolve_handle_to_read_path(repo_root, slug, require_exists=...)` — the seam's `resolve_declared_mid8` SUBSUMES both `mid8_from_slug` (tier 3) and the primary-meta read (tier 1/2). | Subsumption is exact; the local `_mid8_from_primary_meta` helper + `mid8_from_slug` import become dead and are deleted in the same edit. The existing `except StatusReadPathNotFound / MissionSelectorAmbiguous → ActionContextError` translation is preserved unchanged. |

**Internal callers of `resolve_mission_read_path` (stay — they ARE the seam internals):**
`_read_path_resolver.py:509` (inside `resolve_handle_to_read_path`), `:608`
(`candidate_feature_dir_for_mission`), `:709` (`resolve_feature_dir_for_slug`).
After A1, the primitive is reachable ONLY through these in-module wrappers — i.e. it becomes
a private helper. **Rename `resolve_mission_read_path` → `_resolve_mission_read_path`** (drop
from `__all__`, drop the shim re-export) to make the encapsulation enforced, NOT just
conventional. This is the dead-weight-elimination move: a public symbol with zero external
callers is a duplication risk.

**Dangling check:** after A1+A2 reroutes, `grep -rn "resolve_mission_read_path(" src/` must
show only the 3 in-module wrappers + the (renamed) def. None left dangling. ✅

---

## C. XFAIL DRAIN MATRIX (each of the 6 cells)

| Cell | Today (live-observed) | Drains-to-GREEN how | or STAYS-xfail why |
|---|---|---|---|
| **coord-empty/bare** (`_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY`) | read_path leg FIXED (seam derives mid8→coord); divergence is aggregate `CoordAuthorityUnavailable` (no `error_code`) vs surface typed error | **DRAINS via Option B (A3+A4).** All 3 legs → PRIMARY dir (loud warn). With coord-empty now returning a *directory* (not a typed error), legs A/B/C all return the same primary dir → cell asserts dir-equality, green. | — |
| **coord-empty/slug-mid8** (`_XFAIL_COORD_EMPTY_SEAM`) | read_path→`StatusReadPathNotFound`; surface→`CoordinationWorktreeEmpty`(same code, diff class); aggregate→`CoordAuthorityUnavailable`(no code) | **DRAINS via Option B (A3+A4).** Delete `CoordinationWorktreeEmpty` raise (A3); surface returns primary dir + loud warn. read_path's `_resolve_not_found` coord-empty `fail_closed` branch (`_read_path_resolver.py:364-377`) must ALSO be flipped to return `primary_candidate` for the coord-empty (root materialized) sub-case — keeping the coord-DELETED fail-closed intact. All 3 legs → primary dir. Green. | — |
| **coord-deleted/bare** (`_XFAIL_BARE_AGGREGATE_COORD_AUTHORITY`) | read_path FIXED→ (after A1 reaches coord-deleted detection); divergence aggregate boundary type | **DRAINS via converging on hard-fail (A4).** All 3 legs must raise `CoordinationBranchDeleted` (code `COORDINATION_BRANCH_DELETED`). Requires: (i) read_path/seam to *detect* deleted-branch (currently it returns primary — see feasibility below); (ii) aggregate leg C to propagate the surface's `CoordinationBranchDeleted` instead of translating to `CoordAuthorityUnavailable`. | — |
| **coord-deleted/slug-mid8** (`_XFAIL_COORD_DELETED_SEAM`) | read_path→PRIMARY dir (no error!); surface→`CoordinationBranchDeleted`; aggregate→`CoordAuthorityUnavailable` | **DRAINS via converging on hard-fail (A1+A4).** Same as above. The hard part is read_path: today `resolve_mission_read_path` has NO `git rev-parse` deleted-branch probe (only the surface's `_coord_branch_exists` does). See FEASIBILITY. | — |
| **coord-fresh/bare** | already GREEN | n/a (already equivalent) | — |
| **coord-behind/bare** | already GREEN | n/a (folds into coord-fresh) | — |

### FEASIBILITY — coord-DELETED converging on the hard-fail in read_path

The brief asks: "verify feasibility — read_path must ALSO hard-fail coord-deleted instead of
returning primary." **Feasible but it adds a git touch to the read_path primitive**, which
violates its current "pure-path on the happy path" contract (`_read_path_resolver.py:247`).

Two options, in order of preference:

1. **PREFERRED — route leg A through the surface for the not-found tail only.** When
   `resolve_handle_to_read_path` (the seam, leg A) would fall to the not-found/primary tail
   AND `meta` declares `coordination_branch`, delegate the *final* coord-deleted-vs-coord-empty
   disambiguation to `resolve_status_surface_with_anchor` (which already owns `_coord_branch_exists`).
   This keeps the deleted-branch `git rev-parse` in ONE place (the surface) — no duplication.
   The #1718 create-window contract is preserved because the seam still routes to PRIMARY for
   *unmaterialised-but-not-deleted* coord (the surface returns the composed coord path there,
   which the seam's `require_exists=True` gate then resolves correctly). **This is the
   semantic-consolidation move: one deleted-branch authority, not two.**

2. Fallback — lift `_coord_branch_exists` into a shared primitive both legs call. More code,
   two call sites. Avoid unless option 1 regresses #1718 in a live probe.

The aggregate leg C drain (A4) is then trivial: stop catching `StatusReadPathNotFound` →
`CoordAuthorityUnavailable`; let `CoordinationBranchDeleted` (a `StatusReadPathNotFound`
subclass) propagate as-is. **But** this is the HIGH-blast-radius change (public API,
`agent status` CLI, 3 non-owned tests) — it MUST ship with those 3 tests updated in the same WP.

### ⚠️ Caveat the planner MUST adjudicate (do not let spec/plan undersize it)

The 2 slug-mid8 SEAM cells currently say convergence "is not in WP06's requirement_refs" and
the aggregate `CoordAuthorityUnavailable` is "WP04's approved public single-seam contract,
un-editable." **The #2040 collapse explicitly re-scopes that** — converging the aggregate type
IS now in scope (operator pulled R3 forward). So A4 deliberately edits what WP04 froze. The
WP that owns A4 must:
- Decide the converged type: keep `CoordAuthorityUnavailable` for coord-empty-Option-B is moot
  (coord-empty now returns a dir, no error). For coord-DELETED, the converged type is
  `CoordinationBranchDeleted` across all 3 legs.
- Update `agent status` CLI rendering + the 3 non-owned tests in the SAME WP (they assert the
  old boundary type; leaving them stale = red CI).

---

## D. #2052 and #2061 tidies — coupling check

### #2052 `_resolve_lanes_dir` (implement.py)
**Already collapsed — not an open tidy in the form the brief states.** At
`implement.py:1019-1027` the lanes-dir is already `_lanes_feature_dir = _status_feature_dir`
(the coord surface from `resolve_status_surface_with_anchor`). There is no inline
`_resolve_lanes_dir` at 1020-1026 anymore — `resolve_lanes_dir` lives canonically in
`lanes/persistence.py:23` and is consumed by `persistence.py:54,89` and
`workspace/context.py:798`. **Independent of the collapse** (separable owned_files:
`lanes/persistence.py` + `implement.py`). If #2052 wants the implement.py inline join folded
into `resolve_lanes_dir`, it's a 1-line reroute with zero overlap with the resolver surfaces.
**Confirm: separable WP, no coupling.**

### #2061 commit_router inverted-layering (commit_router.py:303/308)
`commit_router.py:293` imports `path_is_under_worktrees` from
`cli/commands/merge.py:171` — a CLI module importing UP into a coordination module is the
inverted layering. The canonical shape predicate is `is_under_worktrees_segment`
(`surface_resolver.py:289`, the blessed C-SEAM-1 home). **Reroute:** replace the
`from specify_cli.cli.commands.merge import path_is_under_worktrees` with
`from specify_cli.coordination.surface_resolver import is_under_worktrees_segment` and
collapse the two functions onto one (they answer the same `".worktrees" in parts` question).
**Coupling:** touches `surface_resolver.py` (shared with the collapse) only as an *importer*,
not a *mutator* — the predicate body is untouched. **Separable WP; sequence AFTER A3/A4 land
to avoid merge churn on `surface_resolver.py`, but no logical coupling.** Also delete the
now-orphaned `path_is_under_worktrees` in `merge.py` if it has no other caller (verify).

---

## E. WP / owned-files decomposition (Tidy-First, disjoint surfaces, gate-green-at-every-step)

The differential matrix is the deletion-safety gate. Each WP flips its xfail cells to GREEN
(by editing ONLY the xfail markers + the resolution body it owns) and the suite must stay
green/xfail-tracked at every commit. Order = smallest blast radius → highest.

**WP-T1 (Tidy-First, no behavior change): rename + reroute the mid8-blind primitive.**
- owned: `_read_path_resolver.py`, `acceptance/__init__.py`, `mission_runtime/resolution.py`, `mission_read_path.py`
- Rename `resolve_mission_read_path → _resolve_mission_read_path` (drop from `__all__`/shim).
- Reroute the 2 external callers to `resolve_handle_to_read_path` (B-table). Delete dead `_mid8_from_primary_meta`/local mid8 derivation.
- Delete `mission_read_path.py` (A2) IFF grep proves zero external importers; else defer to a follow-on.
- Gate: matrix unchanged (still 27/6) — pure consolidation. ✅ equivalence-verify.

**WP-T2: commit_router layering tidy (#2061) — independent, parallelizable with WP-T1.**
- owned: `commit_router.py`, `merge.py`
- Reroute to `is_under_worktrees_segment`; delete orphaned `path_is_under_worktrees`.
- Gate: matrix unchanged. ✅

**WP-T3: lanes-dir tidy (#2052) — independent, parallelizable.**
- owned: `lanes/persistence.py`, `implement.py`
- Fold the implement.py inline join into `resolve_lanes_dir` if desired.
- Gate: matrix unchanged. ✅

**WP-C1: coord-EMPTY → Option B loud primary fallback (drains 2 cells).**
- owned: `surface_resolver.py`, `_read_path_resolver.py` (the `_resolve_not_found` coord-empty branch), `tests/coordination/test_surface_resolver_collapse.py`, the 2 coord-empty rows in `test_surface_resolution_equivalence.py`
- DELETE `CoordinationWorktreeEmpty` + `_is_coord_empty_condition` + `_canonicalize_or_enrich_coord_empty` (A3). Surface returns primary dir + emits the loud structured warning (per amended ADR). Flip read_path coord-empty `fail_closed` → primary.
- Rewrite `test_surface_resolver_collapse.py` to assert loud-primary-fallback (NOT hard-fail).
- Flip `coord-empty/bare` + `coord-empty/slug-mid8` xfail markers to GREEN.
- Gate: 29 passed, 4 xfail. ✅ Must NOT touch coord-deleted (still hard-fail).

**WP-C2: coord-DELETED convergence on hard-fail (drains 2 cells) — HIGHEST blast radius, last.**
- owned: `_read_path_resolver.py` (route the not-found tail through the surface's deleted-branch authority — feasibility option 1), `aggregate.py` (A4: stop translating to `CoordAuthorityUnavailable`, propagate `CoordinationBranchDeleted`), `cli/commands/*status*` CLI rendering, the 3 non-owned aggregate tests, the 2 coord-deleted rows.
- All 3 legs → `CoordinationBranchDeleted` / `COORDINATION_BRANCH_DELETED`.
- Flip `coord-deleted/bare` + `coord-deleted/slug-mid8` to GREEN.
- Gate: 31 passed, 0 xfail. ✅ FULL DRAIN — at this point delete the 4 `_XFAIL_*_OUT_OF_SCOPE` constants and the allowlist docstring paragraph.

**Disjointness:** WP-T1/T2/T3 are fully disjoint (different files). WP-C1 and WP-C2 both touch
`surface_resolver.py` + `_read_path_resolver.py` → **linearize C1 before C2** (refactor-mission
shared-surface rule). WP-T1 must land before C1/C2 (they assume the renamed private primitive).

**Risk-explicit:** WP-C2 edits what WP04 froze as a "public single-seam contract." That is
sanctioned by the operator pulling R3 forward, but it is the one place a naive implementer will
either (a) weaken the `type(a) is type(b)` gate assertion to fake-green, or (b) leave the 3
non-owned tests stale. Both are review-blocking. The gate assertion is load-bearing; only the
xfail markers are editable.

---

## Summary of the reduction

- **Files deleted:** `mission_read_path.py` (if no external importers); `CoordinationWorktreeEmpty` + 2 helpers; the `_XFAIL_*` constants + allowlist docstring (at full drain).
- **Symbols privatized:** `resolve_mission_read_path → _resolve_mission_read_path`.
- **Duplications collapsed:** 2 deleted-branch authorities → 1 (surface owns `_coord_branch_exists`); CLI→coordination inverted import folded onto `is_under_worktrees_segment`.
- **Net behavior change (operator-sanctioned):** coord-empty stops hard-failing (Option B); coord-deleted converges all 3 legs on the existing hard-fail.
- **Proven by:** the differential matrix going 27/6 → 29/4 → 31/0, green at every WP boundary.

# Mission Specification: Read-Surface SSOT Completion & #1716 Closeout

**Mission slug**: `read-surface-ssot-closeout-01KWZV91`
**Mission type**: software-dev
**Status**: Draft (post pre-spec-squad + post-spec 3-lens squad)
**Roadmap**: 3.2.x · G2 (core-domain SSOT strangling) — the **read-side counterpart** to the #1878 write-side strangler
**Tracker**: closes #1716 (its last two open children #2088, #2100) · #2453 · #2404 · under #2160 / #1619
**Base**: branched off `design/coord-primary-partition-lock` (PR #2462) — consumes the `PlacementSeam` that PR introduces

> **Squad provenance.** A 3-scout pre-spec scoping squad + a 3-lens post-spec squad (Priti/Alphonso/Pedro,
> 2026-07-08) corrected every ticket's scope and the sizing. Their evidence folds into `research/` at plan.
> Key corrections baked in below: #2088 already fixed (close-only); #2404 is a **seam-level** write-routing
> defect (not a 2-caller patch, not a partition flip); #2453 is 36 sites not ~71; #2100 is 60 sites and the
> ratchet must be non-vacuous. **Honest size: 15–17 WPs.**

## Purpose (stakeholder-facing)

**TL;DR**: Finish the read side — route the remaining coordination-surface *reads* through their canonical
authorities, close the write-routing **defect class** that leaves the accept-matrix stale (at the seam, not
per-caller), and close epic #1716.

The write-side placement mission (PR #2462) locked **where** every mission artifact is *written* (one
topology-aware `PlacementSeam`). This mission does the **read counterpart** plus one write-side class-closure:
route the last kind-blind `resolve_feature_dir_for_mission` reads onto `read_dir(kind)`, route the last inline
`meta.json` reads onto the canonical `load_meta` authority, make the kind-aware commit router **partition-aware
per file** so coordination artifacts stop landing on the primary branch (the root of the stale-accept-matrix
bug), and close the two remaining open children of epic #1716. Each thread is *extract → route → enforce*
behind a non-vacuous tightening ratchet.

## Scope (four threads)

### Thread A — feature_dir read sweep + coord_authority drain (#2453) · ~6 WPs
Route the **25 READ** `resolve_feature_dir_for_mission` sites (+ the **4** `resolve_feature_dir_for_slug` sites,
currently outside the gate) onto `placement_seam(...).read_dir(kind)`. Drain the `coord_authority` ratchet
**7 → 2** (2 permanent by-design: `decisions/emit.py:71`, `widen/state.py:63`). **Per-site adjudication is
binding** (the gate's function-level `is_write` flag labels all 5 drainable as writes — do NOT trust it; use
the manual read/write split): `implement.py`@1468/1663/1169 are reads (→`read_dir`); **`workflow.py:2747`**
(the `review` sub-artifact dir: `mkdir` + `review-cycle-N.md`) is a **genuine write** (→`write_target`) — note
`review` has TWO drainable sites, `@2710` (read) + `@2747` (write); the allow-list locator says `2670` but the
live site is `2747` (freshen). Reclassify the two status-write false-negatives (`lanes/recovery.py:755`,
`agent_tasks_ports.py:322`) as **writes** via `_COORD_WRITE_BY_DESIGN` / widening the write-indicator
predicate — **never route them** (`recovery.py:755` carries an explicit "MUST stay coord-aware — never route
it" directive; it feeds `emit_status_transition_transactional`). Fix the residual fail-closed fallback at
`orchestrator_api/commands.py:1451` red-first.

### Thread B — inline meta.json read sweep + new ratchet (#2100) · ~6–7 WPs
Route the remaining inline `json.loads(<meta_path>)` reads (**~50 sites** after the migration deferral) onto
`load_meta` / `load_meta_strict` / `load_meta_or_empty` (`mission_metadata.py`), matching each site's
`allow_missing`/`on_malformed` contract. Do **not** route `mission_metadata.py` internals or the `task_utils`
adapter. For `coordination/transaction.py`, route its meta reads **outside** the C-004-frozen 751-771 block +
a byte-unchanged regression on that block. For `src/runtime/next/` sites, respect the shared-package boundary
(route onto `specify_cli.mission_metadata.load_meta` only where a `specify_cli` import is already sanctioned;
otherwise defer or stand up a runtime-local authority — a plan-time call). **Establish** the first tightening
ratchet for this debt as a *dedicated* WP (not folded into routing) — see FR-006 for the non-vacuity contract.

### Thread C — accept-matrix write-routing: close the class at the seam (#2404) · ~2–3 WPs — NOT a partition flip
Do **not** re-kind `ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` (C-002 — unsound; reverses the #2462-locked partition
and fails `test_write_surface_placement_guard.py`). The read side is already correct. The matrix is stale
because coordination artifacts are **written to the primary branch** by a seam that classifies a whole
multi-file batch under one caller-supplied `kind` (`commit_for_mission` → `resolve_placement_only(kind=…)` at
`commit_router.py:152`). **Fix the class at the seam (Directive-043, C-006):** make `commit_for_mission`
per-file partition-aware (group by partition, commit each group to its own ref) *or* guard-reject a
mixed-partition batch. That closes `spec_commit_cmd.py` (`kind=SPEC`) and `mission_finalize.py:1320`
(`kind=TASKS_INDEX`, batching `acceptance-matrix.json`/`issue-matrix.md`/`status.*`) **by construction**. Then
route `accept.py::_commit_residual_acceptance_artifacts` through the now-partition-aware seam (it currently
raw-`git commit`s) **and reconcile its dirty-detection surface** (it scans primary `git status`, but the
accept-time `write_acceptance_matrix` writes to the *coord* worktree — a coord-worktree edit never shows in
primary status). Coord-topology regression across all three write paths.

### Thread D — #1716 closeout (#2088) · ~1 WP (split)
`#2088` (ownership-overlap validator dependency/lane-awareness) is **already fixed** on `main` (commit
`69dd1fa46`, verified ancestor of base, 16 tests green). **Close #2088 early** (independent of #2462). Then
**close epic #1716** — gated on: (a) #2462 merged to `upstream/main` (it carries the planning-on-primary
retirement + the seam), and (b) a plan-time enumeration confirming #1716 has **no** open children beyond
#2088/#2100.

## Cross-Thread Linearization (binding for `/tasks`)

**The single biggest decomposition risk.** These **9 files are touched by BOTH Thread A (feature_dir) and
Thread B (meta)** — their A-edit and B-edit **cannot** be split across different lanes with disjoint
`owned_files`. They MUST be co-owned in one WP or sequenced same-lane (the pattern #2088's now-dependency-aware
overlap validator explicitly enables — Thread D underwrites this mission's own decomposition):

`cli/commands/implement.py`, `orchestrator_api/commands.py` (also carries A's FR-004 fix), `context/resolver.py`,
`decisions/service.py`, `doctrine_synthesizer/apply.py`, `lanes/recovery.py` (triple-loaded: A feature_dir +
FR-003 predicate + B meta), `cli/commands/_identity_audit.py`, `missions/plan/plan_interview.py`,
`missions/plan/specify_interview.py`.

Plus a package-proximity 3-way in `acceptance/` — `accept.py`/`spec_commit_cmd.py` (Thread C), `__init__.py`
(Thread A), `matrix.py` (Thread B): keep `owned_files` **file-granular, never `acceptance/` dir-level**.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Route the 25 READ `resolve_feature_dir_for_mission` sites + the 4 `resolve_feature_dir_for_slug` sites onto `placement_seam(...).read_dir(kind)`; no lifecycle read re-derives the feature dir from a raw resolver/path. | Draft |
| FR-002 | Drain `coord_authority` 7→2 using the **manual** per-site read/write split (not the gate's `is_write` flag): reads→`read_dir`, `workflow.py:2747`→`write_target`; shrink floor + margin + allow-list; freshen the stale `2670`→`2747` (and other) line locators. | Draft |
| FR-003 | Reclassify the two status-write false-negatives (`lanes/recovery.py:755`, `agent_tasks_ports.py:322`) as writes via `_COORD_WRITE_BY_DESIGN`/predicate-widen — never route them. This FR **precedes** FR-002's floor re-pin (it moves the live write count). | Draft |
| FR-004 | Fix `orchestrator_api/commands.py:1451` fail-closed: an `ActionContextError` raises/propagates a structured error, never `CommitTarget(ref=current_branch)`. Red-first. | Draft |
| FR-005 | Route the inline `meta.json` reads (census-directional ~50–63 sites; the IC-06 scanner is the authoritative tie-breaker) onto `load_meta`/`load_meta_strict`/`load_meta_or_empty` with the matching contract. **Each site's `allow_missing`/`on_malformed` derives from POST-#2091 semantics, NOT the pre-#2091 local try/except:** a site that now hard-fails at the #2091 guard routes to `load_meta_strict`/`allow_missing=False` — routing it to `allow_missing=True` would MASK the guard and silently re-introduce the removed legacy tolerance. Exclude `mission_metadata.py` internals + the `task_utils` adapter; `transaction.py` reads routed **outside** 751-771 with a byte-unchanged guard on that block; `runtime/next` sites respect the shared-package boundary. | Draft |
| FR-006 | Establish a **non-vacuous** tightening ratchet for inline meta reads: concrete integer floor + margin + a **routed-count floor** (anti-mass-allow-list, mirroring `ROUTED_CANONICALIZER_FLOOR`) + composite-key allow-list with **stale-entry detection** + per-entry rationale. Every deferred site is an explicit allow-list entry carrying a rationale **and a filed follow-up issue number** (not a prose note). | Draft |
| FR-007 | Make the `commit_for_mission` **seam** per-file partition-aware (group files by partition, commit each group to its own ref) or guard-reject a mixed-partition batch — closing the wrong-kind-commit class by construction (fixes `spec_commit_cmd.py` `kind=SPEC` and `mission_finalize.py` `kind=TASKS_INDEX` without per-caller patches). **`kind_for_mission_file` returns `None` for unrecognized paths (gap-analysis, generator-config) — the per-file grouping MUST retain the caller-supplied `kind` as the fallback for `None`-classified files, keep single-partition batches on the fast path, and thread residue-cleanup per group.** Red-first proving BOTH a mixed batch misroutes AND a `None`-file batch still lands correctly. | Draft |
| FR-008 | Route `accept.py::_commit_residual_acceptance_artifacts` through the partition-aware seam (not raw `git commit`) **and** reconcile its dirty-detection surface with the write-back surface: detect coord-worktree dirt where `write_acceptance_matrix` writes (coord `feature_dir`), not only primary `git status`. | Draft |
| FR-009 | (#2404) Coord-topology regression: `acceptance-matrix.json` filled + committed via **each** path (`spec-commit`, `finalize`, `accept` residual) lands on the coordination surface and is read back by `accept` — no stale copy. | Draft |
| FR-010 | (#2088/#1716) Verify `69dd1fa46` on base; close #2088 early; then close epic #1716 gated on #2462 merged + a plan-time check that #1716 has no open children beyond #2088/#2100. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Routing resolves the **kind-correct** surface. For most sites this is behaviour-preserving (same physical dir, now via the authority). BUT for PRIMARY-kind reads under **coord topology** the kind-aware `read_dir` legitimately resolves a *different* surface than the old kind-blind resolver (coord husk → primary): that divergence **is** the #2453 fix (the husk can shadow real primary planning truth), not a regression. Characterization tests MUST assert the kind-correct **post-fix** surface and MUST NOT pin the old kind-blind coord dir (would freeze the bug / go red on the fix — Directive-041); carry a coord-topology divergence regression. kind→partition mapping unchanged (C-002). | Per-site kind adjudication decides *whether the physical surface moves*, not only `read_dir` vs `write_target`; coord-topology divergence regression present. | Draft |
| NFR-002 | Both ratchets are shrink-only and non-vacuous. | coord_authority floor 7→2 with a valid margin; the new meta gate has floor + margin + **routed-count floor** + stale-entry detection; a re-introduced inline read/raw resolver goes RED; the allow-list cannot silently swallow the census. | Draft |
| NFR-003 | New/changed code passes the quality gates. | `ruff` + `mypy` zero issues; per-function complexity ≤15; new branches/helpers carry focused tests in the same WP. | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Route through the canonical authorities only. **Honesty note:** `read_dir` forks RETROSPECTIVE to `resolve_retrospective_home`, and ~70 sites call the `*_feature_dir_for_mission` primitives directly — the ratchet covers the gated resolver, not every primitive call; do not claim a single funnel beyond what the gate enforces. | Draft |
| C-002 | **Do NOT change the kind→partition mapping** (#2404 is write-routing, not a re-kind — a flip reverses the #2462-locked partition + fails `test_write_surface_placement_guard.py`). Verified sound by the squad. | Draft |
| C-003 | **Depends on PR #2462 merging** for Threads A/C and — via the 9 cross-thread collision files — for the parts of Thread B co-owned with A. Only the *non-colliding* Thread B files + Thread D's #2088-close are truly #2462-independent. Rebase this branch onto merged `upstream/main` before implementing A/C. | Draft |
| C-004 | Leave `coordination/transaction.py:751-771` legacy HEAD override untouched (#1878 territory); route the file's *other* meta reads, guard the block byte-unchanged. | Draft |
| C-005 | Red-first for every new guard/routing/fix (FR-004, FR-007, FR-008). | Draft |
| C-006 | Close the #2404 wrong-kind-commit class **at the seam** (`commit_for_mission`), not per-caller (Directive-043). Per-caller-only patches are rejected — the next caller reintroduces the class. | Draft |
| C-007 | Plan-gate: re-run the gate's own scanner to record the live READ/WRITE/by-design split for Thread A, and enumerate #1716's open children, **before** `/tasks` sizes the mission. | Draft |

## Success Criteria

- **SC-001**: 0 lifecycle reads re-derive the feature dir via a raw resolver/path outside documented primitives; `coord_authority` at floor 2 (after FR-003 precedes FR-002); the 2 status-write false-negatives reclassified.
- **SC-002**: Inline-meta reads drained to the ratchet floor; the ratchet bites on a re-introduced read AND cannot be mass-allow-listed (routed-count floor holds).
- **SC-003**: On a coord-topology mission, `acceptance-matrix.json` written via `spec-commit`, `finalize`, AND `accept` all land on coord and are read back by `accept` — the wrong-kind-commit class is closed at the seam (a new mixed-partition-batch caller cannot reintroduce it).
- **SC-004**: #2088 closed; #2100 closed; **epic #1716 closed** (post-#2462-merge, children-enumeration confirmed).
- **SC-005**: No new shadow path; kind→partition mapping unchanged; `ruff`/`mypy` clean.

## Key Entities

- **`PlacementSeam.read_dir(kind)` / `write_target(kind)`** — feature-dir read/write authority (from #2462).
- **`load_meta` / `load_meta_strict` / `load_meta_or_empty`** — meta.json read authority (`mission_metadata.py`).
- **`commit_for_mission` + `kind_for_mission_file`** — the kind-aware commit router (to be made partition-aware) + the per-file classifier.
- **`coord_authority` ratchet + the new meta-read ratchet** — the enforcement gates.

## Assumptions

- PR #2462 merges before Thread A/C implementation; this branch rebases onto the merged base.
- The `resolve_feature_dir_for_mission` census is re-run at plan time via the gate's own scanner (C-007); the "~71" figure is stale (live ≈ 36 production sites).

## Dependencies

- **Hard**: PR #2462 (`PlacementSeam`, partition-aware commit context) for FR-001/002/003/007/008.
- **Advances/closes**: #1716 (SC-004), #2453, #2404; #2088/#2100 as its children; under #2160/#1619.

## Out of Scope

- **Migration-script meta reads** — the deferral is limited to the *historical-fixture-sensitive* set `upgrade/migrations/m_0_13_*.py` only. `migration/backfill_*`, `migration/mission_state.py`, `migration/rebuild_state.py` are **not** blanket-deferred (they are #2100-in-scope): route them, or allow-list each with a per-site rationale + filed issue. No wholesale `migration/` path-exclude.
- **The `ACCEPTANCE_MATRIX`/`ANALYSIS_REPORT` partition flip** — rejected (C-002).
- **`transaction.py:751-771` legacy HEAD override** — #1878 (C-004).
- **`mission_record_analysis.py` analysis-report commit** — verified correct (`kind=ANALYSIS_REPORT`, COORD); NOT the #2404 bug class.
- The duplicated `_get_mission_id` helper in `plan_interview`/`specify_interview` — S1192-adjacent note, not required here.

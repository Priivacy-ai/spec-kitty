---
affected_files:
- path: tests/architectural/test_gate_read_literal_ban.py
cycle_number: 1
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: uv run python -c "import sys,ast;sys.path.insert(0,'.');from
  tests.architectural.test_gate_read_literal_ban import _WRITE_ARM_SURFACES,_find_function,write_arm_anchors;
  [print(s.rel_path,s.func,write_arm_anchors(_find_function(ast.parse(open(s.rel_path).read().replace('primary_feature_dir_for_mission(','placement_seam(repo_root,slug).read_dir(MissionArtifactKind.PRIMARY_METADATA)#(')),s.func)))
  for s in _WRITE_ARM_SURFACES]"
reviewed_at: '2026-07-28T12:20:00Z'
reviewer_agent: reviewer-renata
verdict: changes_requested
wp_id: WP01
---

# WP01 Review — CHANGES REQUESTED (one defect, in T002)

Commits `13ed4a279` + `333614aa8`. This is strong work and most of it is verified correct
against the tree, not merely against the prompt. **One defect blocks**, and it is in the one
place the Reviewer Guidance singles out as highest-value: T002's positive write-arm assertion
does not survive this mission's own migration, and the WP records the opposite.

Everything I verified independently is listed under "Verified" so cycle 2 does not re-litigate
settled ground.

---

## BLOCKING — B1. T002's post-migration recognition path is inert for all three real subjects; the assertion will oblige a DELETED name

**Where**: `tests/architectural/test_gate_read_literal_ban.py`, `write_arm_anchors` /
`_builds_meta_path_from_primary_seam` / `_anchor_invoked_in`.

**What T002 step 3 required** (verbatim): *"Track the post-migration spelling: after WP08 the
public name is gone, so anchor the assertion on the surviving private leaf, not on the deleted
wrapper."*

**What landed**: `reads_via_primary` is the disjunction of three signals. For each of the three
enumerated `_WRITE_ARM_SURFACES`, only ONE of them fires today —
`_anchor_invoked_in(func, _WRITE_PRIMARY_ANCHOR)`, i.e. *"is
`primary_feature_dir_for_mission` called in this function"*. That is the exact public name
FR-006 / WP08 T035 **deletes**.

**Mutation evidence** (three surfaces × four mutants, run against the live tree; no repository
file was modified):

| Mutation applied to the real surface body | `(candidate, primary)` | Node verdict |
|---|---|---|
| baseline | `(False, True)` | green |
| M1 `primary_feature_dir_for_mission` → `candidate_feature_dir_for_mission` | `(False, False)` | **reds** ✅ |
| M2 `primary_feature_dir_for_mission` → unrelated third resolver | `(False, False)` | **reds** ✅ |
| **M3 → post-migration seam idiom `placement_seam(...).read_dir(PRIMARY_METADATA)`** | **`(False, False)`** | **reds — SHOULD BE GREEN** ❌ |
| M4 → `read_dir(STATUS_STATE)` through the same call shape | `(False, False)` | reds ✅ (kind discipline holds) |

M1/M2 confirm the assertion genuinely bites today — the discarded-signal version passed both.
**M3 is the defect**, and it failed identically on all three surfaces:
`core/paths.py::get_feature_target_branch`, `core/git_ops.py::resolve_target_branch`,
`mission_finalize.py::finalize_tasks`.

**Root cause**: `_builds_meta_path_from_primary_seam` requires a literal
`<dir> / "meta.json"` `BinOp`. The WP's own commit body correctly diagnoses that **none of the
three surfaces contains that join** — they are thin adapters that hand the dir to
`read_target_branch_from_meta`. I confirmed this by reading all three bodies. So the branch
presented as *"the surviving spelling after WP08 deletes `primary_feature_dir_for_mission`"*
**cannot match any of its own subjects, in any world**. The thin-adapter recognition
(`_anchor_invoked_in`) was wired only to the deleted wrapper, never to the seam.

**Why this is not cosmetic** — it is the defect class this WP exists to remove, reintroduced on
the write arm:

1. **It fires, unrecorded, in two later WPs.** `mission_finalize.py:1645` is inside
   `finalize_tasks` (1589–1788) and is a **WP06** routing target; `core/paths.py` ×2 and
   `core/git_ops.py` are FR-005 foundation sites that must leave the public wrapper when **WP08**
   deletes it. In each case `reads_via_primary` → False → the node reds. Nothing in
   `research/expected-reds.md` predicts it, so it will present as a fresh regression — the exact
   misattribution SC-020 and this WP's stated bar exist to prevent.
2. **Its failure message instructs the implementer to resurrect a deleted primitive**: *"the
   resolver must POSITIVELY anchor on `primary_feature_dir_for_mission`"*. A gate obliging the
   drained primitive to keep being used is precisely what T003 retires nine hundred lines away.
   This is the mission's named "single most dangerous failure mode" (fixing the product to keep a
   defunct gate green) with a signpost pointing at it.
3. **The WP asserts the opposite in three places** — `write_arm_anchors`' docstring, the commit
   body, and the `## WP01` section of `research/expected-reds.md` all claim the seam form is "the
   surviving spelling". A reviewer or later implementer reading any of them will believe the
   post-migration case is covered. That claim is falsified above.

**What would close it** (your call on shape; do not treat this as a spec):

- Add the thin-adapter analogue for the seam — you already have the primitive:
  `_names_bound_from_primary_read_dir(func)` yields exactly *"names bound from a
  PRIMARY-partition `read_dir(kind)`"*. Recognising a dir so bound (or a
  PRIMARY-partition `read_dir` call occurring in the function at all) as primary-anchored is the
  direct counterpart of `_anchor_invoked_in`, needs no information WP03 has not produced yet,
  and keeps the kind discrimination that M4 proves is load-bearing.
- Then re-run the M3 mutation (recipe in `reproduction_command`, or the four-mutant harness) and
  show `(False, True)` for all three surfaces.
- If any residual post-migration red genuinely cannot be eliminated from this lane, it must be
  **recorded in `## WP01` with its FR and greening WP**, and the failure message must name the
  *target* anchor rather than the deleted wrapper. An unrecorded red is the one outcome this WP
  is not allowed to hand off.

---

## Non-blocking — flagged, do not spend a cycle unless it is cheap

**N1. `reads_via_candidate` stays literal-join-only, so the negative arm is vacuous for all
three real subjects.** A candidate-anchored *thin adapter* would not be flagged by
`reads_via_candidate`. Coverage is preserved indirectly — my M1 mutation shows the new positive
arm catches exactly that regression — and the deferral is stated honestly in the docstring. No
action required; just do not let a future cycle read the negative arm as protection it is not
providing.

**N2. The trio positive arm now obliges `resolve_handle_to_read_path` to stay imported.**
`assert used & _SEAM_ALLOWED_READ_PATH_RESOLVER_NAMES` fails if the trio imports *nothing* from
`_read_path_resolver`. Simulated: post-WP05 `used = {resolve_handle_to_read_path}` → both
assertions pass (WP05 does not touch the two surviving function-local imports at
`workflow.py:356` and `acceptance/__init__.py:722`), so **WP05 can green it as recorded**. But
`used = ∅` → red. This is the same "must remain in use" shape one level up, on the seam entry
point rather than the leaf. Defensible as anti-vacuity; worth a sentence in the docstring
naming the two imports the assertion depends on, so a later routing pass does not remove them
blind.

**N3. Node name is now a misnomer.** `test_allowed_read_path_resolver_names_are_currently_used`
asserts *non-reacquisition*, not *currently-used*. Keeping the node id stable is the right call
for the gate-coverage baselines and the docstring explains the change — noted only so it is not
mistaken for drift.

**N4. The required foreign-honest-red P0 section (T007 step 3) sits under the `## WP02` section**
of `research/expected-reds.md`, not `## WP01`. Content is present and correct (`#3031`,
`tests/sync/test_sync_consent_default_deny.py`, by-surface rule); duplicating it would be worse.
Requirement met at file level — recorded here only so the reconciliation in WP08 T039 knows
where it lives.

---

## Verified — settled, do not re-litigate in cycle 2

- **Check 1 — every widening is kind-discriminated. PASS.** PRIMARY is resolved through
  `mission_runtime.artifacts.is_primary_artifact_kind` over the `_PRIMARY_ARTIFACT_KINDS`
  frozenset; no kind list is hardcoded in the test (`STATUS_STATE` → False, `LANE_STATE`/`SPEC`
  → True, confirmed live). `_PRIMARY_FOLD_CALLSHAPE_FUNCS` gained no member. **Both** consumption
  sites are unioned — `callshape_violations` and `_caller_binds_arg_coord_aware` here, and
  `test_coord_read_residuals_closeout.py::test_no_status_leg_rerouted_to_primary` — and that node
  acquired no new failure. Discrimination is load-bearing, not decorative: I monkeypatched
  `_is_primary_partition_read_dir_call` to be callee-name-blind and the STATUS binding was
  immediately classified primary-bound (the negative-case node reds under the mutant, passes
  under the real predicate).
- **Check 2 (T006 half) — the trio assertion bites. PASS.** It reds on the *live* tree against 2
  real reacquired names across 5 files — a live bite, not a synthetic one. M6 anti-vacuity holds
  under mutation: with `blessed = frozenset()` the helper still flags every import, so its teeth
  do not depend on the blessed set's size. `used - blessed` is the correct direction; the retired
  `blessed - used - {…}` shape was provably the empty set post-shrink.
- **Check 3 — retirement bookkeeping. PASS.** Before/after integers recorded
  (`CANONICALIZER_FLOOR` 44; `ROUTED_CANONICALIZER_FLOOR`/`_MARGIN` 40/4), the reason stated as a
  **retirement** with the "routing shrink, not a re-pin" precedent cited as annotation template,
  the `DIRECTIVE_043` transfer-not-abandonment adjudication spelled out (to WP02's bypass census,
  with its own concrete floor + per-primitive non-vacuity + alias resistance + shrink-only
  allow-list), and `DIRECTIVE_041` dispositions named per change. Present in the commit body, in
  the retirement comment blocks of both modules, and in `## WP01`.
- **Check 4 — zero collection errors, zero `src/` changes. PASS.** 169 tests collected across
  the six C-008 gates, 0 errors. Diff touches only 5 files, all under `tests/architectural/`.
- **Check 5 — classification by surface. PASS.** All 3 reds are on placement/read-path surfaces
  this mission owns. `tests/sync/test_sync_consent_default_deny.py` correctly excluded (C-010).
- **Reconciliation. PASS, exactly.** My own run of the six gates:
  **166 passed / 3 failed / 0 collection errors**, and the 3 failures are node-for-node the 3
  rows recorded in `## WP01`. No unpredicted red. All 3 are assertion failures about behaviour,
  each traceable to a named FR (FR-014 → WP04; FR-004/FR-005 → WP05; FR-004/FR-012 → WP05).
- **Census figures re-derived from the tree, not read.** quickstart §1 alias-resolving recipe +
  the gate's own scanner: **46 total canonicalizer call sites / 43 routed** — matches. Closeout
  module's own `_count_read_call_sites`: **24 identity / 10 lanes** — matches the corrected
  figure; the +2 (not off-by-one) correction is right, and leaving the floor at 18 is correct.
- **The deleted test — deletion UPHELD.** `test_routed_canonicalizer_floor_matches_recorded_census`
  carried four assertions: two `==` pins on the retired constants, and two bound checks that were
  literal duplicates of the retired `test_routed_count_floor`'s own bounds. Every one of them
  referenced a constant being retired; the module's **site floor** (its real non-vacuity) was
  correctly kept. I checked the one thing that would have made deletion wrong — whether
  `scan_canonicalizer_call_sites` lost all coverage — and it retains **7** other consumers in
  `test_resolution_authority_gates.py`, so the scanner is still exercised. `DIRECTIVE_041`
  disposition STALE is the right call and is recorded; `tactic:delete-the-assertion-not-the-test`'s
  burden of proof ("provably zero-coverage") is discharged. Retiring it in the same commit as
  T003 was mandatory (`DIRECTIVE_034` collection-error hazard) and was done.
- **T005 pin + pin-existence test removed in one commit.** Confirmed in `13ed4a279`.
- `ruff check` on all four changed test modules: clean. No new suppressions anywhere in the diff.
- The three planning contradictions the WP reported rather than silently resolving (absent YAML
  block; +2 not off-by-one; the unowned stale comment in `test_inline_meta_read_gate.py:24`) are
  planning inaccuracies, correctly reported, **not** counted against this WP. Same for landing
  `## WP01` on the planning branch.

## Verdict

**CHANGES REQUESTED** on B1 alone. Fix the post-migration recognition path (or record the
resulting red with its greening WP and a message that names the target anchor), re-run the M3
mutation on all three surfaces, and correct the three places that currently claim the seam form
is the surviving spelling. Nothing else in this WP needs to move.

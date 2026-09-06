# Tracer: Design Decisions

Mission: runtime-advance-guard-topology-wp-completion-01M1W6VZ (issues #3883, #3884)

## Decision: `mission_slug` is a new optional parameter on `gather_artifact_presence`,
defaulting to a `feature_dir.name` fallback when omitted

Rationale: `placement_seam(repo_root, mission_slug)` needs both values, but no
function in the current call chain (`_check_cli_guards`, `_check_composed_action_guard`,
`_dispatch_via_composition`) carries `mission_slug` today. Every real production
call site (`_dn_dependency_gate`'s two branches, `_dn_composition_dispatch`) already
has `ctx.mission_slug` in scope, so production correctness never relies on the
fallback. The fallback exists for backward compatibility with existing test call
sites and to make spec.md's own elliptical Independent Test call shape
(`_check_composed_action_guard("tasks", coord_worktree_feature_dir,
mission="software-dev")`, no `mission_slug` shown) still resolve correctly.
Precedent for the fallback shape: `_mission_slug_from_feature_dir`
(`src/runtime/next/_internal_runtime/retrospective_terminus.py:63-65`) already does
`feature_dir.name` as a documented best-effort derivation elsewhere in this
codebase.

**Open item for WP1**: confirm empirically, against a real coord-topology fixture,
that `feature_dir.name` for a coordination worktree equals the exact slug (or
`<slug>-<mid8>` composed form) `placement_seam` expects. If it does not hold for
some naming variant, the red-first tests must pass `mission_slug` explicitly and
this fallback note should be updated to say so plainly (not deleted — the fallback
still matters for the other call sites that never supply it).

**2026-09-07 (WP02, T002) — resolved, CONFIRMED**: built a real coord-topology
fixture (`tests/runtime/next/test_coord_topology_fixture.py`'s
`build_coord_topology_fixture` — a genuine git repo, a real coordination branch,
and `specify_cli.missions._read_path_resolver.coord_feature_dir`'s actual
composed directory; no resolver patched) and asserted BOTH forms against
`mission_runtime.placement_seam(repo_root, <slug>).read_dir(
MissionArtifactKind.WORK_PACKAGE_TASK)`: the bare `mission_slug` resolves to
`primary_dir` (as expected), AND the coordination worktree's genuine
`feature_dir.name` — verified to be the composed `<slug>-<mid8>` form, never
the bare slug, for a real coord worktree — resolves to the IDENTICAL
`primary_dir`. Root cause: `resolve_artifact_surface`'s backfilled-primary-dir
idempotence path (`resolution.py`'s `_backfilled_primary_dir`) absorbs the
composed suffix before classification. **Conclusion for WP01**: the
`feature_dir.name` fallback is safe for this shape as written; no reproduction
needs to pass `mission_slug` explicitly to route around a mismatch. See
`tests/runtime/next/test_coord_topology_fixture.py::TestT002MissionSlugFallbackSpike`
for the runnable proof (both directions asserted, not merely one).

## Decision: anchoring gates on `repo_root is not None`, not a separate flag

Reuses the #3704/WP02 precedent verbatim: `repo_root` already means "the caller
opted into org-tier/primary-aware resolution," and every production caller already
passes a real one. This also makes the fix a true no-op for `single_branch`
topology (this mission's own repo) by construction — `placement_seam(...)` resolves
to the same directory `feature_dir` already denotes for that topology, not via a
special-cased branch.

## Decision: `PrimaryPlacementResolutionError` lives in `runtime_bridge_io.py`, not
a shared/kernel location

Both consumer modules (`runtime_bridge.py`, `runtime_bridge_composition.py`)
already import `runtime_bridge_io` under the `_io_seam` alias, so no new import
edge is needed. Mirrors where `CanonicalStatusNotFoundError` is already imported
from for this same module.

## Decision: `_check_composed_action_guard` catches the new exception and returns
`[str(exc)]` (a non-empty failure list), not a `Decision` object

This function's existing return contract is `list[str]`; it has no Decision-
construction code today and adding one would duplicate logic its own callers
(`_dn_composition_dispatch` via `_dn_composition_blocked_decision`) already own. A
non-empty list is exactly what those callers already convert into a `blocked`
Decision. Opposite polarity from the adjacent `UnregisteredMissionFamilyError`
handling in the same function (which degrades to `[]` = unblocked) — flagged
explicitly so an implementer does not copy the wrong polarity by pattern-matching
the neighboring `except` block.

## Decision: `_wp_blocks_step`'s fix is one new `or`-disjunct, not a restructure

`lane is Lane.UNINITIALIZED or state.is_blocked or (...)` — added at the front of
the existing `implement`-branch return expression. Confirmed via
`src/specify_cli/status/wp_state.py` that `UninitializedState` is neither
`is_blocked` nor `is_run_affecting`, which is the exact root cause (it falls
through both existing disjuncts by omission). No restructuring of the
`is_acceptable_ending` early-return, the `review` branch, or
`_should_advance_wp_step`'s no-`tasks/`-dir early return.

## Decision (tasks phase, 2026-09-07): mandatory 3-WP repartitioning, overriding
plan.md's own WP1a/WP2 split

plan.md's "Phasing" section proposed WP1a (FR-004/005's `_wp_blocks_step` fix)
and WP2 (FR-001/002/003/006/008's `gather_artifact_presence` fix + the Seam 2
extension) as separate work packages relying on "disjoint line ranges" inside
the same file (`runtime_bridge.py`) plus a `dependencies: [WP1a, WP1b]` edge to
avoid a same-file merge conflict at `spec-kitty merge` time. The tasks phase's
`wps.yaml` `owned_files` contract requires glob patterns to be pairwise
non-overlapping **at the file level** across every work package, not only at
the line level within a dependency-ordered pair — so WP1a and WP2 are folded
into ONE work package (`WP01` in this mission's `wps.yaml`) that owns
`runtime_bridge.py`, `runtime_bridge_composition.py`, and `runtime_bridge_io.py`
outright. plan.md's WP1b becomes `WP02` (independent, no production code,
`dependencies: []`); plan.md's WP3 becomes `WP03` (`dependencies: [WP01]`).
This changes WHICH WP the same work lands in — not the fix design, not the
settled Test Strategy (all six adversarial review rounds' findings carry
forward verbatim into `tasks/WP01-merged-production-fix.md`). The resulting
`WP01` is ~827 lines and 12 subtasks, well over the normal 3-7/max-10 sizing
guideline — this is by construction (the `owned_files` disjointness
requirement overrides the sizing guidance here), not an oversight; see
`tasks/WP01-merged-production-fix.md`'s own Context/Risks sections for the
full statement of why it is not split further. See `wps.yaml` for the
authoritative WP definitions; `WP03` (`tasks/WP03-regression-sweep-baseline-reverify.md`)
appends the corresponding closing sequencing note to `tracer-approach.md` at
implementation time.

## Decision (2026-09-07, operator ruling): narrow this mission from #3883+#3884 to
#3884 only

Verified, not assumed: draft PR #3923 (`codex/upgrade-preview-mission-health`, base
`main`) already fixes #3883 in `src/runtime/next/runtime_bridge_io.py`, via a
kind-aware placement seam (`_artifact_presence_read_dir` / `kind_for_mission_file` /
`placement_seam`) — an independently-invented, further-progressed mechanism than
this mission's own (now-deleted) `resolve_primary_anchor_dir`/
`PrimaryPlacementResolutionError` design for the same bug. Confirmed via the
paginated GitHub API (the truncated-at-100 `gh pr view --json files` hides this): PR
#3923 has 125 changed files, touches `runtime_bridge_io.py`, and mentions
`gather_artifact_presence` 9 times in its diff. Equally confirmed: PR #3923 does
NOT touch `src/runtime/next/runtime_bridge.py`, and its diff has zero mentions of
`_wp_blocks_step`, `_should_advance_wp_step`, or `UninitializedState` — so #3884
remains entirely this mission's own work.

**Removed**: the former User Story 1 / Seam 1 design in full — FR-001/002/003/006/
007/008, NFR-002, C-001 through C-005, `resolve_primary_anchor_dir`,
`PrimaryPlacementResolutionError`, the 8-row `mission_slug` call-site threading
table, and the five FR-006 catch sites across three files.

**Kept, unchanged**: FR-004/FR-005 (`_wp_blocks_step`'s `Lane.UNINITIALIZED`
disjunct) — always independently #3884's, sharing no implementation seam with
#3883.

**Kept, re-derived**: the former "Seam 2 extension" (PLAN-FIT-001) —
`_should_advance_wp_step`'s own separate, unanchored `tasks_dir` read in
`runtime_bridge.py`, which makes FR-004's fix unreachable for a real
COORD-topology mission unless anchored too. This survives as explicit spec.md
requirements FR-009/FR-010, re-derived (not merely carried forward) in two ways:
(1) with Seam 1 gone, there is exactly one caller left for the anchoring logic, so
it is now written INLINE in `_should_advance_wp_step` against the already-existing
`mission_runtime.placement_seam(...)` primitive `runtime_bridge.py` already
imports elsewhere — no new shared helper, no new exception class; (2) this
narrowing ran the previously-deferred "which exception does a corrupt/missing
`meta.json` fixture raise" empirical spike directly, against the actual kind
FR-009 uses (`MissionArtifactKind.WORK_PACKAGE_TASK`, not `PRIMARY_METADATA`), and
found the original assumption did not hold: resolving a PRIMARY-partition kind's
directory is pure path composition, never a `meta.json` content read, so a
corrupt/missing `meta.json` does not raise here at all. The one exception that CAN
fire is the already-existing `MissionSelectorAmbiguous`, for a genuinely ambiguous
`mission_slug` handle — confirmed empirically against this checkout (`placement_seam(
repo_root, "totally-bogus-mission-slug-zzz").read_dir(MissionArtifactKind.
WORK_PACKAGE_TASK)` does not raise; it resolves to a real, if absent, `Path`).

**Kept, repurposed**: `wps.yaml`'s WP02 coord-topology fixture. It is genuinely
still needed (the reachability bug is coord-specific by definition — it only
manifests when `feature_dir` is a coordination worktree lacking `tasks/` while
primary has it), but its own reproduction is redesigned to isolate FR-009's bug
from FR-004's using an `in_progress`-claimed WP (which already correctly blocks
under today's un-patched `_wp_blocks_step`) rather than an uninitialized one (which
would conflate the two bugs) — see `tasks/WP02-coord-topology-fixture-repro1.md`'s
Context section for the full isolation rationale.

**Also proven, not merely asserted**: `_check_cli_guards:858`'s and
`runtime_bridge_composition.py:557`'s own internal `_should_advance_wp_step` calls
do NOT need anchoring — both are provably reached only after
`_dn_dependency_gate`'s WP-iteration-branch direct call (`:1680`, the one call site
this mission's fix threads) has already succeeded with byte-identical inputs and
no intervening mutation, for every mission family (registered or not), because
`_dn_dependency_gate` always runs before composition dispatch and always
intercepts a `should_advance == False` verdict for `implement`/`review` steps
first. `runtime_bridge_composition.py` is therefore not touched by this mission at
all, post-narrowing.

## NFR-001 pre-change baseline (WP02, T005, run 2026-09-07, BEFORE WP01's first
production-code commit)

Ran the three exact invocations plan.md's Baseline (NFR-001) section names, on
this branch, with only WP02's own test-only file added (no `src/` change).
Recorded here as this mission's own "before" data point — WP03 diffs its
post-WP01 "after" counts against this entry, not only against plan.md's
original citation.

1. `pytest tests/runtime/next tests/next` (full) — **607 passed**. plan.md
   cites **598 passed**; the +9 delta is exactly WP02's own 9 new tests in
   `tests/runtime/next/test_coord_topology_fixture.py` (4×T001 + 2×T002 +
   2×T003 + 1×T004). Zero net-new reds.
2. `pytest tests/runtime --ignore=tests/runtime/next` — **672 passed, 1
   skipped** (673 collected). Exact match to plan.md's cited baseline,
   byte-for-byte — expected, since this invocation excludes the directory
   WP02's new file lives in.
3. `pytest tests/runtime tests/next tests/specify_cli/next
   tests/specify_cli/status -m "fast or unit"` (fast/unit tier) — **1675
   passed, 1 skipped, 325 deselected**. plan.md cites **1666 passed, 1
   skipped, 325 deselected**; the +9 delta is again exactly WP02's own new
   tests, with the skipped and deselected counts matching EXACTLY.
   **Invocation-ambiguity note for whoever re-runs this**: neither plan.md
   nor spec.md states the literal `-m` flag for this "(fast/unit tier)"
   label — it is not simply `make test-fast`'s own `FAST_TIER_MARKERS`
   (`(fast or unit) and not slow and not e2e and not integration and not
   regression and not distribution and not live_adapter and not stress and
   not windows_ci and not platform_darwin`), which over these four
   directories instead gives **1621 passed, 380 deselected** (a materially
   different split, not merely +9) — confirmed by direct comparison, not
   assumed. The bare `-m "fast or unit"` shown above is the one that
   reproduces plan.md's exact skipped/deselected counts plus WP02's own
   delta, and is therefore the one this mission's NFR-001 baseline actually
   means; cite this exact string, not `make test-fast`'s target, when
   re-verifying.

Classification: all three counts are additive-only (WP02's own new tests),
with zero test outside `tests/runtime/next/test_coord_topology_fixture.py`
changing state. No pre-existing-red, CI-environment, stale-install, or
stale-venv classification was needed — every count is explained in full by
this WP's own new file.

## WP03 (T014/T015) — NFR-001 baseline re-verification and closing summary (2026-09-07)

**Two branches, two legitimately different gate counts — both correct for the tree
they were measured on.** This mission's `lanes.json` routes WP01/WP02 through lane
worktrees (`kitty/mission-runtime-advance-guard-topology-wp-completion-01M1W6VZ-lane-a`,
tip `de115ebc0`; `...-lane-b`, tip `5724a0db5`), reviewed to `approved` in
`status.json` but **not yet merged** into the mission/target branch
`fix/runtime-advance-guard-3883` at the time WP03 ran. Verified, not assumed:
`git merge-base --is-ancestor <tip> HEAD` is false for both lane tips, and
`git diff --stat <merge-base-with-HEAD> <lane-tip>` shows the entire production fix
in `runtime_bridge.py`, all three new test files, and the blast-radius edits to
`tests/runtime/test_bridge_decide_next.py` / `test_bridge_decision_builder.py`
exist only on the lanes. This is expected pre-consolidation state, not a defect —
`lanes.json` itself records `lane-planning` (WP03) as `depends_on_lanes: [lane-a]`
and `lane-a` as `depends_on_lanes: [lane-b]`, i.e. the canonical order is
lane-b -> lane-a -> WP03's own gate re-verification; this mission ran WP03's
baseline pass ahead of that consolidation actually landing.

**Mission-branch (`fix/runtime-advance-guard-3883`, pre-consolidation, unfixed
tree) — measured 2026-09-07:**

1. `pytest tests/runtime/next tests/next` — **598 passed** (run directly by WP03).
2. `pytest tests/runtime --ignore=tests/runtime/next` — **672 passed, 1 skipped**
   (run directly by WP03).
3. `pytest tests/runtime` (bare) — **745 passed, 1 skipped** (run by the
   orchestrator on this same branch).
4. `pytest tests/runtime tests/next tests/specify_cli/next tests/specify_cli/status
   -m "fast or unit"` — **1666 passed, 1 skipped, 325 deselected** (run by the
   orchestrator on this same branch).
5. `make lint` (`ruff check src/`) — clean (run by the orchestrator on this same
   branch).

These five counts are byte-for-byte identical to plan.md's own original Baseline
(NFR-001) citation — expected, since the mission branch at this point carries
neither WP01's nor WP02's diff at all.

**lane-a** (`kitty/mission-runtime-advance-guard-topology-wp-completion-01M1W6VZ-lane-a`,
tip `de115ebc0`, WP01+WP02 fix present) — reviewer-verified, quoted verbatim from
`status.json`'s WP01 `review_result.reference`: "Gates all match: 618, 672+1,
765+1, 1686+1/325, ruff and mypy clean." (Two pre-existing mypy errors, outside
the touched lines, correctly classified baseline-red by that same review.)

**T014 step 6 — diffing the "after" (lane-a) against WP02's own captured "before"
(lane-b's T005 entry, present only on the lane branches, cited in full in the
closing note below) — AGREEMENT, fully explained, zero unclassified deviation:**

| invocation | plan.md static baseline (= mission branch today) | WP02-only, before WP01 (lane-b T005) | WP01+WP02, after fix (lane-a, reviewer-verified) |
|---|---|---|---|
| `tests/runtime/next tests/next` | 598 | 607 (+9: WP02's own new tests) | 618 (+11 more: WP01's own new tests; +20 total) |
| `tests/runtime --ignore=tests/runtime/next` | 672+1 | 672+1 (unchanged — WP02's file lives under `tests/runtime/next`) | 672+1 (unchanged — WP01's two blast-radius edits are modifications, not additions) |
| bare `pytest tests/runtime` | 745+1 | not separately captured by WP02 | 765+1 (+20 — matches the `tests/runtime/next` delta exactly, since this invocation includes that subtree) |
| `-m "fast or unit"` (4 dirs) | 1666+1/325 | 1675+1/325 (+9) | 1686+1/325 (+20) |

Every delta is exactly and only the count of new test functions the two WPs
added (WP02: 9, in `test_coord_topology_fixture.py`; WP01: 11 more, split across
`test_advance_guard_uninitialized_wp.py` and `test_advance_guard_coord_reachability.py`)
— no pre-existing test changed state in either direction, so **no baseline-red
classification is needed anywhere in this table**: this is additive-only
agreement, confirmed by reconciling the file-level diff stats
(`git diff --stat <merge-base> <lane-tip>`) against the numeric deltas above, not
merely asserted.

**Closing note (T015 step 2) — WP01/WP02's lane-only tracer entries, cited in full
for the mission-branch record.** WP02's `mission_slug`-fallback spike (T002) and
NFR-001 pre-change baseline (T005) entries exist today only in the lane-a/lane-b
copies of this file, not yet on this mission-branch copy, because lane
consolidation is still pending (see above). Reproduced here so the mission-branch
record is complete regardless of when the lane merge lands:

- **`mission_slug` fallback: HELD, confirmed empirically (WP02, T002).** A real
  coord-topology fixture (`build_coord_topology_fixture`, zero mocks/patches)
  proved a coordination worktree's genuine `feature_dir.name` is the composed
  `<slug>-<mid8>` form, never the bare slug — and that this composed form
  resolves through `mission_runtime.placement_seam(...).read_dir(
  MissionArtifactKind.WORK_PACKAGE_TASK)` to the IDENTICAL `primary_dir` the bare
  slug resolves to. Root cause: `resolve_artifact_surface`'s
  backfilled-primary-dir idempotence path absorbs the composed suffix before
  classification. Conclusion: this file's earlier "Open item for WP1" is closed —
  the `feature_dir.name` fallback needed no explicit `mission_slug` threading
  beyond what WP01 shipped.
- **Resolving a PRIMARY-partition kind is pure path composition; a corrupt or
  missing `meta.json` does not raise.** Already recorded above in the 2026-09-07
  narrowing entry; re-confirmed by WP01's own T009 implementation, which found
  the one real raise is `MissionSelectorAmbiguous`, caught at exactly one site
  (`_dn_dependency_gate`'s WP-iteration branch, `runtime_bridge.py`).
- **Joint-fix proof: neither disjunct is redundant.** WP01's reviewer
  independently reproduced both single-revert probes: reverting the
  `Lane.UNINITIALIZED` disjunct alone makes the coord-topology assertion fail;
  reverting the anchoring extension alone makes the anchored assertion fail
  while the (unrelated) primary-dir assertion still passes. This is the direct
  empirical answer to whether FR-004/005 and FR-009/010 are two independent
  bugs sharing one call path (they are) — confirmed by the reviewer's own
  independent extraction of both the pre-fix and post-fix `_wp_blocks_step`, not
  merely asserted by the implementer.

**Mid-mission narrowing, restated for this closing summary.** The evidence for
narrowing this mission from #3883+#3884 to #3884-only (recorded in full in the
2026-09-07 narrowing entry above) depended on the **paginated** GitHub API: a
plain `gh pr view --json files` against draft PR #3923 silently truncates at 100
of its 125 changed files, which would have hidden that the PR touches
`runtime_bridge_io.py` at all — nearly causing a correct finding (PR #3923
already fixes #3883 independently) to be dismissed as unverified or false. Only
the paginated call surfaced the `runtime_bridge_io.py` touch and the 9
`gather_artifact_presence` mentions that made the narrowing decision defensible.

## 2026-09-07 — Pre-merge squad follow-up: known interaction with draft PR #3923 (INT-002)

Recorded, not fixed here — this mission's operator ruling was explicit that no
code changes are proposed for this.

The pre-merge integration reviewer (`reviews/premerge-integration.findings.yaml`,
INT-002) found that draft PR #3923 (`codex/upgrade-preview-mission-health`,
`src/runtime/next/runtime_bridge_io.py`, not touched by this mission) builds its
own, independently-designed anchoring for the same `tasks/`-lookup concept inside
`gather_artifact_presence`, and makes the opposite call on the identical
`MissionSelectorAmbiguous` exception this mission's FR-010 hard-blocks on: #3923's
`_artifact_presence_seam` catches `MissionSelectorAmbiguous` (alongside
`ActionContextError`/`StatusReadPathNotFound`) and silently degrades to the
supplied `feature_dir`, logged at DEBUG, never raised. This mission's
`_dn_dependency_gate` (`runtime_bridge.py`, FR-010) catches the SAME exception
from the SAME `placement_seam(repo_root, mission_slug).read_dir(...)` call shape
and converts it into a hard `Decision(kind=blocked, ...)`.

No functional collision exists today: `_dn_dependency_gate`'s anchored,
fail-loud `_should_advance_wp_step` check runs before any guard evaluation that
would consume `gather_artifact_presence`'s own (soft-degrading) `tasks_dir`
fact, so for an ambiguous-slug coord-topology mission at implement/review, this
mission's hard block fires first and `gather_artifact_presence` is never
reached with the ambiguous input on that path. But the two PRs have made
opposite raise-vs-degrade decisions for the identical exception on the
identical underlying read, authored independently, with neither branch's
tests aware of the other's contract. A future "harmonize the two anchoring
mechanisms" cleanup could silently adopt #3923's softer contract and revert
this mission's own FR-010 behavior, or could plumb `gather_artifact_presence`'s
`tasks_dir` fact into `wp_advance_ready` and inherit its silent-degrade
semantics without anyone re-deciding raise-vs-degrade on purpose.

Action taken: flagged in the PR body under a known-interactions/follow-ups
heading; the operator will relay this to #3923's author separately so the two
PRs (whichever lands second) deliberately reconcile the policy rather than
leaving two contradictory precedents live in the same guard-evaluation
neighborhood. No code change proposed in either mission for this entry.

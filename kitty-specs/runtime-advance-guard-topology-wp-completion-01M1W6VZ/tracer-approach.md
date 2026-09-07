# Tracer: Approach

Mission: runtime-advance-guard-topology-wp-completion-01M1W6VZ (issues #3883, #3884)

## Why these two issues are one mission

Both are runtime-advance-guard defects reported together (#3883/#3884), but they do
NOT share an implementation seam — spec.md's User Story 2 is explicit about this,
and this plan preserves that framing rather than papering over it. #3883 lands in
`gather_artifact_presence` (`src/runtime/next/runtime_bridge_io.py:998`), feeding
`present_artifacts`/`status_facts`; #3884 lands in `_wp_blocks_step`
(`src/runtime/next/runtime_bridge.py:781-810`), feeding a decision over
`wp_advance_ready`. What they share is the `evaluate_guards_strict` dispatch and the
single `ArtifactPresenceSnapshot` factory both guard functions read — not a fix, a
common upstream producer. Scoped into one mission for programme/co-review reasons
only.

## Sequencing (per plan.md, verified against the code first-hand)

- **WP1** — red-first fixture + reproductions for both defects, plus the two
  empirical unknowns flagged during planning (mission_slug/feature_dir.name
  invariant for a real coord worktree; the concrete exception
  `placement_seam(...).read_dir(PRIMARY_METADATA)` raises for a corrupt meta.json).
- **WP2** — `_wp_blocks_step` fix (#3884, FR-004/005): small, isolated, landed
  first for an early green signal.
- **WP3** — `gather_artifact_presence` fix + new `PrimaryPlacementResolutionError`
  + the 8-row call-site `mission_slug` threading table (#3883, FR-001/002/003/006/008).
- **WP4** — C-002's byte-exact regression sweep + NFR-001 baseline re-verification
  + tracer-file close-out.

## Design choice worth restating here

`gather_artifact_presence` gets exactly one new optional parameter (`mission_slug`),
gated by the existing `repo_root is not None` signal (not a second toggle) — this
mirrors the #3704/WP02 precedent that already added `repo_root` to this same call
chain. See plan.md's "Seam 1" section for the full trace; not re-derived here.

## 2026-09-07 — Scope narrowing (operator ruling)

The operator ruled this mission down from two issues (#3883+#3884) to #3884 only.
Draft PR #3923 (`codex/upgrade-preview-mission-health`) already fixes #3883
independently, in `src/runtime/next/runtime_bridge_io.py` — verified via the
paginated GitHub API (125 files, touches `runtime_bridge_io.py`, mentions
`gather_artifact_presence` 9 times in its diff) and confirmed to NOT touch
`src/runtime/next/runtime_bridge.py` or mention `_wp_blocks_step`/
`_should_advance_wp_step`/`UninitializedState`. A handover comment recording this
has already been posted on #3883.

The former "WP1"/"WP2"/"WP3" sequencing above (four WPs, two-issue premise) is
superseded by the mission's actual 3-WP shape: **WP02 -> WP01 -> WP03**, all of it
now scoped to #3884 alone (`_wp_blocks_step`'s `Lane.UNINITIALIZED` disjunct, plus
`_should_advance_wp_step`'s coord-topology reachability anchoring extension, which
survives from the pre-narrowing draft's "Seam 2 extension"/PLAN-FIT-001, now
promoted to explicit spec.md requirements FR-009/FR-010). See `spec.md`'s "Scope
Narrowing" section and `plan.md`'s "Narrowing" section for the full evidence and
technical re-derivation (in particular: no shared `resolve_primary_anchor_dir`
helper survives — the anchoring is now written inline in `_should_advance_wp_step`
itself, and FR-010 targets the already-existing `MissionSelectorAmbiguous`
exception, not a new one, per this narrowing's own empirical verification).

**PR description operator note — copy into the PR body at review time**: before
this fix, `_should_advance_wp_step` was never called with `repo_root` on a
coord-topology mission, so its `tasks/` lookup (against the coordination
worktree, which never receives `tasks/WP*.md`) always failed and the function
returned `True` unconditionally on `implement` — skipping the per-WP loop
entirely, regardless of whether any WP was in-progress, blocked, or rejected,
not only never-claimed. Shipping this fix will newly (and correctly) re-enable
the per-WP completion check for EVERY coord-topology mission currently in
`implement`: a mission whose WP was never claimed (#3884) will now block, but so
will one whose WP is merely `in_progress` and not yet handed off, `blocked`, or
rejected without operator provenance — any WP not in an acceptable/handed-off
state, not only a never-claimed one. Recommend that whoever merges this
spot-checks EVERY currently-in-`implement` coord-topology mission (not only
ones already suspected to have a never-claimed WP) immediately after merge. No
mission-tracking code change is proposed for this — it is a call-out about a
real operational discontinuity, not an internal test-suite delta.

**PR body scope line**: `Closes #3884` only — **not** `Closes #3883`. #3883 is out
of scope for this mission (draft PR #3923 fixes it independently); do not let the
mission's original two-issue framing (still visible in `reviews/*.yaml`'s review
history) make it into the PR body as `Closes #3883, #3884`.

## WP03 closing note (2026-09-07) — actual sequencing and the lane-consolidation gap

This mission's actual as-run sequencing was **WP02 -> WP01 -> WP03**, all three
scoped to #3884 alone post-narrowing — not the pre-narrowing four-WP, two-issue
shape this file's own seed content (above) describes (WP1/WP2/WP3/WP4 against
#3883+#3884). See `wps.yaml` and this mission's tasks-phase decision (recorded in
`tracer-design-decisions.md`'s "mandatory 3-WP repartitioning" entry) for the full
rationale — not re-derived here.

**Operationally important, and not yet resolved as of this WP's own run:** WP01
and WP02 are reviewed and `approved` in `status.json`, but their lane branches
(`kitty/mission-runtime-advance-guard-topology-wp-completion-01M1W6VZ-lane-a`, tip
`de115ebc0`; `...-lane-b`, tip `5724a0db5`) have **not yet been merged** into the
mission/target branch `fix/runtime-advance-guard-3883`. Verified: `git merge-base
--is-ancestor <tip> HEAD` is false for both; the entire production fix, all three
new test files, and the blast-radius test edits exist only on the lanes.
`lanes.json` records `depends_on_lanes: [lane-b]` for lane-a and
`depends_on_lanes: [lane-a]` for WP03's own `lane-planning` — i.e. the canonical
order is lane-b -> lane-a -> WP03's gate re-verification, and this mission ran
WP03's baseline pass ahead of that consolidation landing. **Lane consolidation
(lane-b then lane-a, per the dependency order) must happen before the PR is
opened** — the PR is meant to carry the fix, and today the mission branch does
not yet contain it. See `tracer-design-decisions.md`'s WP03 closing summary for
the full gate-count reconciliation across both trees.

**PR description operator note — addendum (2026-09-07, WP03).** In addition to
the rollout-impact note already recorded above (newly, correctly blocking a
never-claimed WP, including on COORD topology): whoever merges the lanes and
opens the PR should cite the **lane-a** gate numbers (618 / 672+1 / 765+1 /
1686+1/325 / ruff+mypy clean) in the PR's *Tests run* section, not the mission
branch's pre-consolidation numbers (745+1 / 1666+1/325 / ruff clean) — the
mission branch's numbers describe the unfixed tree and are not evidence the fix
works, even though they are individually correct for the tree they were measured
on. Name the branch each count was taken on explicitly; do not present one
without the other's context.

The `Closes #3884`-only scope line recorded above still stands unchanged.

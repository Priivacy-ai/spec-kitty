---
work_package_id: WP02
title: 'Verify #2646 closes via WP01 alone; contingent fix'
dependencies: []
requirement_refs:
- FR-003
planning_base_branch: research/3044-review-artifact-topology-seam
merge_target_branch: research/3044-review-artifact-topology-seam
branch_strategy: Planning artifacts for this mission were generated on research/3044-review-artifact-topology-seam. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/3044-review-artifact-topology-seam unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
agent: claude
history:
- at: '2026-08-02T16:42:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: src/specify_cli/agent_utils/
create_intent:
- tests/regression/test_2646_stale_verdict_closes_via_fr001.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/agent_utils/status.py
- tests/regression/test_2646_stale_verdict_closes_via_fr001.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 - Verify #2646 closes via WP01 alone; contingent fix

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load debugger-debbie
```

## Objective

**This is a verify-first work package, not a designed build.** GitHub issue #2646 reports that an
approved WP can continue to display a stale `rejected` warning in `agent tasks status` for
`lanes_with_coord` missions. This mission's spec/plan originally committed to fixing that by routing
`agent_utils/status.py`'s stale-verdict scan through `resolve_snapshot_review`/
`latest_review_artifact_verdict` — a post-plan adversarial squad found that design **type-shape
broken** (`ReviewOverride` carries no `verdict` field) and found **live evidence**, via direct
reproduction, that #2646 today reproduces only because WP01's writer doesn't exist yet — not because
of a live coord/primary read-authority split, which appears to already be closed by an earlier,
separately-merged mission (the placement-seam unification).

Your job is to **prove this empirically**, not take it on faith either way:

1. Confirm WP01 has landed (its writer must exist for this verification to mean anything).
2. Drive a `lanes_with_coord` mission fixture through reject→approve using WP01's real, shipped writer.
3. Assert `agent tasks status --json` reports correctly — **with zero changes to
   `src/specify_cli/agent_utils/status.py`**.
4. **If that assertion passes**: you are done. Commit the regression test as permanent proof #2646 is
   closed. Do not add any code to `agent_utils/status.py` — there is nothing to fix.
5. **If that assertion fails**: the stale warning still fires. Only then do you trace the actual
   residual mechanism (which may not be what any prior research in this mission describes) and
   implement the smallest fix that closes it, with its own regression test.

**Do not implement a fix speculatively "just in case."** A post-plan squad specifically flagged this
as a fakeable-DoD risk: building the (broken) originally-planned fix and declaring done without ever
running the verification this WP exists to perform. The whole point of this WP is that verification
comes first and gates whether any fix exists at all.

## Context & Constraints

Read these in full before starting:

- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/spec.md` — User Story 3 (rewritten post-plan;
  read the current version, not any cached memory of an earlier draft), FR-003
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/plan.md` — IC-02 (redesigned from the original
  IC-03; explains why the `resolve_snapshot_review` approach was retracted)
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/research.md` — R3's correction section (the
  full type-shape and live-reproduction findings)
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/data-model.md` — "Stale-verdict scan resolution"
  section, marked `[POST-PLAN CORRECTION]`
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/contracts/review-cycle-writer.md` — the
  `_get_wp_review_verdict` section, explicitly retracted
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/quickstart.md` — FR-003 section, verify-first
  commands

**Constraints (binding)**:
- Do **not** implement the `resolve_snapshot_review`-based design described in any earlier draft of
  this mission's research/data-model/contracts docs — it is retracted and does not work
  (`ReviewOverride` has no `verdict` field).
- Do **not** modify `src/specify_cli/agent_utils/status.py` unless the verification in T009 actually
  fails. `owned_files` reserves this path for the contingent case — reserving it is not permission to
  use it unconditionally.
- This WP has no declared `dependencies` (zero file overlap with WP01), but its verification is only
  meaningful once WP01's writer exists — if WP01 has not yet landed, coordinate with the operator
  before proceeding rather than fabricating a stand-in writer.

## Subtasks & Detailed Guidance

### Subtask T008 – Drive a `lanes_with_coord` fixture through reject→approve

- **Purpose**: Reproduce #2646's exact reported scenario against current code, using the real shipped writer, not a hand-simulated one.
- **Steps**:
  1. Reuse the existing `tests/integration/coord_topology_fixture.py` fixture (a fixture of this shape was used during this mission's post-plan live reproduction — this is the only coord-topology fixture in the tree, so it is the right one, though the exact prior usage isn't separately archived; do not build a new fixture from scratch).
  2. **Prefer calling `create_rejected_review_cycle` (WP01's generalized writer) directly** — once with `verdict="rejected"`, then again with `verdict="approved"` — over driving the full `spec-kitty agent tasks move-task` CLI path. A post-tasks squad found the CLI path requires the WP to already be sitting in `in_review`, which means fabricating a full `planned→claimed→in_progress→for_review→in_review` lane-transition history first — real, avoidable setup cost the direct-call path skips entirely, and it's what this mission's own earlier live reproduction (research.md R1/R3) actually used.
  3. Confirm the resulting `review-cycle-2.md` exists, has `verdict: approved`, and is committed (per WP01's own acceptance criteria) before proceeding to T009.
- **Files**: none changed yet — this subtask is a driving/setup step for T009's assertion.
- **Parallel?**: No — sequential with T009.
- **Notes**: **Do not edit `coord_topology_fixture.py`.** A post-tasks squad found it is shared infrastructure consumed by ~26 unrelated test files across `tests/integration/`, `tests/coordination/`, `tests/specify_cli/`, and `tests/acceptance/` — none of which this WP's own regression command (`pytest tests/agent/ tests/regression/ -q`) would catch if broken. Compose only its existing entry points. If that turns out to be genuinely insufficient to drive this scenario, stop and raise it with the operator rather than extending shared, unowned test infrastructure inside this WP.

### Subtask T009 – Assert `agent tasks status` reports correctly; commit the regression test

- **Purpose**: This is the actual verification — the load-bearing check this entire WP exists to run.
- **Steps**:
  1. Run `agent tasks status --json` (or call `_get_wp_review_verdict`/the stale-verdict scan function directly in a test context) against the fixture from T008.
  2. Assert the WP reports as approved with **no stale-verdict warning**.
  3. Write this as a permanent, checked-in test at `tests/regression/test_2646_stale_verdict_closes_via_fr001.py`, mirroring the shape of `tests/regression/test_2684_review_override_recognition.py` (a named regression test tied to the issue number, not an ad-hoc script).
  4. **Add an Activity Log entry recording T009's literal result before doing anything else** — `T009 result: PASS — zero status.py diff` or `T009 result: FAIL — <verbatim observed stale-verdict output>`. This is not optional bookkeeping: it is the reviewer's only auditable proof of which branch of this WP actually happened (see Review Guidance's `git log` gate).
  5. **If the assertion passes**: commit this test. `src/specify_cli/agent_utils/status.py` gets zero changes. This WP's FR-003 scope is satisfied — go to Review Guidance below and mark this WP done.
  6. **If the assertion fails**: do not paper over it. Record the actual observed failure (what `agent tasks status` reports, and why) in the test itself (as a comment or a clearly-failing assertion with a descriptive message) and proceed to T010.
- **Files**: `tests/regression/test_2646_stale_verdict_closes_via_fr001.py` (new)
- **Parallel?**: No — depends on T008.
- **Notes**: Also confirm the flat/single-branch regression (spec.md User Story 3, Acceptance Scenario 3) — run the same fixture flow against a non-coord mission and confirm behavior is unchanged from the pre-mission baseline, so this WP doesn't accidentally alter flat-topology behavior while investigating the coord case.

### Subtask T010 – Contingent: trace and fix, only if T009's verification fails

- **Purpose**: If — and only if — the expected-favorable outcome doesn't hold, this mission still needs #2646 closed for real.
- **Steps** (only perform these if T009's assertion actually failed):
  1. Trace the actual residual mechanism directly from the failing test's evidence — what does `_get_wp_review_verdict` (`agent_utils/status.py:40-62`) actually read, and why does it disagree with reality in this specific reproduction? Do not assume it's the same mechanism any prior document in this mission described — those were all found stale or wrong at some point in this mission's history; treat this as a fresh investigation grounded in the T009 failure itself.
  2. Design the smallest, most targeted fix that closes the observed gap — this may or may not resemble the originally-retracted `resolve_snapshot_review` design; do not default back to it without re-verifying it actually addresses what T009 found.
  3. Implement the fix, and extend `test_2646_stale_verdict_closes_via_fr001.py` (or add a sibling test) so it goes from red (documenting the T009 failure) to green.
  4. Update `kitty-specs/review-verdict-write-integrity-01KZ1CGF/contracts/review-cycle-writer.md`'s `_get_wp_review_verdict` section to describe the actual fix implemented, replacing its current "retracted, verify-first" framing.
- **Files**: `src/specify_cli/agent_utils/status.py` (only if this subtask activates)
- **Parallel?**: No.
- **Notes**: This subtask is expected to be a no-op in the favored-by-evidence outcome. Do not implement it preemptively — the whole design of this WP is that T009's result determines whether T010 does anything at all.

## Test Strategy

- `pytest tests/regression/test_2646_stale_verdict_closes_via_fr001.py -v`
- If T010 activates: `mypy --strict src/specify_cli/agent_utils/status.py`
- Full scoped regression before marking done: `pytest tests/agent/ tests/regression/ -q` (NFR-001)

## Risks & Mitigations

- **The single biggest risk for this WP is building T010 anyway, regardless of T009's outcome** — the exact fakeable-DoD shape a post-plan squad flagged. Mitigate by making T009's pass/fail result the explicit, recorded gate for whether T010 runs at all, and having the reviewer independently check this (see Review Guidance).
- **Fixture staleness**: `coord_topology_fixture.py` may need to reflect WP01's new writer behavior correctly (e.g., the commit step) to produce a valid reproduction. Confirm the fixture actually exercises WP01's shipped code, not a stubbed/mocked writer.

## Review Guidance

- **The reviewer's primary job is confirming T009 actually ran and its real result — pass or fail — determined whether T010 has any content.** A WP that "just happens" to include both a passing verification test AND a status.py fix, without a clear record of the verification having failed first, should be rejected and sent back.
- **Concrete, checkable gate (not a trust-the-narrative check)**: before approving, run
  `git log --oneline -- tests/regression/test_2646_stale_verdict_closes_via_fr001.py src/specify_cli/agent_utils/status.py`.
  - If `agent_utils/status.py` has **any** diff in this WP's commits, reject unless the WP's Activity Log
    contains an antecedent entry recording T009's literal FAIL result (the actual observed stale-verdict
    output), timestamped before the `status.py` change. If `status.py` has a diff with no such antecedent
    FAIL entry, or with a PASS entry instead, reject — that is exactly the fakeable-DoD shape this WP was
    designed to prevent.
  - If `status.py` has a diff, additionally `git stash` it locally and re-run
    `test_2646_stale_verdict_closes_via_fr001.py` to confirm it goes red without the fix (proving T010's
    fix is load-bearing, not decorative), then restore the stash.
- If T009 passed (the expected, evidence-favored outcome): confirm `src/specify_cli/agent_utils/status.py` has zero diff in this WP.
- If T010 activated: confirm the fix is scoped to the actually-observed failure, not a resurrection of the retracted `resolve_snapshot_review` design without re-justification.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-02T16:42:46Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP02 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

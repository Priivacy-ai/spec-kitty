---
work_package_id: WP03
title: Base-red triage
dependencies:
- WP02
requirement_refs:
- FR-002
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
- T017
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: python-pedro
authoritative_surface: tests/missions/test_mission_v1_compat_unit.py
create_intent:
- kitty-specs/ci-pipeline-reinstatement-01M1X35E/triage-3284.md
execution_mode: code_change
owned_files:
- tests/missions/test_mission_v1_compat_unit.py
- tests/missions/test_mission_v1_events_unit.py
- tests/missions/test_mission_v1_guards_unit.py
- tests/missions/test_mission_v1_runner_unit.py
- tests/missions/test_mission_v1_schema_unit.py
- tests/missions/test_e2e_mission_v1_integration.py
- tests/missions/test_mission_guards_integration.py
- tests/missions/test_mission_loading_integration.py
- tests/missions/test_mission_software_dev_integration.py
role: implementer
tags: []
tracker_refs:
- '#3284'
---

## ⚡ Do This First: Load Agent Profile

Load your assigned agent profile via `/ad-hoc-profile-load <profile>` (role:
implementer) before anything else. Then read `plan.md` (FOUNDATION F2 base-red
triage), `spec.md` FR-002 + SC-008, `contracts/p1-census-oracle.md` (the census
authorizes each drop), and the charter §"Red-Main Discipline (SO#9)" +
"Pre-existing Failure Reporting Rule".

## Objective

A full run on the mission base shows **23 untracked failures + 2 errors (#3284)**. A
green gate frozen on that base would be a lie (SC-008). This WP triages every base
red so the base is **green before any shard topology is frozen** (WP08). Each red is
resolved as **exactly one of two dispositions** — never a third "tracked-and-left-red":

1. **Drop** — a behavioral test over census-`dead` code, authorized ONLY by the WP02
   census with **independent evidence** (retirement-gate ref / ADR /
   zero-importer-AND-not-dynamically-reached). Self-certification is invalid.
2. **Fix** — a live regression, fixed at the **stable entry point** (DIR-034).

**This WP consumes the WP02 census** (`dependencies: [WP02]`) — every drop must be
census-authorized, and the census's independent-evidence guard is what makes this
non-fakeable. The enumerated owned `tests/missions/test_mission_v1_*` files are the
**candidate dead-import drops** identified in grounding; the implementer confirms each
against the census by reproducing #3284.

**Non-fakeable DoD (binding):** each drop carries INDEPENDENT per-red evidence
recorded in the triage record — a retirement-gate reference, an ADR, or a proof of
zero-importer-AND-not-dynamically-reached. Never self-certification, never a bare
"dead-code" label.

## Subtask guidance

### T013 — Red-first: reproduce #3284 into the triage record (SEPARATE first commit)

The stable entry point here is the canonical suite run. As your **first commit**,
create `kitty-specs/ci-pipeline-reinstatement-01M1X35E/triage-3284.md` and reproduce
#3284 on the mission base: run the suite as #3284 describes, capture the **exact 23
failures + 2 errors** (node ids + the failing assertion/error each), and record the
run command + counts. This *is* the red-first evidence: the observable precondition
(base is red) is captured before any fix/drop. Do not fix anything yet.

### T014 — Per-red independent-evidence triage

For each of the 25 reds, record in the triage record: node id → disposition
(`drop`|`fix`) → **independent evidence**. For a `drop`, name the **retired src surface
the test imports/exercises** and cite the WP02 census entry + its evidence
(gate-ref/ADR/that-src-surface-is-zero-importer-AND-not-dynamically-reached) — never the
test file's own importer count. For a `fix`, name the live regression and
the stable entry point through which it manifests. Cross-check every `drop` against
`_p1_census_oracle.py` — an unevidenced drop must be refused by the census guard.

### T015 — Drop the census-authorized dead-import files

Delete the enumerated `tests/missions/test_mission_v1_*` files (and any others the
census authorizes) that are dead-import behavioral tests over retired mission_v1
surfaces. Each deletion references its census evidence in the triage record. If the
census does NOT authorize a candidate (it is actually live), do not drop it — fix it
instead (T016) and note the reclassification.

### T016 — Fix live regressions at the stable entry point

For every red the census marks `live` (not droppable), fix the regression through the
pre-existing stable entry point (DIR-034) — the failure must be the bug's observable
symptom, not a missing-new-symbol collection error. If reproduction shows **all 23
are census-dead drops**, record that explicitly with per-file evidence (an empty
fix-set is a valid outcome only if every red is independently evidenced as dead).

> **Ownership note (partition):** the enumerated owned files are the expected drops.
> If a live-regression fix must touch a `src/**` file or a test **not** in
> `owned_files`, STOP and coordinate with the orchestrator to extend ownership or
> spin a follow-up — do not silently edit outside the partition (DIR-024). Record the
> coordination in the triage record.

### T017 — Verify base green + no leave-red

Re-run the canonical suite; confirm **0 untracked failures** (SC-008). Record the
final run command + counts in the triage record. Assert there is **no third
disposition**: every #3284 red is either dropped (evidenced) or fixed — none is
tracked-and-left-red. This green base is the precondition for the TOPOLOGY shard
freeze (WP08).

## Branch Strategy

- Base/target: `feat/ci-pipeline-reinstatement`; worktree via `spec-kitty implement WP03`.
- Depends on WP02 (census) — claim only after WP02 is approved/done.
- Commit order: **T013 reproduce-red FIRST**, then triage/drops/fixes, then T017 green proof.

## Definition of Done

- The triage record captures #3284 red-on-base (23+2, node ids + failing assertions)
  and the final **0-untracked-failures** green run, with exact commands + counts.
- Every drop is bound to the **retired src surface the failing test imports/exercises**
  (that surface is census-`dead`), with **independent, individually-reviewable
  evidence** (gate-ref / ADR / that src surface is
  zero-importer-AND-not-dynamically-reached) — never self-certification, and **never**
  the test file's own (always-zero) importer count.
- No base red is left tracked-and-red (no third disposition).
- **Targeted test surface**: the canonical base suite per #3284 (record the exact
  command), plus `pytest tests/missions/ -q` to confirm the retained mission tests
  still pass after the drops.

## Risks

- **P1 loophole (top squad-flagged risk)**: dropping a live regression as "dead". The
  WP02 independent-evidence guard is the machine defense — every drop must survive it.
  The anti-laziness pass targets exactly this DoD.
- **#3284 reproduction variance**: baseline-red gotcha (CLAUDE.md) — classify each red
  as truly base (red on merge-base) vs CI-env/stale-venv/stale-install. Re-run
  `uv sync --frozen --all-extras` before recording a failure as pre-existing.
- **Ticket assignment (DIR-012)**: assign #3284 to the HiC before/as you begin.
- **Marker/baseline gates**: dropping test files can shift marker baselines or node-id
  baselines — if a shape guard reds on the deletions, coordinate with WP16 (it owns
  the demotion); do not fake a baseline swap here.

## Reviewer guidance

- Independently verify each drop's evidence against the census — do NOT accept a bare
  "dead-code" label. Spot-check at least 3 drops by confirming zero importers /
  retirement-gate coverage yourself.
- Confirm the reproduce-red (T013) predates the drops in commit order.
- Confirm the final green run is real (command + counts in the record) and that no red
  was silenced by skip/xfail rather than dropped-or-fixed.

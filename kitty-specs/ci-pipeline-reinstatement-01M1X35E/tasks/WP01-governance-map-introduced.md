---
work_package_id: WP01
title: Governance-map `introduced` disposition + dead-`ci.yml` retirement
dependencies: []
requirement_refs:
- C-001
- C-010
- FR-012
- FR-017
planning_base_branch: feat/ci-pipeline-reinstatement
merge_target_branch: feat/ci-pipeline-reinstatement
branch_strategy: Planning artifacts for this mission were generated on feat/ci-pipeline-reinstatement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-pipeline-reinstatement unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-ci-pipeline-reinstatement-01M1X35E
base_commit: f4ffd7007c9454f085b1b1eaafc26fec5ace612b
created_at: '2026-09-07T10:01:54.949801+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-09-07T00:00:00Z'
  actor: planner-priti
  action: created
agent_profile: implementer-ivan
authoritative_surface: docs/convergence/interim-ci-producer.md
create_intent: []
execution_mode: code_change
owned_files:
- docs/convergence/interim-ci-producer.md
- tests/release/test_release_ci_ownership.py
- .github/workflows/ci.yml
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before anything else, load your assigned agent profile via
`/ad-hoc-profile-load <profile>` (the orchestrator assigns `agent_profile`;
`role: implementer`). Then read, in order:

1. `plan.md` — the FOUNDATION cluster and the "Constitution Check (Charter)" table.
2. `contracts/governance-map-schema.md` — **authoritative** over this prompt where they conflict.
3. The charter `.kittify/charter/charter.md` §"ATDD-First Discipline (C-011)" and
   the "Quality & Tech-Debt Standing Orders" (SO#1 lockstep, SO#5 non-vacuous gates).

## Objective

The mission de-defers and introduces many workflows; the enforcer
`tests/release/test_release_ci_ownership.py` asserts an **exact closed set** per
disposition (`restore | defer | never-restore`) over the pre-fork paths named in
`docs/convergence/interim-ci-producer.md`. Net-new workflows (Sonar, `ci-router`,
`module-tests`, `ci-modules`, `ci-aggregate`, `ci-nightly`, `packs`) have **no
pre-fork ancestor** and are therefore un-modellable today — appending a row is not
representable in a closed-set assertion. This WP **extends the schema + enforcer
with an `introduced` disposition** (FR-012 / C-001) so net-new workflows are
first-class, and **retires the dead EXPERIMENTAL-fenced `.github/workflows/ci.yml`**
(FR-017 / C-010) in lockstep with its enforcing seam
`test_private_factory_ci_is_scoped_to_experimental_repo` (which today hard-asserts
the fence). This is the FOUNDATION WP that unblocks **every** net-new-workflow WP —
land it first.

**Scope guard (DIR-024 locality):** touch only the three owned files. Do NOT add
the actual net-new workflow files here — those belong to their own WPs. This WP
makes the *schema* able to represent them and registers the `ci.yml` retirement.

## Subtask guidance

### T001 — Red-first: pin `introduced` + `ci.yml` neutralized (SEPARATE first commit)

This is the ATDD anchor (C-011). Author, as your **first commit**, a failing test
in `tests/release/test_release_ci_ownership.py` that:

- Asserts a fourth disposition set `introduced` exists in the map + enforcer and
  that it contains at least the net-new workflow names the mission will add
  (assert the *contract*, e.g. `"sonar.yml" in introduced_set`), and
- Asserts the archived `ci.yml` is neutralized/retired (e.g. the fenced suite job
  that references `spec-kitty/EXPERIMENTAL-spec-kitty` is gone, or `ci.yml` is
  registered as `never-restore`/removed per the schema decision).

Run it against the mission base and **confirm it fails for the right reason** (the
`introduced` vocabulary does not yet exist / `ci.yml` still carries the dead fence)
— not a collection/import error. Capture the red output for the reviewer. Any
new-symbol import must be lazy/in-test so the test still *collects* on base.

### T002 — Tidy-first: campsite the ownership-test module (SO#2, behavior-preserving)

`test_release_ci_ownership.py` is a god-ish enforcement surface (multiple
disposition sets, runner/token invariants, fence assertions). Before adding the
fourth set, do a **distinct, behavior-preserving** tidy commit: extract the
per-disposition set literals + the shared "load map rows" helper into named
module-level locals/fixtures so the fourth set slots in without duplication.
Separate this from the functional change (DIR-024: opportunistic cleanup is its own
commit). Do not change any assertion outcome in this step.

### T003 — Add the `introduced` disposition to the map

In `docs/convergence/interim-ci-producer.md`, add the `introduced` disposition to
the documented vocabulary (per `contracts/governance-map-schema.md`) and add rows
for the mission's net-new workflows with a one-line rationale each. **Also reconcile
the now-stale "private EXPERIMENTAL vs public promotion" split**: since the
EXPERIMENTAL repo is archived and its Blacksmith producer is inert (C-010), the map
must state the reinstated CI is the primary/sole producer, not a shift-left layer
beneath Blacksmith. Keep the existing `restore`/`defer`/`never-restore` rows intact.

### T004 — Neutralize/retire the dead `.github/workflows/ci.yml`

`ci.yml` is fenced to `github.repository == 'spec-kitty/EXPERIMENTAL-spec-kitty'`
and the repo is archived → it runs nowhere. Neutralize/retire it per the schema
decision recorded in T003 (remove the dead fenced suite job / retire the file).
Do NOT silently delete without registering the disposition — the map + enforcer
must agree (C-001 lockstep). No `blacksmith` runner and no `SK_CI_TOKEN` may remain
referenced by any surviving public job.

### T005 — Enforcer: `introduced` exact-set + invariants + every-workflow-PR + self-mutation

**Enforcer subject (binding):** the enforcer asserts on the **map-ROW disposition**
(each pre-fork/net-new path's row in `docs/convergence/interim-ci-producer.md`), **not**
on filesystem presence of the workflow file. A row is the unit of assertion; do not
substitute "the `.yml` exists on disk" for "the row is registered with the right
disposition". **Frozen 7-net-new-name contract:** the `introduced` set is exactly the
mission's seven net-new workflow names (Sonar, `ci-router`, `module-tests`,
`ci-modules`, `ci-aggregate`, `ci-nightly`, `packs`). This count is frozen for the
mission — an **8th** net-new workflow is not representable in the exact set and
**reopens WP01** (acceptable, documented) rather than being appended silently downstream.

Grow `test_release_ci_ownership.py` so it (all now GREEN):

- Asserts the `introduced` set as an **exact set** (per the schema contract §Invariants);
- Preserves the existing three-set assertions unchanged (do not weaken them);
- Asserts `introduced` + `restore` workflows use **stock runners** (`"blacksmith"
  not in text`) and carry **no `SK_CI_TOKEN`** on public jobs;
- Asserts the enforcer runs on **every workflow-changing PR** (not only a tag push)
  — this is a real trigger/scope assertion, part of the mission's governance spine;
- Carries a **self-mutation negative** (SO#5 non-vacuity): deleting any row from any
  disposition set reds the test — the enforcer is not vacuous.

### T006 — Reconcile the private-factory fence with `ci.yml` retirement

`test_private_factory_ci_is_scoped_to_experimental_repo` (in the same file) hard-
asserts the EXPERIMENTAL fence on `ci.yml`. Retiring `ci.yml` must NOT leave that
assertion orphaned-red. Update it in lockstep so it either (a) asserts the fence is
gone/neutralized, or (b) is retired with the file — whichever the schema decision in
T003 dictates. The end state: no orphaned red, and the invariant that no public job
carries the private fence is still enforced.

## Branch Strategy

- `planning_base_branch`: `feat/ci-pipeline-reinstatement`
- `merge_target_branch`: `feat/ci-pipeline-reinstatement`
- Worktree: `spec-kitty implement WP01` resolves the per-lane worktree from
  `lanes.json`; work there, never reconstruct the path by hand.
- Commit order: **T001 red-first commit FIRST**, then T002 tidy commit, then the
  functional commits (T003–T006). The reviewer verifies red-on-base → green-on-final.

## Definition of Done

- The T001 red-first test was **red on the mission base** (evidence captured) and is
  **green on final**.
- `docs/convergence/interim-ci-producer.md` documents `introduced` + rows for the
  net-new workflows + the reconciled primary-producer statement.
- `.github/workflows/ci.yml` is neutralized/retired with no `blacksmith`/`SK_CI_TOKEN`
  residue and its disposition is registered in the map.
- `test_release_ci_ownership.py` asserts four exact disposition sets **by map-ROW
  disposition (not filesystem presence)**, the stock-runner + no-private-token
  invariants, the every-workflow-PR scope, and a self-mutation negative; the
  private-factory fence test is reconciled (no orphaned red).
- The `introduced` set is frozen at exactly **seven** net-new workflow names (Sonar,
  `ci-router`, `module-tests`, `ci-modules`, `ci-aggregate`, `ci-nightly`, `packs`); an
  8th net-new workflow reopens WP01 (documented), never appended downstream.
- **Targeted test surface** (charter Testing Requirements — no full suite):
  `pytest tests/release/ -q` and `pytest tests/architectural/test_no_retired_subsystems.py -q`.

## Risks

- **Schema over-broadening**: `introduced` must remain an *exact* set — do not turn
  it into a catch-all that lets any unregistered workflow pass. The self-mutation
  negative (T005) guards this.
- **New-file arch gates**: no new src symbols here, but a new assertion may trip
  golden-count `len==N` bans — annotate `# golden-count: cardinality-is-contract`
  on the assertion line if so (see memory `golden-count arch ratchets`), or convert
  to a content check. Do not disable the gate.
- **regen-assets gate**: this WP does not edit a `packs/` SOURCE, so `spec-kitty
  regen` should not be required; if a doc-inventory gate reds on the new map doc,
  register per the docs-index flow rather than improvising.

## Reviewer guidance

- Verify T001 was genuinely red on base **for the right reason** (missing vocabulary /
  live fence), not a collection error — request the captured red output.
- Confirm the tidy commit (T002) is behavior-preserving and **separate** from the
  functional commits.
- Confirm the `introduced` set is asserted as an exact set and the three prior sets
  are unweakened; run the self-mutation negative by deleting a row locally.
- Confirm no orphaned red from the `ci.yml` retirement (T006) and no
  `blacksmith`/`SK_CI_TOKEN` residue.

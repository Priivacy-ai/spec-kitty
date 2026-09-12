# Work Packages: Review-Cycle Verdict Seam Rebuild

**Mission**: `review-cycle-verdict-seam-rebuild-01KZ2W7W`
**Branch**: `pr/review-verdict-write-integrity-01KZ1CGF` (planning base and merge target)
**Generated**: 2026-08-03

Derived from `plan.md`'s Implementation Concern Map. Concerns are not work packages — several split, one merged.

## Ownership and the slicing gate

`validate_no_overlap` hard-fails `finalize-tasks` when two **dependency-unordered** work packages claim overlapping `owned_files`. Sequential pairs are exempt, and **any two root WPs are always concurrent**. Two files are convergence points and drive most of the edges below:

| Convergence file | Claimed by | Serialized as |
|---|---|---|
| `src/specify_cli/review/cycle.py` | WP10, WP13, WP14 | WP10 → WP13 → WP14 |
| `src/specify_cli/review/artifacts.py` | WP09, WP13, WP14 | WP09 → WP13 → WP14 |
| `src/specify_cli/review/arbiter.py` | WP12, WP13, WP14 | WP12 → WP13 → WP14 |
| `.../agent/tasks_verdict_persistence.py` (new, WP06) | WP06, WP11, WP12 | WP06 → WP11 → WP12 |
| `post_merge/review_artifact_consistency.py` | WP07, WP13 | WP07 → WP13 |
| `tests/_arch_shard_map.py` | WP01, WP02 | WP01 → WP02 |
| `tests/architectural/test_verdict_seam_census.py` | WP01, WP08 | WP01 → WP08 |

Rules in force for every WP: **file-granularity `owned_files` only** (a directory-shaped entry swallows everything beneath it via a string prefix test), **no `scope: codebase-wide`** (it exempts a WP from the overlap check *and* two others), and **`create_intent` for every planned-new path**.

Two further constraints surfaced during `finalize-tasks --validate-only` and are recorded because they shaped the design:

- **`owned_files` may not contain any `kitty-specs/` path** — the gate rejects it outright, with no `planning_artifact` exemption. The per-concern census fragments therefore live at `tests/architectural/census/verdict_seam_ICNN.yaml` and fold into `tests/architectural/verdict_seam_census.yaml`, which WP01's check reads as its expected-set fixture. That is a better shape for FR-020 than a markdown doc in a spec directory: the fixture sits next to the check that consumes it.
- **Requirement ids must match `^(?:FR|NFR|C)-\d+$`.** The `FR-001a` / `FR-006a` shape is rejected by design (#2066), so those were renumbered to **FR-022** and **FR-023** across spec, plan, data-model and the WP prompts.

## Execution shape

```
L1  WP01 census        WP03 board-hygiene   WP06 seam-extraction        width 3
L2  WP02 date-rot      WP04 kind+plumbing   WP07 authority   WP09 numbering   width 4
L3  WP05 CI-shards   WP08 reconcile   WP10 atomicity   WP11 ordering   WP18 merge-driver   width 5
L4  WP12 arbiter                                                              width 1
L5  WP13 consumer-unification                                              width 1
L6  WP14 reader-polarity                                                   width 1
L7  WP15 durability-matrix   WP16 truthfulness+fold                        width 2
L8  WP17 mission-exit verification                                         width 1
```

18 work packages, 80 subtasks. **WP18 was authored mid-mission** by operator
adjudication to discharge WP04's T017 ownership deadlock — see its own section
below for the provenance. The original slicing was 17 WPs / 76 subtasks; every
count in this file that predates WP18 refers to that original shape. **Delivered shape, measured rather than drawn**: a 7-level DAG at mean width 2.43, and a **9-slot lane wall clock** — one lane binds to one worktree, and `finalize-tasks` collapses the overlap graph by union-find, so an 8-member connected component runs serially even where its members are pairwise disjoint.

The plan's recomputed target was 6 levels at width 2.83. The one level of growth traces to a single removable edge — WP11→WP12 over the new `tasks_verdict_persistence.py`. Recorded rather than fixed: removing it means splitting that module in two, which re-slices work packages rather than correcting a defect in them.

## Subtask Index

Reference table only — completion is event-sourced via `spec-kitty agent tasks mark-status`, never by editing a row here.

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Author the verdict-seam census check enumerating writers, resolvers and readers | WP01 | |
| T002 | Enforce: a `retire` row with no retiring FR is a census failure | WP01 | |
| T003 | Reconcile the denominator against `test_2093_authority_invariant.py`'s `_EVENT_SLOTS` | WP01 | |
| T004 | Scope the census by concept, excluding `pre_review_gate` and `verdict_aggregation` | WP01 | |
| T005 | Emit `contracts/census/IC-01.md` and register the shard-map row | WP01 | |
| T006 | Fix #3157's dated fixture without touching product code | WP02 | |
| T007 | Derive and record the mixture classifier rule; report the true denominator | WP02 | |
| T008 | Author the absolute-event-timestamp mixture check | WP02 | |
| T009 | Register the shard-map row for the new check | WP02 | |
| T010 | Re-pin the acceptance-verdict frozen flag contract with per-flag rationale | WP03 | [P] |
| T011 | Make the parity check assert resolved activation, not budget-dependent text | WP03 | [P] |
| T012 | Introduce `MissionArtifactKind.REVIEW_CYCLE` | WP04 | |
| T013 | Add it to `_PLACEMENT_ARTIFACT_KINDS`; add the `PARTITION_RATIONALE` row | WP04 | |
| T014 | Add the filename-anchored classifier leg for `review-cycle-*.md` | WP04 | |
| T015 | Make the commit router honour the kind for review-cycle paths | WP04 | |
| T016 | Rule on E2 eligibility for `REVIEW_CYCLE` | WP04 | |
| T017 | Resolve the two-sided `tasks/` reconciliation-class hazard | WP04 | |
| T018 | Document the create-window artifact split | WP04 | |
| T019 | Decouple `fast-tests-*` from `fast-tests-status.result` | WP05 | |
| T020 | Decouple `integration-tests-*` from their `fast-tests-*` counterpart | WP05 | |
| T021 | Add a topology assertion so a new result-gated edge reds | WP05 | |
| T022 | Extract the four verdict sites into `tasks_verdict_persistence.py` | WP06 | |
| T023 | Preserve the import-cycle invariant | WP06 | |
| T024 | Obtain and record the C-003 ruling for the module move | WP06 | |
| T025 | Add the reducer branch surfacing the event verdict | WP07 | |
| T026 | Name the slot distinctly from `review`; state the precedence rule | WP07 | |
| T027 | Make the reader snapshot-first with PRIMARY fallback | WP07 | |
| T028 | Define behaviour for `review_result: null` under `--force` | WP07 | |
| T029 | Re-point the merge gate and `_lane_gate` at the slot | WP07 | |
| T030 | Re-point `merge/preflight.py` and `merge/forecast.py` | WP07 | |
| T031 | Close the `orchestrator_api` ingress hole | WP07 | |
| T032 | Derive cycle numbers from `max(parsed) + 1` | WP09 | |
| T033 | Refuse on collision, including the unparseable-sibling case | WP09 | |
| T034 | Red-first reproduction of the gap-overwrite | WP09 | |
| T035 | Build the reconciliation detector over the census's retired resolvers | WP08 | |
| T036 | Add the `doctor` subcommand shim and its sibling module | WP08 | |
| T037 | Absorb `CoordinationBranchDeleted` for the 45 stranded missions | WP08 | |
| T038 | Regenerate `docs/api/cli-commands.md` | WP08 | |
| T039 | Report, never silently ignore, cross-branch coord records | WP08 | |
| T040 | Red-first reproduction of concurrent verdict loss | WP10 | |
| T041 | Serialize allocation and write under `feature_status_lock` | WP10 | |
| T042 | Retry the commit on index contention via the existing probe | WP10 | |
| T043 | Make the failure path leave no artifact, including validation failure | WP10 | |
| T044 | Red-first reproduction of the crash-orphan | WP10 | |
| T045 | Narrow the content-identity guard without disarming the #990 control | WP10 | |
| T046 | Ensure review fixtures run under a real initialized repo | WP10 | |
| T047 | Red-first reproduction of the orphan surviving a failed transition | WP11 | |
| T048 | Order the verdict write against the transition emit | WP11 | |
| T049 | Emit the `--json` durability key for `--no-auto-commit` | WP11 | |
| T050 | Thread `skip_target_branch_commit` to the writer | WP11 | |
| T051 | Retire the arbiter frontmatter block into `ReviewOverride` | WP12 | |
| T052 | Retire the JSON sidecars into `ReviewOverride` | WP12 | |
| T053 | Fix the bare-`wp_id` resolver and the lexicographic sort | WP12 | |
| T054 | Surface arbiter-persist failure, including under `--json` | WP12 | |
| T055 | Suppress the fabricated approval on the override path | WP12 | |
| T056 | Re-pin `test_tasks_cli_contract_coord.py`'s arbiter path | WP12 | |
| T057 | Unify slug derivation | WP13 | |
| T058 | Route all twelve read/write sites through one owner function | WP13 | |
| T059 | Narrow the merge-gate fan-out, after WP08 has reconciled | WP13 | |
| T060 | Discharge C-001's premise against the unified resolver | WP13 | |
| T061 | Correct the "PRIMARY-partition for every topology" docstring | WP13 | |
| T062 | Re-pin the #2834 coord-husk test with the both-present case | WP13 | |
| T063 | Declare a polarity for every reader in the census | WP14 | |
| T064 | Fix the fail-open kanban reader | WP14 | |
| T065 | Fix the uncaught arbiter crash | WP14 | |
| T066 | Record why the merge gate is already fail-closed | WP14 | |
| T067 | Exercise the durability matrix through the real command surface | WP15 | |
| T068 | Prove each cell reds when the commit call is deleted | WP15 | |
| T069 | Cover the real-router, real-git path | WP15 | |
| T070 | Audit test names against assertions over the bounded denominator | WP16 | |
| T071 | Fold the census fragments into the contract the check reads | WP16 | |
| T072 | Correct `workflow.py`'s inventory docstring and the doc surfaces | WP16 | |
| T073 | Add the CHANGELOG entry for the behaviour changes | WP16 | |
| T074 | Diff the affected-suites node-id set against the committed baseline | WP17 | |
| T075 | Restate NFR-005's countable clause against one named port method | WP10 | |
| T076 | Draft the closing-clause block and the epic-#3044 carve-out | WP16 | |
| T077 | Implement the review-cycle merge driver (never blend two verdicts) | WP18 | |
| T078 | Register the driver across gitattributes, command table, init and lane-merge | WP18 | |
| T079 | Upgrade migration registering the driver for existing clones | WP18 | |
| T080 | Prove the create-window clobber is closed, red-first | WP18 | |

---

## WP01 — Verdict-seam census and its architectural check

**Goal**: Produce the authoritative enumeration of verdict writers, location resolvers and frontmatter readers, so every downstream reduction target is derived rather than asserted.
**Priority**: P1 — three successive spec revisions pinned counts that were all wrong.
**Independent test**: Introduce a new writer, resolver or reader anywhere in `src/`; the check must red.
**Subtasks**: T001 T002 T003 T004 T005 · **Dependencies**: none · **Estimated prompt**: ~380 lines

## WP02 — Time-dependent test rot

**Goal**: Fix #3157's fixture and ban the mixture of hard-coded and `now()`-generated event timestamps in one log.
**Priority**: P1 — a prerequisite for measuring this mission, via WP05.
**Independent test**: The lifecycle test passes with **zero** product-code change; the new check flags a mixed fixture and does not flag an all-hard-coded one.
**Subtasks**: T006 T007 T008 T009 · **Dependencies**: WP01 (`tests/_arch_shard_map.py`) · **Estimated prompt**: ~320 lines

## WP03 — Board hygiene

**Goal**: Clear two pre-existing mainline reds unrelated to the seam.
**Priority**: P3 — the only genuinely droppable package.
**Independent test**: Both named checks pass on the mainline.
**Subtasks**: T010 T011 · **Dependencies**: none · **Estimated prompt**: ~220 lines

## WP04 — The `REVIEW_CYCLE` kind and its plumbing

**Goal**: Give review cycles their own artifact kind on the COORD partition, and make the **write** side follow it.
**Priority**: P1 — ADR 2026-08-03-1. Without the classifier leg every rejection write fails.
**Independent test**: A `kind=REVIEW_CYCLE` write under a coord topology lands on the coord surface and commits there; the same write under `SINGLE_BRANCH` lands PRIMARY.
**Subtasks**: T012 T013 T014 T015 T016 T017 T018 · **Dependencies**: WP01 · **Estimated prompt**: ~520 lines

## WP05 — CI shard independence

**Goal**: Stop one failing shard starving the diff-coverage gate.
**Priority**: P1 — `fast-tests-review` is the only shard covering this mission's own write surface.
**Independent test**: A mainline push with one shard failing still produces coverage for every shard currently gated on another's result.
**Subtasks**: T019 T020 T021 · **Dependencies**: WP02 · **Estimated prompt**: ~250 lines

## WP06 — Extract the verdict seam out of `tasks_move_task.py`

**Goal**: Move the four verdict-relevant sites out of a 2554-line module so four later packages stop queueing on one file.
**Priority**: P1 — a structural prerequisite, not a cleanup.
**Independent test**: Behaviour unchanged; the import-cycle invariant holds; the new module is singly owned.
**Subtasks**: T022 T023 T024 · **Dependencies**: none · **Estimated prompt**: ~300 lines

## WP07 — Verdict authority and its reader

**Goal**: Make the reduced snapshot authoritative for *which* verdict is current, and give it a reader.
**Priority**: P1 — the mission's core invariant.
**Independent test**: A consumer asked "is this WP approved?" reaches the event, and an un-migrated mission still gets an answer rather than "no verdict".
**Subtasks**: T025 T026 T027 T028 T029 T030 T031 · **Dependencies**: WP01 · **Estimated prompt**: ~540 lines

## WP08 — Reconcile records stranded under divergent paths

**Goal**: Find and reconcile verdict records the fan-out currently tolerates and WP13 will stop resolving.
**Priority**: P1 — **must land before WP13's narrowing**, or the merge gate opens a fail-open window.
**Independent test**: Seed a record at each retired resolver's output; the command detects and reports every one.
**Subtasks**: T035 T036 T037 T038 T039 · **Dependencies**: WP01, WP04 · **Estimated prompt**: ~420 lines

## WP09 — Verdict numbering

**Goal**: A new record never overwrites an existing one.
**Priority**: P1 — reproduced data loss.
**Independent test**: With cycles 1 and 3 present, recording a new verdict does not touch cycle 3.
**Subtasks**: T032 T033 T034 · **Dependencies**: WP01 · **Estimated prompt**: ~260 lines

## WP10 — Atomicity, crash-safety, concurrency, and the guard narrowing

**Goal**: One critical section over allocation and write; no orphan on any failure path; repeat feedback recordable without disarming the #990 control.
**Priority**: P1 — three reproduced failure modes.
**Independent test**: Kill the process between write and commit; the identical retry succeeds and records the correct verdict with no manual cleanup.
**Subtasks**: T040 T041 T042 T043 T044 T045 T046 T075 · **Dependencies**: WP06, WP07 · **Estimated prompt**: ~560 lines

## WP11 — Transition ordering and the durability signal

**Goal**: No readable verdict survives a failed transition; the one sanctioned non-durable path announces itself.
**Priority**: P1.
**Independent test**: Force the transition emit to fail; no approved verdict is readable by any consumer.
**Subtasks**: T047 T048 T049 T050 · **Dependencies**: WP06, WP07 · **Estimated prompt**: ~330 lines

## WP12 — Arbiter override retirement

**Goal**: Retire the arbiter's two non-authoritative override representations into the event-sourced `ReviewOverride`.
**Priority**: P1.
**Independent test**: An override survives a fresh clone, clears the merge gate, and produces no approval record.
**Subtasks**: T051 T052 T053 T054 T055 T056 · **Dependencies**: WP06, WP07, WP11 (both claim `tasks_verdict_persistence.py`) · **Estimated prompt**: ~470 lines

## WP13 — Consumer unification

**Goal**: Every read, write, gate and display path resolves one identical location, through one owner function.
**Priority**: P1 — owns C-001's discharge.
**Independent test**: For each accepted filename separator, every path resolves the same directory.
**Subtasks**: T057 T058 T059 T060 T061 T062 · **Dependencies**: WP04, WP07, WP08, WP09, WP10, WP12 · **Estimated prompt**: ~500 lines

## WP14 — Declared reader polarity

**Goal**: Every reader in the census resolves a damaged record to a declared polarity; none crashes uncaught; no safety gate fails open.
**Priority**: P2.
**Independent test**: Seed a non-UTF-8 record; every census reader behaves as declared.
**Subtasks**: T063 T064 T065 T066 · **Dependencies**: WP01, WP13 · **Estimated prompt**: ~340 lines

## WP15 — Durability coverage matrix

**Goal**: Exercise the durable path through the real command surface across verdict × lane × topology × auto-commit.
**Priority**: P1 — the commit branch has never run end-to-end through the real router.
**Independent test**: Deleting the commit call turns **each** matrix cell red.
**Subtasks**: T067 T068 T069 · **Dependencies**: WP05, WP10, WP11, WP12 · **Estimated prompt**: ~300 lines

## WP16 — Truthfulness sweep, census fold, changelog

**Goal**: Make names, documents and the changelog describe what the code does; fold the census fragments into the contract the check reads.
**Priority**: P2.
**Independent test**: No test name or contract key contradicts its assertions within the bounded denominator; the census check reads the folded contract.
**Subtasks**: T070 T071 T072 T073 T076 · **Dependencies**: WP04, WP07, WP08, WP10, WP12, WP13 · **Estimated prompt**: ~360 lines

## WP18 — Review-cycle merge driver for the two-sided `tasks/` hazard

**Goal**: Land the reconcile driver ADR 2026-08-03-1 names as a required deliverable, so a coord mission's review-cycle write cannot be clobbered by `-X theirs` during the migration window.
**Priority**: P1 — it closes the #2804 clobber shape in a directory the reconciliation guard pre-classifies as safe.
**Independent test**: Reproduce the create-window clobber (cycles on PRIMARY, cycle-1 write to COORD, `-X theirs` squash) and assert the target-side verdict survives with the driver registered — red without it.
**Subtasks**: T077 T078 T079 T080 · **Dependencies**: WP04 · **Estimated prompt**: ~430 lines

**Provenance — authored mid-mission, not part of the original slicing.** WP04's T017 required either a merge-driver diff or a re-justification backed by a test demonstrating the clobber cannot occur. WP04 established that the re-justification is *dishonest* (the create-window split makes the clobber genuinely reachable, so no honest test can show otherwise) and that the driver needs `.gitattributes`, the command table, `init.py`, `lanes/merge.py` and an upgrade migration — all outside its `owned_files`. Neither permitted discharge was achievable within its slicing boundary. The operator adjudicated: land the driver in a new WP owning that registration surface. WP04's T017 is discharged by deferral to this WP.

All six of WP18's `owned_files` were verified unowned by every other WP before it was authored, so `validate_no_overlap` is not breached.

## WP17 — Mission-exit verification

**Goal**: Discharge NFR-001 and SC-009 by diffing the measured baseline, and prove no prohibited method was used.
**Priority**: P1 — the surface most tempting to discharge by re-run.
**Independent test**: The failing node-id set is a subset of the committed baseline, and the affected-suites node-id set has not shrunk.
**Subtasks**: T074 · **Dependencies**: WP02, WP03, WP05, WP13, WP14, WP15, WP16 · **Estimated prompt**: ~200 lines

---

## MVP scope

**WP01 + WP02 + WP05.** The census makes every later target derivable, and WP02→WP05 restores coverage measurement for `src/specify_cli/review` — without which this mission cannot score itself. Nothing else can be honestly evaluated first.

## Parallelization

Widest at L3 (four packages). The real critical path, computed from the dependency blocks rather than drawn, is **WP01 → WP07 → WP11 → WP12 → WP13 → WP14 → WP17** — note it runs through the WP11→WP12 edge, and that WP10 is *not* on it.

## Post-tasks findings, recorded

A two-lens post-tasks squad found and this pass fixed: four WPs with no Definition of Done at all (WP09–WP12, the four owning every reproduced defect); a census denominator empty by construction, because the prose read a path the ownership gate forbids WP01 to write; WP14 over-claiming two files no subtask touches, which was welding it to the spine; WP11 recommending an emit-first ordering that inverts US1 AC3 under FR-001's authority; a pinned CI edge count that was both wrong and did not sum; and nine requirements claimed by nobody — including C-007, whose entire purpose is preventing a dishonest epic claim.

Two items deliberately left open:

- **`maxlane 8` is a 4× regression against this repo's precedent** (19 of the last 22 missions ran at maxlane 1). The fix is to split WP06's module in two and extract the location resolver into its own, landing maxlane ≈ 3. That is a re-slice rather than a defect fix, so it is an operator decision.
- **`analysis-report.md` does not exist yet.** `/spec-kitty.implement` refuses without it, and its freshness hash covers `spec.md`, `plan.md` and `tasks.md` — so it must be generated *after* this finalize run.

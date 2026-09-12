# Implementation Plan: Review-Cycle Verdict Seam Rebuild

**Branch**: `pr/review-verdict-write-integrity-01KZ1CGF` | **Date**: 2026-08-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md`

## Summary

The review-verdict seam has two stores answering the same question and no agreement about which one is right. The status event carries a `ReviewResult` nobody reads; the on-disk artifact carries the content the event cannot hold; several resolvers disagree about where that artifact lives; and four readers disagree about what a damaged one means.

This mission does not add another guard. It establishes one answer per question — the event is authoritative for *which* verdict is current, the artifact for *what the reviewer said* — gives the event's verdict a reader, unifies location resolution, and declares a failure polarity for every reader. The four correctness defects the spec enumerates then stop being individually-defensible states and become unrepresentable ones.

Five architecture decisions govern this mission. Four are recorded in `decisions/` (one supersedes another); the partition decision is recorded as [ADR 2026-08-03-1](../../docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md):

| Decision | Choice | Key consequence |
|---|---|---|
| Serialization boundary | Lock covers allocation + write; commit runs outside with retry-on-contention | Honours NFR-006; a contention loser retries rather than losing its verdict |
| Retired-path reconciliation | Operator-invoked repair command | No permanent read cost, no upgrade dependency; nothing reconciles unless run |
| Override authority | **Reuse the existing event-sourced `ReviewOverride`** (superseded decision — see below) | Adds no representation; retires two into it. Backed by ADR 2026-07-19-1 |
| Review-cycle partition | **COORD under coordination topologies, PRIMARY otherwise** | Verdict authority and record on one partition. Requires classifier + commit-router work and exception-absorbing migration for 45 missions. ADR 2026-08-03-1 |
| Reducer reader | Add the slot *and* re-point the safety-relevant consumers | Makes FR-001 a delivered property; largest single expansion in the mission |

**Governing ADR**: [`2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged`](../../docs/adr/3.x/2026-07-19-1-wp-runtime-state-event-log-eviction-via-innerstatechanged.md) (Accepted). It names "review-cycle fields" among the state to be evicted and pins *"one authority per datum — runtime state has exactly one read path (the reduced snapshot)"*, with the typed `WPInnerStateDelta` slot on `InnerStateChanged` as the chartered mechanism. An earlier revision of this plan cited no ADR and proposed a widened field on the transition-ledger `StatusEvent`, which the ADR forecloses.

**Superseded**: the original override-vocabulary decision offered a choice between widening `ReviewResult.verdict` and adding a flag beside it. Both options were malformed — `ReviewOverride` already exists as the declared authority, and the stated cost of the rejected alternative ("avoids widening a persisted `Literal`") was fictional: `ReviewResult.verdict` is a bare `str`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, filelock, pytest, mypy, ruff — all already present; this mission introduces none
**Storage**: append-only JSONL event log (`status.events.jsonl`) plus git-committed Markdown artifacts under `kitty-specs/<mission>/tasks/<wp>/`
**Testing**: pytest, ATDD-first per charter C-011 — every defect in scope lands its red reproduction before its fix. Fault injection uses the existing `TasksPorts` DI bundle (`FakeCoordCommitRouter`, `FakeGitOps`, `FakeFsReader`); `_do_move_task` resolves `_mt_execute` from module globals at call time, so `monkeypatch.setattr` intercepts cleanly, and `FakeCoordCommitRouter.artifact_result` is **already** a configurable constructor field. **One new test seam IS required**: `feature_status_lock` is not a port — it is imported directly and patched by module symbol in ~20 suites, so a lock acquired inside `review/cycle.py` is a different symbol those `_null_lock` patches do not reach, leaving a real lock spawning `git rev-parse` in unit tests that currently do neither.
**Target Platform**: Linux, macOS, Windows 10+ (charter DIR-001)
**Project Type**: single project — CLI tool with a shared runtime package
**Performance Goals**: verdict recording including durable persistence stays within the existing 2-second budget asserted in `tests/review/test_cycle.py`; **NFR-005's invocation clause needs restating** — measured, every verdict already costs two durable-persistence invocations (one `commit_artifact` for the record, one `commit_status` for the event), and the authority split requires both. Read literally the NFR is unsatisfiable; the countable clause must name one port method
**Constraints**: cyclomatic complexity ≤15 (`pyproject.toml` `max-complexity = 15`); `mypy --strict` and `ruff` clean with zero new suppressions; changed-line coverage ≥90%; **no lock held across a git subprocess in newly-introduced serialization** — the pre-existing hold in `coordination/transaction.py` is explicitly out of scope
**Scale/Scope**: 22 FRs, 7 NFRs, 7 constraints across ~8 source modules and an affected-suites list of 2820 tests; measured baseline of 2 pre-existing failures committed at `research/baseline-8466727eb.md`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter principle | Status | Note |
|---|---|---|
| **Single canonical authority** | **This mission's subject** | The seam violates it in four places today |
| **Architectural alignment** | Pass | Re-anchored on ADR 2026-07-19-1 after the post-plan squad found the plan cited no ADR while an Accepted one governs this exact mechanism |
| **DDD + tiered rigour** | Pass | Verdict authority, verdict record, arbiter override and location resolution are the modelled concepts |
| **ATDD-first (C-011)** | Pass, load-bearing | Three edge cases are "reproduction owed"; their red test is the first act of the concern that fixes them |
| **Terminology adherence** | Pass | Domain Language table in spec; guard run on every prose commit |
| **DIR-005** tests for new functionality | Pass | Every FR carries an acceptance scenario, verified mechanically |
| **DIR-006** mypy strict | Pass | NFR-003 |
| **DIR-009** breaking changes → CHANGELOG | Pass | FR-021 exists because an earlier revision omitted it |
| **DIR-013** pre-existing failures filed first | Pass | Both baseline failures tracked (#3157, #3160); #2804 reopened during review |
| **Model discipline** | Pass | Implementation routes to sonnet, review to opus |
| **Git workflow** | Pass | All work lands on the mission branch; the operator merges |

**Post-Phase-1 re-check**: see the note at the end of the Implementation Concern Map.

## Project Structure

### Documentation (this mission)

```
kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/
├── plan.md                          # This file
├── spec.md                          # 22 FR / 7 NFR / 7 C / 7 US / 13 SC
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/                       # census fixture + per-concern fragments
├── checklists/requirements.md       # 3 boxes deliberately unchecked
├── decisions/                       # 5 planning decisions (one supersedes another)
├── research/baseline-8466727eb.md   # measured NFR-001 baseline
└── tasks.md                         # /spec-kitty.tasks output — NOT created here
```

### Source Code (repository root)

**Derived from work-package `owned_files`, not hand-maintained.** An earlier revision of this tree was corrected by hand-adding modules a squad had named, and that pass silently dropped `src/mission_runtime/` — the module `MissionArtifactKind.REVIEW_CYCLE` lives in, i.e. the ADR's central deliverable — along with `doctor.py`, `_review_cycle_reconcile_doctor.py` and `tasks_verdict_persistence.py`. Regenerate this block from ownership rather than editing it; a hand-edited surface list has now drifted twice.

Owning work package(s) shown per file. A file with more than one owner is a convergence point and its owners carry an explicit dependency edge.

```
src/mission_runtime/artifacts.py                                 WP04          # the REVIEW_CYCLE kind, partition membership, filename-anchored classifier leg
src/mission_runtime/resolution.py                                WP04          # placement seam / E2 eligibility
src/specify_cli/agent_utils/status.py                            WP14          # the fail-open kanban reader
src/specify_cli/cli/commands/_review_cycle_reconcile_doctor.py   WP08          # NEW — the reconciliation sibling
src/specify_cli/cli/commands/agent/tasks_materialization.py      WP13          # _resolve_wp_slug AND _persist_review_artifact_override
src/specify_cli/cli/commands/agent/tasks_move_task.py            WP06          # orchestration; four verdict sites move out
src/specify_cli/cli/commands/agent/tasks_parsing_validation.py   WP14          # a fifth fail-open verdict reader
src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py  WP06,WP11,WP12# NEW — extracted verdict seam
src/specify_cli/cli/commands/agent/workflow.py                   WP16          # stale 'single mutation point' inventory docstring
src/specify_cli/cli/commands/doctor.py                           WP08          # orchestration shim — thin @app.command only
src/specify_cli/cli/commands/review/_lane_gate.py                WP07          # fourth direct caller of the conflict finder
src/specify_cli/coordination/commit_router.py                    WP04          # must stop overriding the caller's kind
src/specify_cli/merge/forecast.py                                WP07          # dry-run preview, renders verdict + path
src/specify_cli/merge/preflight.py                               WP07          # real caller of the consistency preflight + display path
src/specify_cli/orchestrator_api/commands.py                     WP07          # EXTERNAL ingress; validates ReviewResult at 4 fields
src/specify_cli/post_merge/review_artifact_consistency.py        WP07,WP13     # merge gate
src/specify_cli/review/arbiter.py                                WP12,WP13,WP14# override frontmatter + JSON sidecars, own resolver + reader
src/specify_cli/review/artifacts.py                              WP09,WP13     # ReviewCycleArtifact, cycle numbering, verdict readers
src/specify_cli/review/cycle.py                                  WP10,WP13     # writer, provenance guard, commit step — convergence point
src/specify_cli/status/models.py                                 WP07          # ReviewResult (read); ReviewOverride is the override authority
src/specify_cli/status/reducer.py                                WP07          # gains the verdict slot, distinct from `review`
```

Non-source surfaces, by group:

```
.github                      1 file(s)   WP05
docs                         4 file(s)   WP08,WP16
tests/_arch_shard_map.py     1 file(s)   WP01,WP02
tests/architectural         14 file(s)   WP01,WP02,WP04,WP05,WP08,WP16,WP17
tests/integration            2 file(s)   WP13,WP15
tests/regression             1 file(s)   WP02
tests/review                 3 file(s)   WP09,WP10,WP14
tests/specify_cli            7 file(s)   WP03,WP06,WP08,WP11,WP12,WP15
tests/status                 2 file(s)   WP02,WP07
```

`src/specify_cli/status/emit.py` is **read, not owned** — it already populates `review_result` and no work package modifies it.

**Deliberately NOT in scope**, though an earlier revision listed it: `src/specify_cli/status/work_package_lifecycle.py`. The finding behind FR-014 is that the product code there is correct; touching it is a defect, not a fix.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Reducer slot plus consumer re-pointing inside this mission | FR-001's invariant is otherwise documentation rather than a delivered property | Slot-only was offered and declined; it leaves the second authority in place, so every consumer still chooses between two answers |
| A second reducer slot alongside the existing `review` slot | The `review` slot carries the *override*; the verdict is a distinct datum | Reusing `review` would overload one slot with two facts, which is the ambiguity ADR 2026-07-19-1 exists to remove. IC-04 must name the new slot distinctly and state the precedence rule when both are populated |

The override-flag entry that stood here is **withdrawn** — it justified itself on a `Literal` that does not exist, and the decision it defended has been superseded.

## Resolved: the COORD/PRIMARY partition — ADR 2026-08-03-1

The post-plan squad found the partition for review-cycle artifacts answered two contradictory ways: the canonical glossary lists "review cycles" under COORD, while the code has no `REVIEW_CYCLE` kind and borrows `WORK_PACKAGE_TASK`, a PRIMARY member. IC-04 and IC-09 consequently specified **opposite partitions for the same fact**.

**Adjudicated in the glossary's favour** — [ADR 2026-08-03-1](../../docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md), Accepted. Review cycles are per-WP lifecycle bookkeeping, not stable planning output: written repeatedly during execution, per-WP, and belonging on the coord branch that consolidates into primary at merge.

`REVIEW_CYCLE` becomes a distinct kind in `_PLACEMENT_ARTIFACT_KINDS`. The **read seam** needs no change — verified by probe, `resolve_artifact_surface` already returns PRIMARY for a COORD kind under `SINGLE_BRANCH`/`LANES`. The **write side does not follow**, and a second adversarial pass established that a first draft of this ADR claiming "no new routing machinery" would have shipped an unimplementable change. Three mechanisms are named deliverables:

- **Path classifier** — `_artifact_kind_for_path` returns `WORK_PACKAGE_TASK` for *anything* nested under `tasks/`, and its file leg is a fixed-basename dict. `review-cycle-<N>.md` has no fixed basename, so `REVIEW_CYCLE` cannot be expressed today. Needs a nested-pattern leg, **filename-anchored** (`review-cycle-*.md`) not directory-anchored — `tasks/<wp>/` also holds `baseline-tests.json`, which is deliberately PRIMARY.
- **Commit router** — `_group_files_by_partition` re-classifies by path and *overrides the caller's kind*. Without the classifier leg, a `kind=REVIEW_CYCLE` write is re-bucketed to PRIMARY, returns `no_op_wrong_surface`, and `_commit_review_cycle_artifact` escalates to a hard error **and unlinks the artifact**. Every rejection write would fail.
- **E2 eligibility** — an explicit ruling for `REVIEW_CYCLE`, or a PUBLISHED mission's write falls through to an unconditional coordination probe.

This dissolves the IC-04/IC-09 contradiction rather than arbitrating it: the verdict authority and the verdict record now land on the **same** partition under coord topology.

**Migration is exception absorption, not empty-directory fallback.** Measured: 102 missions carry review cycles, 45 declare a coordination branch, and **zero of those branches still exist** — merge deletes the mission branch, the coordination branch *is* the mission branch, and nothing clears the `meta.json` key. The seam raises `CoordinationBranchDeleted` *before any read happens*, fail-loud by contract, and the merge gate calls it unguarded. `REVIEW_CYCLE` reads must absorb that exception to the PRIMARY directory, in **one owner function** — not per consumer, and not at the seam, which never probes artifact existence.

**Conflict rule**: when both surfaces hold a record, COORD wins under a coordination topology. This inverts `test_review_artifact_gate_ignores_stray_artifact_on_coord_husk` (PR #2834), which is re-pinned citing the ADR with a both-present case added.

**No sparse-checkout change is required.** A lane is checked out on the lane branch, so COORD content is absent regardless of patterns; a lane reaches its review cycles through the seam, which is CWD-invariant. An earlier framing of this as "the exclusion set may need to grow" was backwards.

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` translates these into executable WPs.

**The slicing constraint, and this map's compliance with it.** `validate_no_overlap` hard-fails `finalize-tasks` when two *dependency-unordered* WPs claim overlapping `owned_files`; sequential pairs are exempt, and any two **root** concerns are always concurrent. An earlier revision of this map stated that rule and then violated it six times. The dependency edges below are now drawn so that every file claimed by two concerns has a path between them.

**Two ownership rules that follow from the gate:**
- **File granularity, never directory.** `_prefix` does a string prefix test, so any directory-shaped `owned_files` entry swallows everything beneath it.
- **No concern in this mission is `scope: codebase-wide`.** That flag exempts a WP from the overlap check *and* from authoritative-surface and execution-mode checks. It is the predictable escape route from an overlap error and it is forbidden here.

**The census fixture is fragmented.** FR-020 makes `contracts/verdict-seam-census.md` the check's expected set, which would make one file a mission-wide shared write surface — exactly what the gate forbids. Each retiring concern instead writes `contracts/census/IC-NN.md`, which it alone owns; IC-12 folds the fragments into the census the check reads.

### Execution shape

```
L1  IC-01 census   IC-02 date-rot   IC-13 board-hygiene            width 3
L2  IC-04 authority   IC-03 CI-shards   IC-00 seam-extraction      width 3
L3  IC-07 reconcile-under-fan-out                                  width 1
L4  IC-06 unify-resolution   IC-09 arbiter   IC-05a   IC-05b   IC-05c   width 5
L5  IC-08 reader-polarity                                          width 1
L6  IC-11 durability-matrix   IC-12 truthfulness+census-fold       width 2
```

Recomputed from the concern bodies this plan actually ships (the earlier "12 concerns / width 2.0" figure predated the IC-05 and IC-06 splits and omitted IC-14): **17 concerns, 6 levels, mean width 2.83.**

Judge the delivered decomposition against that, not against the stale figure. `finalize-tasks` computed a 7-level DAG at mean width 2.43 — one level deeper, traceable to a single removable file-contention edge — and a **9-slot lane wall clock**, because one lane binds to one worktree and an 8-member union-find component over the overlap graph therefore runs serially. Spine length is what determines wall clock; see the post-tasks findings recorded in `tasks.md`.

### IC-00 — Extract the verdict seam out of `tasks_move_task.py`

- **Purpose**: Move the four verdict-relevant sites out of a 2554-line module into a small singly-owned one, so four later concerns stop queueing on one file.
- **Relevant requirements**: none directly — a prerequisite that makes the rest sliceable
- **Affected surfaces**: new `cli/commands/agent/tasks_verdict_persistence.py` (~150 lines), `tasks_move_task.py` (sites at ~557, ~649, ~1712-1774, ~2550)
- **Sequencing/depends-on**: none
- **Risks**: **Needs a C-003 ruling** — C-003 forbids identifier renames, and a module move changes qualified names even when local identifiers do not. The `tasks_move_task.py:36` import-cycle invariant ("none of those modules import `tasks`") must survive. A pure move shows as added lines, so the moved body carries the ≥90% diff-coverage cost — work FR-015 demands anyway.

### IC-01 — Census and architectural checks

- **Purpose**: Produce the authoritative enumeration of verdict writers, resolvers and readers, so reduction targets are derived rather than asserted.
- **Relevant requirements**: NFR-007, SC-008; input for IC-06, IC-07, IC-08, IC-12
- **Affected surfaces**: new check under `tests/architectural/`, `tests/_arch_shard_map.py` row, `tests/architectural/_baselines.yaml`, `contracts/census/IC-01.md`
- **Sequencing/depends-on**: none
- **Risks**: A `retire` row with no retiring FR is a census failure — that rule is what stops the target being self-set at zero. **Two collisions to reconcile**: `test_2093_authority_invariant.py` already imports `_EVENT_SLOTS` straight from the reducer as its single source of truth, and its `_READER_AUTHORITY_ROOTS` excludes `review`, `post_merge` and `agent_utils` — the three packages IC-08 targets. A second enumeration with a different denominator is a second authority. **Scope the census by concept** (review-cycle verdict), not by symbol signature: `pre_review_gate.py`'s `SOURCE_MISMATCH` is a deliberate fail-open owned by another mission, and `verdict_aggregation.py` is a different sense of "verdict" entirely.

### IC-02 — Time-dependent test rot

- **Purpose**: Fix #3157's test and prevent the class.
- **Relevant requirements**: FR-014, SC-013
- **Affected surfaces**: `tests/status/test_work_package_lifecycle.py`, new check under `tests/architectural/`, `tests/_arch_shard_map.py`
- **Sequencing/depends-on**: none — but shares `tests/_arch_shard_map.py` with IC-01 and IC-03, so file-granularity ownership is mandatory
- **Risks**: Ban the **mixture** of hard-coded and `now()`-generated timestamps in one event log, not the literal. **The 28-file figure this design was justified on is not reproducible** — candidate rules yield 12, 10, 48 or 64. The classifier *is* the deliverable, so IC-02 owns deriving and recording the rule, then reporting the true denominator. The product code is correct; a fix touching `work_package_lifecycle.py` is a defect.

### IC-03 — CI shard independence

- **Purpose**: Stop one failing shard starving the diff-coverage gate.
- **Relevant requirements**: FR-016, SC-010
- **Affected surfaces**: `.github/workflows/ci-quality.yml`, `tests/architectural/ci_topology_census.json`, `tests/_arch_shard_map.py`
- **Sequencing/depends-on**: IC-02
- **Risks**: A prerequisite, not P3 work — `fast-tests-review` is the only shard covering `src/specify_cli/review` and is gated on the shard #3157 keeps red. Five fast shards each cascade to an integration counterpart; both result-gating edge classes are in scope.

### IC-04 — Verdict authority and its reader

- **Purpose**: Make the reduced snapshot authoritative for *which* verdict is current, and give it a reader.
- **Relevant requirements**: FR-001, FR-022, SC-011
- **Affected surfaces**: `status/reducer.py`, `post_merge/review_artifact_consistency.py`, `merge/preflight.py`, `merge/forecast.py`, `cli/commands/review/_lane_gate.py`, `orchestrator_api/commands.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: **The reader must be snapshot-first-with-fallback, not snapshot-only.** The corpus cutover was deferred by explicit human decision; `status_phase` is per-mission opt-in and *this mission's own `meta.json` has no such key*. A snapshot-only reader returns "no verdict" for every un-migrated mission — which SC-012 declares a failure for a safety gate. IC-04 as a naive re-point manufactures the defect the mission exists to close. Add `status_phase` to IC-01's census as a governed input.
  Further: the new slot is **not** a `_RUNTIME_SLOTS` table row — it needs a new branch in `_wp_state_from_event`, a carry-forward entry, and a precedence ruling against the existing `review` slot. Adding it widens `_EVENT_SLOTS` and can red `test_2093_authority_invariant.py`'s arm 2. Ten consumer call sites across eight modules answer "which verdict is current?" from artifact frontmatter today, not the three an earlier revision named.

### IC-05a — Atomicity and crash-safety on the writer

- **Purpose**: One critical section covering cycle-number allocation and the write; no orphan on any failure path.
- **Relevant requirements**: FR-003, FR-005, NFR-006; SC-003, SC-004
- **Affected surfaces**: `review/cycle.py`
- **Sequencing/depends-on**: IC-00, IC-04
- **Risks**: **"Retry-on-index-contention" is unbuildable as recorded** — `CommitRouterResult.status` is a closed four-value Literal and an `index.lock` collision discards git's stderr, collapsing to `status="error"` with no contention signal. The buildable form uses the existing public `status.views.git_operation_in_progress()` probe (its `_GIT_OP_MARKERS` includes `index.lock`): retry when status is `error` **and** the probe fires, bounded, with a terminal hard failure. `feature_status_lock` is thread-reentrant, so no deadlock — but the write currently runs *before* `_mt_execute` takes the lock, so a lock here yields two disjoint critical sections; FR-005 must be scoped to allocation, not to the (artifact, event) pair. Acquiring the lock on a bare `tmp_path` root manufactures the stray-`.git` hazard #2990 guards; review fixtures need a real initialized repo.

### IC-05b — Verdict numbering

- **Purpose**: A new record never overwrites an existing one.
- **Relevant requirements**: FR-006; SC-002
- **Affected surfaces**: `review/artifacts.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: `max(parsed) + 1` with a collision refusal, not `len() + 1`. The refusal must cover the **unparseable** case too — `_cycle_num` returns 0 for a junk filename, so it sorts first rather than last.

### IC-05c — Transition ordering

- **Purpose**: No readable verdict survives a failed transition.
- **Relevant requirements**: FR-002
- **Affected surfaces**: `cli/commands/agent/tasks_verdict_persistence.py` (from IC-00)
- **Sequencing/depends-on**: IC-00, IC-04
- **Risks**: This is a call-ordering property, not a writer property — it could not be delivered from `review/cycle.py`, which is why it is its own concern. Note **I-1 is not deliverable under the recorded serialization boundary**: the write+commit runs before the event emit and the compensator cannot un-commit. Either weaken I-1 to "no *uncommitted* artifact survives" — which the code nearly achieves — or budget a revert-commit compensator.

### IC-06 — One location resolution, including slug derivation

- **Purpose**: Every read, write, gate and display path resolves one identical directory.
- **Relevant requirements**: FR-023, FR-007, SC-006
- **Affected surfaces**: `mission_runtime/artifacts.py` (the new `REVIEW_CYCLE` kind), `review/cycle.py`, `review/artifacts.py`, `cli/commands/agent/tasks_materialization.py`, `post_merge/review_artifact_consistency.py`, plus the inline resolvers IC-01's census names
- **Sequencing/depends-on**: see the split below — IC-06a on IC-01; IC-06b on IC-06a, IC-07, IC-05a
- **Split required.** A second adversarial pass found IC-06 had become a mega-concern. Split into:
  - **IC-06a — the kind and its plumbing.** `mission_runtime/artifacts.py` (the enum member, the partition membership, the filename-anchored classifier leg), the commit-router bucketing, the E2 ruling, and the two guard-test rows (`test_write_surface_placement_guard.py`'s `PARTITION_RATIONALE` is pinned exhaustive and reds on the enum addition alone). Zero `specify_cli` behaviour change; provable by the existing all-kinds parametrizations. **Depends on: IC-01.** This is a root-adjacent concern and IC-07 depends on *it*, not the reverse.
  - **IC-06b — consumer unification.** Slug-derivation unification (FR-007), the twelve read/write sites of which nine hard-code a PRIMARY assumption, the single owner function that absorbs `CoordinationBranchDeleted` to PRIMARY, the `review_artifact_consistency.py` docstring correction, C-001's discharge, and the fan-out narrowing. **Depends on: IC-06a, IC-07, IC-05a.**
- **Two-sided `tasks/` hazard**: `tasks` is registered in `_NON_DIVERGENT_COORD_RESIDUE_DIRS` on the justification that it is "authored once and never independently edited on the target side". The flip falsifies that — WP files on target, review cycles on the mission branch — so `-X theirs` can clobber a target-side cycle. The #2804 shape, in a directory the guard pre-classifies as safe. IC-06a owns either a reconcile driver or a documented re-justification.
- **Create-window split**: the coord worktree materialises lazily at the commit boundary, so a coord mission's *first* review cycle lands PRIMARY and later ones COORD, with `next_cycle_number` counting one surface. IC-06a must state the behaviour.
- **Risks**: **IC-07 must land first.** `_artifact_dirs_for_wp` returns a *list* — the exact dir plus every `WP01-*` sibling — and the gate iterates all of them. That fan-out is a deliberate tolerance for the divergence IC-06 fixes. Narrowing it to one resolved directory before the stranded records are reconciled makes them invisible to the gate: a fail-open window opened by a concern whose purpose is closing one. The divergence itself is **upstream** of the directory resolver, in `_resolve_wp_slug`. IC-06 also owns C-001's discharge — see the constraint note below.

### IC-07 — Reconcile records stranded under divergent paths

- **Purpose**: Find and reconcile verdict records living under paths the fan-out currently tolerates and IC-06 will stop resolving.
- **Relevant requirements**: FR-008
- **Affected surfaces**: new `doctor` subcommand (shim in `cli/commands/doctor.py` + sibling `_<name>_doctor.py`), `docs/api/cli-commands.md`
- **Sequencing/depends-on**: IC-01, IC-06a — the reconciliation must know the target partition, which is IC-06a's output
- **Risks**: Must precede IC-06b's narrowing, not follow it. FR-008's open question — whether cross-branch records under coord topology are in scope — is now answered **yes** by the partition change: pre-ADR records on PRIMARY under a coord mission are a new stranded class this concern owns. **`docs/api/cli-commands.md` regeneration is a required deliverable** — the docs-freshness workflow's `REF-MISSING` check reds on an unnamed visible path. The visible-count band (222–272, baseline 247) does not trip at 248. Check whether this duplicates the already-chartered deferred `migrate backfill-runtime-state` CLI before building a second reconciler over the same corpus.

### IC-08 — Declared reader polarity

- **Purpose**: Every reader in the census resolves to a declared polarity; none crashes uncaught; no safety gate fails open.
- **Relevant requirements**: FR-012, SC-012
- **Affected surfaces**: `agent_utils/status.py`, `review/arbiter.py`, `review/artifacts.py`, `cli/commands/agent/tasks_parsing_validation.py`
- **Sequencing/depends-on**: IC-01, IC-06, IC-09, IC-05a
- **Risks**: Five fail-open or crashing readers measured, not four — `tasks_parsing_validation.py:296` carries an explicit `# fail-open` comment and feeds the move-task review facts. The merge gate is **already** fail-closed and needs no change; record *why* — it works only because `UnicodeDecodeError` subclasses `ValueError` and `from_file` funnels `OSError` into `ValueError` too, so a future non-`ValueError` silently re-opens it. Do not sweep in `pre_review_gate.py`'s deliberate fail-open or `verdict_aggregation.py`'s different sense of "verdict".

### IC-09 — Arbiter override retirement

- **Purpose**: Retire the arbiter's two non-authoritative override representations into the event-sourced `ReviewOverride`.
- **Relevant requirements**: FR-009, FR-010, FR-011, SC-005
- **Affected surfaces**: `review/arbiter.py`, `cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`
- **Sequencing/depends-on**: IC-00, IC-04
- **Risks**: Partition resolved — ADR 2026-08-03-1 puts the override and the record it annotates on the same surface, so IC-09's "same partition as the record it annotates" and IC-04's event authority no longer conflict. The framing changed: `_persist_review_artifact_override` **already** event-sources the override durably. The residual is not "make the arbiter writer durable" — it is *retire* `persist_arbiter_decision`'s frontmatter block and JSON sidecars. The arbiter's resolver reads `feature_dir/"tasks"/wp_id` (bare id) so in the normal case it reads a directory that does not exist and returns nothing — the override is not merely un-durable, it is **never found at all**. `test_tasks_cli_contract_coord.py:721` pins the divergent bare-id directory as expected output and needs a deliberate re-pin; that re-pin belongs here, not to IC-12. Under `--json` an arbiter-persist failure produces **no output at all** — the dim-warning print is guarded by `if not json_output`.

### IC-10 — merged into IC-05a

FR-004's guard narrowing touches `_guard_feedback_source_provenance` in `review/cycle.py` — the same file as IC-05a, with no logical dependency between them. Serializing two concerns over one file for no reason costs a level; they are one concern. **The narrowing is specific**: a file that *is* a prior verdict record — by path, or by content that parses as one — stays refused. That is the #990 control and C-007 requires the PR to claim `Closes #990`. Deleting it to satisfy FR-004 is a C-002 violation.

### IC-11 — Durability coverage across the real matrix

- **Purpose**: Exercise the durable path through the real command surface.
- **Relevant requirements**: FR-013, FR-015, SC-003
- **Affected surfaces**: new tests; `cli/commands/agent/tasks_verdict_persistence.py` for FR-013's `--json` key
- **Sequencing/depends-on**: IC-03, IC-05a, IC-05c, IC-09
- **Risks**: The claim "every existing CLI test passes `--no-auto-commit`" is **false** — `test_move_task_approval_body_collision.py:139` passes `auto_commit=True`. The true gap is narrower: *no test exercises the commit branch through the real router and real git*. Left absolute, it licenses discharging IC-11 with a fake-router test. `FakeCoordCommitRouter` is already configurable — that work item is zero lines, not one. Deleting the commit call must turn each matrix cell red.

### IC-12 — Truthfulness sweep, census fold, changelog

- **Purpose**: Make names, documents and the changelog describe what the code does; fold the census fragments.
- **Relevant requirements**: FR-017, FR-020, FR-021, SC-007
- **Affected surfaces**: `contracts/verdict-seam-census.md` (the fold), `cli/commands/agent/workflow.py`, `docs/changelog/CHANGELOG.md`, three `docs/plans/` pages
- **Sequencing/depends-on**: IC-04, IC-05a, IC-07, IC-09 — it reconciles documents describing *their* outcomes and cannot precede them
- **Risks**: `workflow.py`'s docstring is wrong in three ways at once — wrong module, wrong line numbers, and "exactly one" mutation point where there are at least three. The audit denominator is machine-derivable by rule; the affected-suites list is 2820 tests.

### IC-13 — Board hygiene

- **Purpose**: Clear two pre-existing mainline reds unrelated to the seam.
- **Relevant requirements**: FR-018, FR-019
- **Affected surfaces**: the registry-parity test, the frozen flag-surface golden
- **Sequencing/depends-on**: none
- **Risks**: The only genuinely droppable concern. Note `tests/specify_cli/invocation/` is **outside** the affected-suites list, so NFR-001's node-id floor cannot observe an IC-13-induced regression there.

### IC-14 — Mission-exit verification

- **Purpose**: Discharge NFR-001 and SC-009 by diffing the measured baseline, and prove no prohibited method was used.
- **Relevant requirements**: NFR-001, SC-009
- **Affected surfaces**: `research/baseline-8466727eb.md`
- **Sequencing/depends-on**: every other concern
- **Risks**: An earlier revision left this owned by nobody — the surface where an implementer is most tempted to discharge by re-run. The node-id set is a floor: it may grow, never shrink, and a node id disappearing because the test moved, was deleted, or lost parametrization is a violation.

### Constraint notes

**C-001 must be rewritten before any concern claims it.** Its current text — *"the merge-time backstop is shown to resolve the same location the writer writes to"* — has three problems. Under IC-04 the gate no longer resolves a location for the verdict, so the predicate has no referent and is satisfiable by construction: **voided, not discharged**. Read against today's code the premise is already false, deliberately, because the fan-out resolves *many* locations precisely so it need not agree with one writer — and IC-06 would make it true in the *unsafe* direction. And C-001's own site, `tasks_transition_core.py:374-410`, was absent from the plan's surfaces entirely. The honest proposition is: *"for every accepted filename, the merge gate reaches a verdict for the work package that the writer wrote"* — testable under both the fan-out and the unified resolver, and still meaningful after IC-04.

**Cross-mission dependencies.** The `review_artifact_override_*` dual-read belongs to `wp-runtime-state-eviction-01KXWN13`'s deferred WP10 and is **RETAINED by explicit operator decision** — a cleanup pass there reverts a landed decision. `test_2684_review_override_recognition.py` pins it and is not in C-002's list.

### Post-Phase-1 Charter re-check

The single-canonical-authority principle is strengthened by IC-01, IC-04, IC-06 and IC-08 — and now correctly anchored on ADR 2026-07-19-1 rather than on an invented mechanism. The COORD/PRIMARY partition question is now adjudicated in ADR 2026-08-03-1 and folded into IC-06; no open questions remain that block slicing.

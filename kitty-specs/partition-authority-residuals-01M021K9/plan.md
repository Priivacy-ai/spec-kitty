# Implementation Plan: Coord/primary partition-authority residuals

**Branch**: `fix/partition-authority-residuals` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/partition-authority-residuals-01M021K9/spec.md`

## Summary

Finish the residual out-of-loop / cross-function callers that resolve the wrong partition surface
under coordination topology, so read and write agree per INV-5. Every partition fix is a **caller
reroute to the existing `mission_runtime.artifacts` SSOT** (no predicate fork, no membership change).
Two operator-directed scope areas: **Scope A** — partition-authority routing folds (#2959, #3439,
#2698, #2939, #2966 p2, #2937); **Scope B** — diagnostic output fidelity via canonical writer-schema
and canonical `kitty-specs/*` discovery, reducer/doctor slot fidelity, and migration-repair fidelity
(#2692, #2696, #2717, #2960, #3066). #2704 and #2973 were reparented out of #2720; completing Scope B
plus those reparents clears #2720 for close.

Technical approach: for each caller, replace the mis-resolved dir/read with the kind-aware
`placement_seam(...).read_dir(<kind>)` / `artifact_home_for(<kind>)` (Scope A) or the canonical
writer-schema / discovery source (Scope B), keeping STATUS-partition reads on COORD. Each fix carries
a **live coord-topology e2e** that is red-before/green-after (the #3437 straggler lesson).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing `spec-kitty` (typer, rich, ruamel.yaml); `mission_runtime`
(`artifacts`, `placement_seam`, `artifact_home_for`, `is_primary_artifact_kind`); `status.*`, `merge.*`,
`coordination.*`, `audit.*`.
**Storage**: git-committed mission artifacts partitioned across PRIMARY (target branch) and COORD
(coordination branch); `status.events.jsonl` event log.
**Testing**: `pytest`; **live coord-topology e2e** (`test_cli_smoke`-style create→finalize→implement
→review→merge on a coord mission) per fix, plus targeted unit tests and `tests/architectural/` guards.
Run targeted only (full suite ~1h — CI is the release authority).
**Target Platform**: Linux/macOS CLI.
**Project Type**: single (CLI).
**Performance Goals**: N/A — correctness/reliability mission (no perf budget).
**Constraints**: no predicate fork / no new legacy resolver path (C-001); STATUS reads stay COORD
(C-002); canonical schema/discovery sources (C-005); `ruff` + `mypy` clean, complexity ≤15 (NFR-003);
second-order gates green (C-003: cutover-guard `status_phase`, diff-coverage critical-paths,
compat-surface superset, completeness baselines).
**Scale/Scope**: ~13 FRs across ~10 modules; coord-topology behavior is the focus (non-coord missions
are the no-op control).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — all Scope-A fixes route through the `mission_runtime.artifacts`
  SSOT; all Scope-B fixes route through the canonical writer schema / `kitty-specs/*` discovery. No
  forked predicate, no hand-rolled key set, no ad-hoc discovery glob (C-001, C-005). ✅ by design.
- **ATDD-first / red-first** — NFR-001 mandates a red-before coord e2e per fix; unit reads alone are
  insufficient. Each WP lands its failing test first. ✅ enforced via DoD.
- **DDD + tiered rigour** — pure caller reroutes; deterministic helper extractions (schema
  derivation, discovery iterator) tested directly (Sonar new-code coverage). ✅
- **Terminology adherence** — canonical **Mission**; `feature_dir`/`feature branch` remain as existing
  code identifiers only. Run `pytest tests/architectural/test_no_legacy_terminology.py` pre-push. ✅
- **Architectural gate discipline** — watch the second-order gates a fix trips (C-003); a cutover-guard
  `status_phase` flip may be required (cf. the write-path-integrity landing). Re-check after design.

**Re-check after Phase 1**: confirm no concern introduced a predicate fork or a second canonical copy.

## Project Structure

### Documentation (this mission)

```
kitty-specs/partition-authority-residuals-01M021K9/
├── spec.md              # committed
├── plan.md              # this file
├── data-model.md        # Phase 1 — partition-kind ↔ surface table + affected callers
├── quickstart.md        # Phase 1 — how to run a coord-topology e2e locally
├── contracts/           # Phase 1 — the seam contracts each caller must honor (INV-5)
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

Brownfield — existing single-project layout. Touched surfaces:

```
src/
├── mission_runtime/artifacts.py                    # SSOT (READ-ONLY reference; do not fork)
├── specify_cli/
│   ├── policy/merge_gates.py                        # IC-02 (#3439 risk/dep gates)
│   ├── coordination/commit_router.py                # IC-01/IC-03 reference (partition split)
│   ├── cli/commands/
│   │   ├── merge.py                                  # IC-01 (#2959 escape hatch)
│   │   ├── safe_commit_cmd.py                        # IC-05 (#2966 p2)
│   │   ├── doctor.py                                 # IC-07 (#2696 --mission)
│   │   ├── retrospect.py                             # IC-07 (#2717 discovery)
│   │   └── agent/
│   │       ├── tasks_materialization.py             # IC-01 (#2959 override write)
│   │       ├── tasks_verdict_persistence.py         # IC-01 (#2959 caller)
│   │       ├── tasks_move_task.py                    # IC-03 (#2939 annotation commit)
│   │       ├── tasks_dependency_graph.py            # IC-02 (#3439 C-009 lift)
│   │       ├── workflow.py                           # IC-02 (#3439 bulk-edit diff base)
│   │       └── mission_finalize.py                   # IC-06 (#2937 wps.yaml)
│   ├── status/emit.py                               # IC-01/IC-03 (emit_inner_state_changed:971-1041)
│   ├── merge/{preflight.py,forecast.py}             # IC-01 (gate consumers)
│   ├── post_merge/review_artifact_consistency.py    # IC-01 (gate read)
│   ├── core/{worktree_topology.py,worktree.py}      # IC-04 (#2698), IC-07 (#2692)
│   ├── status/lane_reader.py                         # IC-04 (#2698)
│   ├── audit/{shape_registry.py,classifiers/meta.py} # IC-07 (#2696 schema)
│   ├── mission_metadata.py                          # IC-07 (#2696 canonical schema source)
│   └── retrospective/summary.py                     # IC-07 (#2717 discovery)
tests/
├── e2e / cli_smoke                                  # coord-topology e2e per fix (NFR-001)
├── unit (mirrors touched modules)
└── architectural/                                   # guards: no predicate fork, terminology, placement-stability (#2198)
```

**Structure Decision**: No new top-level structure. `src/mission_runtime/artifacts.py` is the SSOT and
is **reference-only** — fixes reroute callers to it, they do not modify membership. A small number of
**new shared helpers** are introduced for Scope B (one canonical `kitty-specs/*` mission-instance
iterator; one writer-schema-derived key set) — each with its own focused tests — to avoid the
two-copy trap (C-005).

## Complexity Tracking

*No Charter Check violations.* All changes are caller reroutes plus small tested helper extractions;
no new project, no new pattern, no predicate fork. Nothing to justify here.

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Merge review-artifact gate: partition-correct override + escape hatch (#2959)

- **Purpose**: Kill the coord merge deadlock — make the ReviewOverride write land on the same COORD
  `STATUS_STATE` surface the merge gate reads, and give the gate a sanctioned override escape hatch.
- **Relevant requirements**: FR-001, FR-002.
- **Affected surfaces**: `tasks_materialization.py:78-90` (`_persist_review_artifact_override` — the
  reroute is **caller-side**: resolve `placement_seam(...).read_dir(STATUS_STATE)` and pass that dir in),
  `tasks_verdict_persistence.py:547-571`, `cli/commands/merge.py:420-446` (new
  `--skip-review-artifact-check`/`--note`), gate consumers `post_merge/review_artifact_consistency.py:243`,
  `merge/preflight.py:361`, `merge/forecast.py:203`. **`status/emit.py:971-1041`
  (`emit_inner_state_changed`) stays GENERIC — do NOT make it topology-aware; fixing at the caller
  mirrors the proven `tasks_dependency_graph.py:120-135` pattern and avoids blast radius on the
  shell_pid/note/subtask annotations that also flow through it.**
- **Sequencing/depends-on**: none upstream. **Shares `emit_inner_state_changed` (emit.py:971-1041) as a
  common dependency with IC-03 — but the two fixes sit at different callers and are orthogonal (routing
  vs durability); coordinate, do NOT merge into one WP** (and do not edit the shared function for
  either). Shares the merge-preflight seam (not a function) with IC-02 — land coherently, one shared
  coord e2e (reject→override→merge).
- **Risks**: `canonicalize_feature_dir` rewrites unregistered coord paths back to PRIMARY — the e2e
  must register the coord worktree. The escape hatch must record evidence (parity with `move-task`),
  not silently bypass.

### IC-02 — Merge gates read real PRIMARY data on coord missions (#3439)

- **Purpose**: Stop the risk gate silently SKIPping and the dependency gate seeing an empty graph on
  coord missions; lift the C-009 pin.
- **Relevant requirements**: FR-003, FR-004, FR-005.
- **Affected surfaces**: `policy/merge_gates.py:86/194/242` (per-leg resolve LANE_STATE /
  WORK_PACKAGE_TASK via the seam; keep the STATUS_STATE read on coord), `workflow.py:202`
  (bulk-edit diff base), `tasks_dependency_graph.py:132` (remove the C-009 deferral note).
- **Sequencing/depends-on**: none. Coordinate with IC-01 on the **shared merge-preflight seam** (the
  `evaluate_merge_gates` orchestration pass — NOT the same module; US1's consuming gate is in
  `post_merge/review_artifact_consistency.py`). One combined coord-merge e2e can assert both a fired
  risk gate and an honored override.
- **Risks**: **first-class structural task — thread `repo_root`+`mission_slug` into the gate helpers.**
  `_evaluate_risk_gate`/`_evaluate_dependency_gate` currently take only `(feature_dir, is_blocking)` and
  have no way to build `placement_seam`; `evaluate_merge_gates` already receives `repo_root` (line 91),
  so pass it (and `mission_slug`) down and resolve LANE_STATE/WORK_PACKAGE_TASK per-leg there (proven
  pattern: `tasks_dependency_graph.py:120-135`). Must NOT over-correct the STATUS_STATE read to PRIMARY
  (C-002).

### IC-03 — Status annotation durability via emit_inner_state_changed (#2939)

- **Purpose**: Ensure the post-transition `InnerStateChanged` annotation is committed atomically so
  `move-task` never returns with a dirty status tree.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `tasks_move_task.py:2190-2318` (gather the annotation into the same
  bookkeeping transaction or a second atomic status commit), `status/emit.py:971-1041`.
- **Sequencing/depends-on**: **Shares `emit_inner_state_changed` with IC-01 as a common dependency,
  but the fix is caller-side in `tasks_move_task.py` (commit the annotation), NOT an edit to
  `emit_inner_state_changed`** — which stays generic for both concerns. Keep IC-01 and IC-03 as
  separate WPs; neither edits the shared function.
- **Risks**: also affects the non-rejection `→for_review` path when a note/agent annotation rides
  along — cover both in the e2e.

### IC-04 — Review-handoff lane read via the coord-aware surface (#2698)

- **Purpose**: Make the generated review handoff show true per-WP lane state on coord missions instead
  of a blanket stale `planned`.
- **Relevant requirements**: FR-006.
- **Affected surfaces**: `core/worktree_topology.py:147-149/207`, `status/lane_reader.py:51-76`.
- **Sequencing/depends-on**: none (independent, localized).
- **Risks**: keep the PRIMARY dir for identity/lanes/tasks; only the per-WP lane read moves to the
  coord-aware STATUS_STATE surface. Manifests only on multi-WP coord missions with stacking — the e2e
  must build one.

### IC-05 — Write-target consolidation: the 4th safe-commit sibling (#2966 part-2)

- **Purpose**: Align `_resolve_mission_aware_target` with the three siblings that already route through
  `resolve_write_target_or_degrade` (+ pre-gate + caught-set).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `cli/commands/safe_commit_cmd.py:278-307`.
- **Sequencing/depends-on**: none (independent, smallest concern).
- **Risks**: pure consolidation — but **preserve the refusal-semantics contract**:
  `CONSOLIDATED_CONTENT_ABSENT → MissionAwareCommitRefused`, and benign `FileNotFoundError`/`ValueError`
  → `None` degrade. Route through `resolve_write_target_or_degrade` without dropping that caught-set, or
  a legitimate operator commit that merely *looks* mission-scoped will start failing. Assert refusal-parity.

### IC-06 — finalize checkpoints wps.yaml (#2937) — gated on D-001

- **Purpose**: Make the finalize checkpoint reproduce its own state by committing `wps.yaml` (if D-001
  rules it versioned).
- **Relevant requirements**: FR-009.
- **Affected surfaces**: `cli/commands/agent/mission_finalize.py:187-216/449-461`,
  a `wps.yaml → TASKS_INDEX` classifier entry in `mission_runtime/artifacts.py` (membership *add* for a
  currently-unclassified file — the one place a classifier change is in play; still not a predicate fork).
- **Sequencing/depends-on**: **Decision D-001** (version vs document-as-non-versioned). If non-versioned:
  FR-009 becomes a documentation + `files_committed` reporting change instead.
- **Risks**: `wps.yaml` is operator-authored input — confirm the lifecycle before committing it.

### IC-07 — Diagnostic output fidelity: canonical schema + canonical discovery (#2692, #2696, #2717)

- **Purpose**: Source read-only diagnostics from the canonical writer schema and the canonical
  `kitty-specs/*` mission-instance discovery, eliminating false inventories / false schema findings /
  false missing-record counts.
- **Relevant requirements**: FR-010, FR-011, FR-012, FR-013.
- **Affected surfaces**: `core/worktree.py:661-706/718-721` (inventory from mission `artifacts`
  metadata; fix `research_dir` semantics) + `tests/git_ops/test_worktree.py:465,487`;
  `audit/shape_registry.py:31-47` + `audit/classifiers/meta.py:110` (derive `meta.json` known-keys from
  `mission_metadata.py:47-87` TypedDicts + coordination keys); `cli/commands/doctor.py:1258`
  (`--mission` for `coordination_health`); `retrospective/summary.py:296-303` +
  `cli/commands/retrospect.py:1003-1005` (route both through one canonical `kitty-specs/*` iterator).
- **Sequencing/depends-on**: none upstream. Internally: build the **shared discovery iterator** once and
  route both #2717 sites through it (avoid the two-copy trap); build the **writer-schema key derivation**
  once for #2696 (and reuse the artifacts-metadata source for #2692's inventory).
- **Risks**: findings are INFO severity (won't fail gates unless `--fail-on info`), so tests must assert
  the specific keys/inventory, not just exit codes. Each canonical source needs a regression test that
  goes red if the writer schema/artifact set drifts again (NFR-004).

### IC-08 — Reducer/doctor runtime-slot fidelity (#2960)

- **Purpose**: Stop `agent: ""` silently blanking recorded attribution, and stop `status doctor`
  reporting Healthy over the corrupt state.
- **Relevant requirements**: FR-014.
- **Affected surfaces**: `status/reducer.py:262-264` (replace-slot fold) + `:185` (claim arm) —
  treat empty strings as no-op; `status/models.py:460+` (`WPInnerStateDelta`) — normalize `""`→`None`
  at the write boundary so the log never records a blanking delta; `status/doctor.py` — new check for
  empty-string runtime slots on non-terminal WPs.
- **Sequencing/depends-on**: none. **Scope B (C-007): must not share a WP with any Scope-A concern.**
- **Risks**: pick the right fix altitude — write-boundary normalization is the durable net (the emit
  site producing `""` is unconfirmed); the reducer guard + doctor check are defense-in-depth. Regression
  test: fold `agent:""` over `agent:"claude"` and assert survival + a non-Healthy doctor verdict.

### IC-09 — Migration repair preserves legacy WPStatusChanged transitions (#3066)

- **Purpose**: Stop `doctor mission-state --fix` quarantining legacy `WPStatusChanged` lane
  transitions and regenerating a zero-WP `status.json` (a **data-destroying** repair, P1).
- **Relevant requirements**: FR-015.
- **Affected surfaces**: `migration/mission_state.py:1583-1667` (`_rule_reject_non_status_event` /
  `_is_preserved_non_lane_row`). Adopt PR #3067's diff: add `_is_legacy_typed_lane_transition(row)`
  (true when `event_type == "WPStatusChanged"` AND `wp_id`/`from_lane`/`to_lane` all present) and
  route it via passthrough at the head of the rule, before the quarantine branches.
- **Sequencing/depends-on**: none. **Scope B (C-007).** Reuses the existing (stale) PR #3067 diff —
  reroll it onto current main rather than re-implementing; keep its red-first migration test.
- **Risks**: TeamSpace envelopes (lane fields under `payload`) and `DecisionPointOpened` mirrors MUST
  stay quarantined — only the canonical-writer `WPStatusChanged` shape passes through. The repair is
  mutating, so the test must assert `status.json` retains the WPs after `--fix`.

### Cross-cutting notes

- **Reference implementation**: `tasks_dependency_graph.py:120-135` already performs the exact per-leg
  split this mission prescribes — `read_dir(STATUS_STATE)` (coord) + `read_dir(WORK_PACKAGE_TASK)`
  (primary) passed into an **unchanged** helper signature. Cite it as the pattern for IC-01/IC-02/IC-04;
  it proves no predicate fork and no shared-helper surgery is required.
- **Scope-A / Scope-B WP separability (C-007, HIGH)**: `/spec-kitty.tasks` MUST NOT put a Scope-A
  partition reroute and a Scope-B schema/discovery fix in the same WP — disjoint modules, different
  canonical sources, different test families (NFR-001 coord-e2e vs NFR-004 schema-drift guards). IC-01…
  IC-06 are Scope A; IC-07/IC-08/IC-09 are Scope B and decompose into their own WP(s).
- **`emit_inner_state_changed` (emit.py:971-1041) is a shared DEPENDENCY, not a shared edit**: IC-01 and
  IC-03 both flow through it but fix at their own callers; **neither WP edits the function**. This
  removes the apparent shared-file conflict.
- **Shared-seam coordination** (must not diverge): the merge-preflight pass (IC-01 + IC-02) — thread
  `repo_root`/`mission_slug` once and land both on a shared coord-merge e2e.
- **Non-coord control**: every concern's tests include a SINGLE_BRANCH/LANES control asserting identical
  behavior (the reroutes are no-ops off coord topology).
- **Second-order gates** (C-003): after design, re-check whether any concern trips cutover-guard
  (`status_phase`), diff-coverage critical-paths, the compat-surface superset, or completeness baselines.

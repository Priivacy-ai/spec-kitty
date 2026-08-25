# Implementation Plan: M8 — Lane-allocation single-seam (recurrence prevention for #3571)

**Branch**: `rc3-lane-allocation-single-seam-01M0GGX8` | **Date**: 2026-08-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/rc3-lane-allocation-single-seam-01M0GGX8/spec.md`

> **Branch contract (stated twice per plan doctrine).** Current branch at plan start:
> `rc3-lane-allocation-single-seam-01M0GGX8`. Planning/base branch: same. Final merge target:
> the feature branch `rc3-lane-allocation-single-seam-01M0GGX8` — `spec-kitty merge` consolidates
> locally; the PR to `upstream/main` is the closeout and **the operator merges**. `meta.target_branch`
> still records the merged+deleted `pr/rc3-friction-mission-specs`; it is corrected to the feature
> branch at `finalize-tasks --target-branch rc3-lane-allocation-single-seam-01M0GGX8`.

## Summary

M8 is the **structural home** that prevents recurrence of the #3571 class: *an allocation/resolution
decision has two+ disjoint routes and an override/flag/field reaches only one, so the dominant route
silently discards operator intent while reporting success.* M1 (`#3571`, `4dab528545`) + `#3618`
already landed the **point-fix** — `base` threading, `UnhonorableBaseError`, `_guard_base_honorable`,
`_resolve_lane_parent`, structural lane-reuse detection. M8 **generalizes around** that work (C-001):
it folds the two landed helpers into **one** `resolve_lane_base_or_refuse` seam returning a
`LaneBaseDecision`, routes every allocation route through it, adds a structural **anti-bypass guard**,
makes the topology predicate authoritative on its **residual** surrogate sites, ships the **read-side
degrade companion** `resolve_read_dir_or_degrade`, and fixes the **#3536** un-followable no-coord
refusal remedy — all under the fail-loud contract (epic #3410).

**Technical approach:** mirror the proven write-side precedent
`resolve_write_target_or_degrade` (`src/mission_runtime/write_target_degrade.py:67`). Three sibling
seams share one family and vocabulary — **write** (exists), **read** (new, #3462), **allocate**
(new, subsumes M1's `base`) — over the single authoritative topology predicate
`_transaction_topology_available` (#3460). Every route is red-first (ADR `2026-07-17-1`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib + existing internal packages (`specify_cli.coordination`,
`specify_cli.lanes`, `specify_cli.status`, `mission_runtime`); `subprocess` (git); no new third-party deps
**Storage**: git worktrees + branches; `lanes.json`, `meta.json`, `status.events.jsonl` (files) — N/A DB
**Testing**: pytest (unit + architectural). Red-first per cell. Anti-bypass = architectural test
(`tests/architectural/`). No `-n0` daemon/real-port tests introduced.
**Target Platform**: Linux/macOS/Windows dev host (cross-platform CLI, DIR-001)
**Project Type**: single project (CLI library — `src/specify_cli/` + `src/mission_runtime/`)
**Performance Goals**: N/A — allocation is a human-cadence CLI operation; the seam adds no hot-loop cost
**Constraints**: ruff + mypy clean, zero new suppressions; complexity ceiling 15 (S3776/C901);
no new dependency (supply-chain section N/A); NFR-001 byte-identical parentage when no override supplied
**Scale/Scope**: 5 WPs across the coordination core; ~6 files touched for the seam + ~5 read-side
migration sites + 2 files for #3536. Wide blast radius → adversarial squad point-cut warranted.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first (C-011):** every route and helper lands red-first. The anti-bypass guard (FR-007) is
  itself a red-first architectural test. ✅ planned.
- **Canonical sources (no improvisation):** the seam mirrors the existing write-side helper contract
  rather than inventing a new shape. ✅
- **Terminology Canon:** no `feature*` aliases; "Mission" not "feature". Run
  `tests/architectural/test_no_legacy_terminology.py` before push (prose touched). ✅ planned.
- **Regression vigilance:** guardrails that MUST stay green — #2993 (reuse self-heal), #2512/#2514
  (crash-recovery + sparse-checkout), #1684 (dependency-tip propagation), #1915 (atomic dep-merge
  rollback), #2939 (`test_flat_topology_annotation_still_lands`), #1848 (data-loss re-raise). ✅ tracked.
- **NFR-001 backward-compat:** dominant coord path and legacy `mission_branch` path keep current
  parentage when no override supplied — only the bypass hazard is removed. ✅
- **No new dependency** → supply-chain gate N/A. ✅
- **Ownership boundary:** M8 owns the allocation/degrade/predicate seams; it does NOT change coord/primary
  partition *semantics* (out of scope). ✅

No violations requiring Complexity Tracking justification.

## Project Structure

### Documentation (this mission)

```
kitty-specs/rc3-lane-allocation-single-seam-01M0GGX8/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (the LaneBaseDecision / ReadDirDecision value objects)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (seam contracts + anti-bypass-guard contract)
└── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── lanes/
│   └── worktree_allocator.py        # WP2: fold _guard_base_honorable + _resolve_lane_parent
│                                     #      into resolve_lane_base_or_refuse -> LaneBaseDecision;
│                                     #      route fresh-coord / fresh-legacy / reuse / crash-recovery
├── coordination/
│   ├── status_transition.py         # WP1: authoritative predicate residual (DO NOT touch :1481 emit site)
│   ├── commit_router.py             # WP5: #3536 route/remedy
│   └── policy.py                    # WP5: #3536 refusal message :225-236 (thread topology; cross-ref #2739)
├── status/aggregate.py              # WP4: migrate onto read companion — PRESERVE #1848 re-raise (:351)
├── retrospective/generator.py       # WP4: migrate (:264) — CO-EDIT with M5, per-symbol ownership
├── core/worktree_topology.py        # WP4: migrate (:173)
└── cli/commands/
    ├── agent/status.py              # WP4: migrate (:154, :195)
    └── _review_cycle_reconcile_doctor.py  # WP4: migrate

src/mission_runtime/
├── write_target_degrade.py          # precedent to mirror (unchanged)
├── read_dir_degrade.py              # WP4: NEW — resolve_read_dir_or_degrade companion
├── resolution.py                    # WP1: residual surrogate census (:1284, :1362, :1460)
└── context.py                       # WP1: residual surrogate census (:70)

tests/
├── architectural/
│   └── test_lane_allocation_single_seam.py   # WP3: NEW anti-bypass guard (FR-007)
├── specify_cli/lanes/               # WP2 seam unit + route coverage
├── coordination/                    # WP1 predicate residual + WP5 #3536
└── mission_runtime/                 # WP4 read companion unit
```

**Structure Decision**: single project. The seam lives where its consumers live — the allocation seam
in `lanes/worktree_allocator.py` (co-located with `allocate_lane_worktree`), the read companion in
`mission_runtime/` beside its write-side sibling `write_target_degrade.py` (one family, one directory).

## Parallel Work Analysis

> Topology is `single_branch` → WPs execute sequentially in one workspace; the graph below is the
> **logical** dependency + ownership map, not a parallel-lane assignment.

### Dependency Graph

```
WP1 (#3460 predicate anti-divergence guard) ──→ WP5 (#3536 refusal; needs the no-coord answer)
WP2 (allocation seam) ─┐
                       ├─→ WP3 (anti-bypass guard: tests WP2's seam AND WP4's read migration)
WP4 (#3462 read companion + migration) ─┘
```

Execution order (single_branch, sequential): **WP1 → WP2 → WP4 → WP3 → WP5.**

- **WP3 depends on BOTH WP2 and WP4** (post-plan squad, paula MED): the guard's assertion 3 checks WP4's
  read-migration allowlist, so WP3 cannot land before WP4. WP3 may be *authored* red-first early (a guard
  naming a not-yet-existent seam is a legitimate red anchor) but not *approved* until WP2+WP4 land.
- **WP5 after WP1**: consumes the authoritative predicate's no-coord answer (INV-3536-3, #2739 convergence).
- **WP1 first** (lowest risk — an enforcement/anti-divergence test, no code change; census found zero
  residual gates). **WP2** is the core seam. **WP4** ships the read companion for its two genuine degrade
  consumers before the guard (WP3) can assert the read family.

> **Honest scope (post-plan squad — stated plainly).** M8 is a **consolidation / anti-divergence refactor
> plus one user-facing fix (WP5/#3536)**, NOT a #3571 reproduction — M1 already closed the live P0. WP1,
> FR-002, and most of WP4's error vocabulary are already satisfied on `main`; M8's value there is
> *enforceability* (the seam + the anti-bypass/anti-divergence guards). Net-new behavior concentrates in
> WP5. Issue-closure text credits M8 only for the guard/consolidation, not for M1/#3618/prior-WP05 work.

### Work Distribution

- **Sequential work (foundation):** WP1 authoritative-predicate residual (unblocks WP5's no-coord answer).
- **Core:** WP2 shared allocation seam (subsumes M1's `base`, C-001 reference-not-duplicate).
- **Independent streams:** WP4 read-side companion (read path, disjoint from allocation).
- **Ownership to avoid conflict:** `retrospective/generator.py` is co-edited by running **M5**
  (#2901 reader convergence). Verified disjoint symbols (post-plan squad, paula): M8 owns `_load_traces`
  (`~:224-299`, the trace-read degrade `try/except` `~:264`); M5 owns `generate_retrospective` (`~:1319`)
  — ~1000 lines apart. The **one shared hunk** is the top-of-file import region (`~:20-33`). Mitigation:
  M8's WP4 keeps the new `resolve_read_dir_or_degrade` import **function-local** (matching the existing
  function-scoped-import pattern in `_load_traces` AND the `mission_runtime` layering constraint), so the
  import block stays untouched. Note the import region as the sole shared hunk in the PR body; whoever
  lands second rebases.

### Coordination Points

- **Guardrail regression sweep** after WP2 and WP4: targeted runs of #2993 / #2512 / #2514 / #1684 /
  #1915 / #2939 / #1848 coverage before each WP is marked for review (NOT the full ~1h suite — targeted).
- **#3536 ↔ #2739 convergence check** during WP5: confirm the unified predicate exposes the no-coord
  answer #2739's sub-issues also need, so the two protected-primary fixes converge, not diverge.
- **Adversarial squad point-cut** pre-merge (coord-topology core, wide blast radius) per charter cadence.

## Complexity Tracking

*No Constitution Check violations require justification.* The one complexity risk is the seam's
`resolve_lane_base_or_refuse` staying under the S3776/C901 ceiling of 15 while subsuming four routes'
guard logic — mitigated by keeping the positive parent-choice and the four fail-loud triggers as
flat, separately-tested helpers behind the seam (the shape M1 already established with
`_guard_base_honorable`).

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

# Phase 1 Data Model: CI Topology Shrink & Guard Un-Blinding

**Mission**: `ci-topology-shrink-01KWQAVX` | **Date**: 2026-07-04

This mission has no runtime datastore. The "entities" are the **parsed relations of the bound
`_gate_coverage` model** and the committed census/timings artifact. Each is a static structure the
architectural invariants assert over — modeled here for traceability to the spec's Key Entities.

> **Quickstart / contracts N/A**: no user-facing runtime API, HTTP surface, or CLI command is added. The
> only "contract" is the invariant suite over the parsed workflow model, authored as red-first test code
> (see plan.md WP-red), not as `contracts/*` schema files. Recorded here per the plan-template rationale.

## Entities

### Worklist census artifact — `tests/architectural/ci_topology_census.json`

The construction-derived authority SC-001 iterates (NFR-006).

| Field | Type | Meaning |
|-------|------|---------|
| `t_loc` | int | Committed LOC floor (`T_LOC`, recommended 500) — the plan-time constant, NOT in the test |
| `rule` | str | The derivation predicate (dir ≥ `t_loc` LOC ∧ no src-backed group) |
| `worklist[]` | list | Each: `{ dir, loc, cone_roots[], target_group, target_shard }` |
| `mapped_dirs[]` | list | The 23 already-mapped dirs (oracle, for the negative assertion) |
| `arch_blind_groups[]` | list | The 13 Mode-B groups (un-blind targets) |
| `timings_baseline` | obj | `{ fast_core_misc_min: 17.0, arch_shard_min: 12.3, critical_path_min: 29.4, next_lane_min: 13.6, source_run_id: 28705381819 }` (NFR-001) |

### Filter group (dorny) — parsed via `WorkflowModel.filter_groups`

`name → tuple[glob, …]`. **Src-backed** iff ≥1 glob starts with `src/` (`_group_is_src_backed`). Src-backed
groups (minus `any_src`) join the `unmatched` enumeration (FR-010c). New composite groups are src-backed by
construction (their globs are `src/specify_cli/<member>/**`).

### Shard job — a `Gate` = `(workflow, job, shard, paths, ignores, marker_expr)`

Parsed by `_gate_coverage.parse_workflow`. Kinds: `fast-tests-<group>`, an
`integration-tests-core-misc` matrix entry (`shard`), or the new always-on `arch-adversarial` job. Each
emits `coverage-<name>.xml` (FR-006, glob-consumed). The always-on arch job is the special case: whole-tree
paths + `architectural`-family marker + NO filter-group `if:` (Option A).

### Bound model — `_gate_coverage.py` + `_gate_coverage_baseline.json`

The parsed authority. `WorkflowModel` fields already expose `filter_groups`, `job_needs`,
`job_gating_groups`, `cov_targets`, `diff_cover_critical_paths`, `pull_request_types`. **Additive
extensions** this mission introduces (C-001 additive; NFR-007):

- **Differential-matrix relation (NFR-002)**: `{ dir → arch_selected: bool }` over every `src/specify_cli/*`
  dir; fails if any dir is arch-blind. With the always-on arch job (no src path filter) every dir is
  selected by construction.
- **Same-tier uniqueness relation (NFR-003)**: `{ test → count_fast_shards, count_integration_shards }`;
  fails if either > 1. Distinct from the existing report-only cross-tier duplicate count (3 550).

Baseline invariants held constant: `total_tests = 28573`, `orphan_test_count = 0` (SC-004).

### Needs-list — a job's `needs:` set (coverage integrity, C-005)

| Consumer | Authority | C-005 binding |
|----------|-----------|---------------|
| `quality-gate.needs` | blocking-set (already FR-011-bound via `toJSON(needs)`) | membership of all new jobs |
| `sonarcloud.needs` | hand-maintained | **coverage-emitting jobs ⊆ this** (NEW invariant) |
| `diff-coverage.needs` | hand-maintained | **critical-path emitters ⊆ this** (NEW invariant) |
| `slow-tests.needs` | fast-jobs-only | **do NOT add integration/arch jobs** (would red) |
| `mutation-testing.needs` | `if: false`, parsed | mirror where it consumes coverage |

## State transitions (topology, not runtime)

```
UNMAPPED dir --[5-edit atomic registration, FR-002]--> MAPPED to composite group + focused shard
MAPPED arch-blind group --[always-on arch job, FR-005/013]--> ARCH-RUN (Mode-B closed for all 13 at once)
fast-core-misc (unsharded, serial arch behind it) --[FR-003 matrix split + FR-013 de-serialize]--> parallel focused shards + parallel always-on arch pole
```

Each transition must keep the 8 #2368 invariants + the new NFR-002/003/005 + C-005 relations green
(NFR-007) and the ratchet totals unchanged (SC-004).

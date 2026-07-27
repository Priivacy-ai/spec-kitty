# Implementation Plan: CI Topology Shrink & Guard Un-Blinding

**Branch**: `tidy/ci-topology-shrink` | **Date**: 2026-07-04 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `kitty-specs/ci-topology-shrink-01KWQAVX/spec.md`

## Summary

Extend the bound `_gate_coverage` marker→job model (consume, don't rebuild — C-001) so that (1) every
`src/specify_cli/*` dir on a **construction-derived worklist** (NFR-006) maps to a named filter group and
a focused shard — closing Mode-A `unmatched→run_all` blast radius (FR-001/002); (2) the architectural +
adversarial suite runs on **100%** of src changes via an **always-on arch job that adds no filter group**
(Option A) — closing Mode-B arch-blindness across 13 groups / 120k LOC (FR-005); and (3) that same arch
job is **de-serialized** from `fast-tests-core-misc` and `fast-tests-core-misc` is matrix-sharded, cutting
the core-misc critical path from a live-measured **29.4 min → ≤13.6 min** (FR-003/013, NFR-001). Un-blind
(pillar 2) and wallclock (pillar 3) are solved by the **same** arch-pole move. All 8 #2368 invariants stay
green; new invariants (NFR-002/003/005, C-005) are additive to the bound model (NFR-007).

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: GitHub Actions workflows (`ci-quality.yml`, `ci-windows.yml`) + `dorny/paths-filter@v4`
+ pytest (marker-expression selection via `_pytest.mark.expression`) + the bound `_gate_coverage` model
(`tests/architectural/_gate_coverage.py` + `_gate_coverage_baseline.json`) + `scripts/ci/quality_gate_decision.py`
(`JOB_GROUPS` heredoc)
**Storage**: N/A (CI configuration + a committed census/timings artifact, no runtime datastore)
**Testing**: architectural invariant suite (`tests/architectural/`), red-first — new invariants authored
failing, then satisfied by the workflow edits; ratchet against `_gate_coverage_baseline.json`
**Target Platform**: GitHub Actions CI (ubuntu-latest lanes; windows-latest second layer)
**Project Type**: single
**Performance Goals**: NFR-001 — post-mission core-misc critical path **≤ 55% of the committed 29.4-min
baseline AND ≤ the next-longest independent lane (13.6 min)** ⇒ effective ceiling ≈ **13.6 min**
**Constraints**: all **8 #2368 WP04 invariants** green through every WP (NFR-007) + C-001..006; additive
extension only; no split-brain derived surface (C-002); single-owning WP for `ci-quality.yml` (C-003);
coverage-consumer integrity bound to `sonarcloud.needs`/`diff-coverage.needs`, NOT `slow-tests.needs` (C-005)
**Scale/Scope**: ~32 unmapped worklist dirs / ≈68k LOC (Mode A, `T_LOC=500`) + 13 arch-blind groups /
≈120k LOC (Mode B); one 3307-line `ci-quality.yml`; 4 suite-running workflows in the parsed model

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Canonical sources & unification (Directive 044, C-001)** — PASS. Extends the single bound
  `_gate_coverage` authority additively; does not fork a parallel selection model or rebuild the
  marker→job substrate (#2034/#2368).
- **Close defect classes by construction (Directive 043)** — PASS and central. Mode-A (`unmatched`
  blast radius), Mode-B (arch-blindness), and the coverage-consumer drop (C-005) are each closed by a
  *structural* invariant in the parsed model, not by discipline reminders.
- **No split-brain derived surfaces (C-002, Decision 8)** — PASS. Every new derived surface (catch-all
  OR-list, `JOB_GROUPS` heredoc, `ci-windows` static list) is asserted-against-parsed-source.
- **Tests as scaffold, not friction (Directive 041)** — PASS. New invariants pin *behavioral relations*
  (a dir routes to a group; the arch job selects 100% of dirs), not workflow line numbers; refactor-stable.
- **Additive-only / consumes substrate (C-001)** — PASS. Charter Check passes; no violations require
  Complexity-Tracking justification beyond the honest WP sizing below.

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-topology-shrink-01KWQAVX/
├── plan.md              # This file
├── research.md          # Phase 0 — census, baselines, routing table, arch-pole mechanism
├── data-model.md        # Phase 1 — bound-model entities (Key Entities from spec)
├── spec.md              # Authority (FR/NFR/C/SC)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

Quickstart / contracts: **N/A** — this is CI-infra + invariant-suite work with no user-facing runtime API
or HTTP/CLI contract surface. The "contract" is the set of architectural invariants over the parsed
workflow model; those are authored as red-first test code (WP02), not as `contracts/*` schema files.

### Source Code (repository root — real files this mission touches)

```
.github/workflows/
├── ci-quality.yml          # SINGLE-OWNER WP (C-003): filter groups, changes.outputs rows,
│                           #   unmatched loop, fast-core-misc matrix split + --ignore mirror,
│                           #   integration matrix ignore_args, arch-pole extraction/de-serialization,
│                           #   coverage-consumer needs-lists, JOB_GROUPS heredoc
└── ci-windows.yml          # SECOND-LAYER WP: static windows_critical list (:24-42) for relocated
                            #   windows-marked test files (FR-008)

scripts/ci/
└── quality_gate_decision.py  # (consumes JOB_GROUPS payload; edited only if the heredoc moves — the
                              #   heredoc itself lives in ci-quality.yml)

tests/architectural/
├── _gate_coverage.py               # additive parse extension (differential-matrix relation, NFR-002;
│                                   #   same-tier uniqueness relation, NFR-003)
├── _gate_coverage_baseline.json    # ratchet baseline refresh at closeout (total/orphan unchanged)
├── test_src_filter_coverage.py     # existing FR-010/012/013 invariants (must stay green)
├── test_workflow_coherence.py      # existing FR-003/005/008/011 invariants (must stay green)
├── test_marker_job_completeness.py # existing marker-completeness invariants (must stay green)
├── test_ci_topology_worklist.py    # NEW — SC-001: census iteration (0 dirs → run_all)
├── test_arch_unblind_matrix.py     # NEW — SC-002/NFR-002: arch selects 100% of src dirs
├── test_same_tier_uniqueness.py    # NEW — NFR-003: no test in >1 fast shard nor >1 integration shard
├── test_coverage_consumer_needs.py # NEW — C-005: cov emitters ⊆ sonarcloud/diff-coverage needs
├── test_job_count_ceiling.py       # NEW — NFR-005: len(quality-gate.needs) ≤ ceiling
└── ci_topology_census.json         # COMMITTED artifact (json only, underscore): worklist (T_LOC + dirs)
                                     #   + 29.4-min timings baseline; SC-001/NFR-001/NFR-006 authority the
                                     #   tests iterate. Lives under tests/architectural/, NOT kitty-specs/.
```

**Structure Decision**: single-project CI-infra. The load-bearing constraint is C-003: `ci-quality.yml`
is a **shared hot file** edited by ONE owning WP (the `lanes` allocator rejects overlapping `owned_files`,
so per-slice WPs cannot co-own it). WPs partition **by FILE** (workflow / bound-model / invariant-tests /
ci-windows / census-artifact), never by slice.

## Complexity Tracking

*No Charter Check violation requires justification.* The table below records the honest WP-sizing shape
(the pre-spec + post-spec squads called ~8-10 WPs; C-003 forces the workflow edits into ONE WP, so the
realistic count is ~7-8). WP shape = **spine → red-first invariants → single-owner workflow → second-layer
→ verify → closeout**, partitioned BY FILE.

| Aspect | Decision | Why / Simpler alternative rejected |
|--------|----------|-------------------------------------|
| `ci-quality.yml` ownership | ONE WP owns all group+shard+arch-pole+needs+heredoc edits (WP03) | Per-slice WPs editing one file cannot be `owned_files`-disjoint; the `lanes` allocator rejects overlap (C-003). If per-slice edits become unavoidable → flatten to `single_branch` with linearized shared-surface edits (docs-consolidation pattern) — a plan-time topology decision. |
| Composite vs dedicated jobs | Composite filter groups mirroring the 6 integration shards (FR-010) | ~32 dedicated `fast/integration-tests-<D>` jobs balloon `quality-gate.needs` (~45 today) past the NFR-005 ceiling; composites cap it (~57). |
| Arch-pole realization | Always-on standalone job, NO filter group (Option A) | Adding a filter group for "arch runs everywhere" would perturb `src_backed_groups`/`compute_unmatched` and red the FR-010 invariants; Option A leaves the parsed relations untouched (C-001). |
| WP count | ~7-8 (not per-slice-vertical) | The scope-doc's per-slice-vertical sketch pre-dated C-003; single-file ownership collapses the vertical WPs into WP03. |

### Honest WP-shape sketch (authoritative decomposition is /spec-kitty.tasks)

- **WP-spine** — census artifact (`tests/architectural/ci_topology_census.json`: `T_LOC`, worklist, 29.4-min timings baseline) +
  routing table + additive `_gate_coverage` parse extension (differential-matrix + same-tier relations) +
  ONE reference slice (dossier — it also fixes the latent integration-shard gap) establishing the recipe.
- **WP-red** — red-first invariants: `test_ci_topology_worklist` (SC-001), `test_arch_unblind_matrix`
  (SC-002/NFR-002), `test_same_tier_uniqueness` (NFR-003), `test_coverage_consumer_needs` (C-005),
  `test_job_count_ceiling` (NFR-005). Authored FAILING against today's topology.
- **WP-workflow (SINGLE-OWNER `ci-quality.yml`)** — ALL edits: composite filter groups + `changes.outputs`
  rows + `unmatched` loop + `fast-tests-core-misc` matrix split + `--ignore` mirror + integration
  `ignore_args` for nested roots + arch-pole extraction/de-serialization + coverage-consumer needs-lists +
  `JOB_GROUPS` heredoc. Turns WP-red green.
- **WP-second-layer** — `ci-windows.yml` static `windows_critical` list for any relocated windows-marked
  file (FR-008); confirm `quality_gate_decision.py`, `drift-detector.yml`, `release.yml` need NO shard/
  ignore edits (they carry none).
- **WP-verify** — fresh per-shard timings vs the committed baseline (NFR-001 acceptance observation);
  each shard emits `coverage-*.xml` (FR-006); C-006 nightly-option decision iff post-shrink critical path
  still >15 min.
- **WP-closeout** — `_gate_coverage_baseline.json` refresh (total/orphan unchanged), #1931 rollup, close
  #2378/#1933/#2383, CHANGELOG (root symlink → `docs/changelog/`).

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Single-owner workflow surface & topology partition

- **Purpose**: `ci-quality.yml` is one shared hot file; all group/shard/arch-pole/needs/heredoc edits must
  land in a single owning WP so lane ownership is disjoint and the derived surfaces stay coherent.
- **Relevant requirements**: C-003, C-002, FR-002, FR-003, FR-004, FR-010.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (dorny filters, `changes.outputs`, `unmatched`
  loop `:309-329`, `fast-tests-core-misc` `:1321-1376`, `integration-tests-core-misc` matrix `:1430-1564`,
  `JOB_GROUPS` heredoc `:3219-3258`).
- **Sequencing/depends-on**: IC-03 (worklist) + IC-04 (registration recipe) + IC-06 (uniqueness) inform it;
  IC-05 needs-lists edited in the same WP.
- **Risks**: the `lanes` allocator rejects overlapping `owned_files` — WPs MUST partition by FILE, not
  slice; if per-slice edits become necessary, flatten to `single_branch` (linearized). Topology is a
  plan-time decision.

### IC-02 — Arch-pole de-serialization & always-on un-blind (FR-013)

- **Purpose**: extract the `architectural` matrix shard into a standalone always-on job, drop its
  `needs: fast-tests-core-misc`, so the arch/adversarial suite runs on 100% of PRs in parallel with the
  fast lane — the SINGLE object solving Mode-B blindness (US2) AND the wallclock long pole (US3).
- **Relevant requirements**: FR-005, FR-013, NFR-001, NFR-002, NFR-004.
- **Affected surfaces**: the extracted `arch-adversarial` job; removal of the serialization `needs`; its
  addition to `quality-gate.needs` + `sonarcloud.needs` + `diff-coverage.needs`.
- **Sequencing/depends-on**: within IC-01's WP; the NFR-002 differential-matrix invariant (IC-04) guards it.
- **Risks**: the always-on job must carry NO filter-group `if:` (else it perturbs `src_backed_groups` and
  reds FR-010c/FR-011); its coverage must land in the aggregator `coverage-*.xml` glob (FR-006).

### IC-03 — Census-driven worklist (NFR-006)

- **Purpose**: the FR-001 worklist is computed (`T_LOC` floor + no-src-backed-group predicate), committed
  as an artifact the SC-001 test iterates — so the metric measures coverage, not the implementer's constant.
- **Relevant requirements**: NFR-006, FR-001, SC-001.
- **Affected surfaces**: `tests/architectural/ci_topology_census.json` (json only, underscore — NOT under `kitty-specs/`); `test_ci_topology_worklist.py`.
- **Sequencing/depends-on**: feeds IC-01 (which groups to add).
- **Risks**: `T_LOC` is a committed constant — pin it in the artifact, not the test; the sub-`T_LOC` tail
  is catch-all-safe (FR-009), not a coverage regression.

### IC-04 — Atomic 5-edit group registration + invariant integrity (FR-002, NFR-007)

- **Purpose**: each new composite group changes ALL five bound-model surfaces in one commit (filter glob,
  `changes.outputs` row, `unmatched` loop entry, ≥1 job `if:`, `JOB_GROUPS` row); the 8 #2368 invariants
  and the new NFR-002/003 relations stay green throughout.
- **Relevant requirements**: FR-002, NFR-007, NFR-002, C-002.
- **Affected surfaces**: `_gate_coverage.py` (additive parse), the 5 `ci-quality.yml` surfaces,
  `test_arch_unblind_matrix.py`.
- **Sequencing/depends-on**: recipe established by the WP-spine reference slice; consumed by IC-01.
- **Risks**: a partial (< 5) edit reds FR-010c/FR-010c-2nd-arm/FR-011 — the invariants are the safety net;
  authoring order is red-first (IC-06 WP-red before IC-01 WP-workflow).

### IC-05 — Coverage-consumer integrity by construction (C-005 — CORRECTED target)

- **Purpose**: a new invariant binds **coverage-emitting jobs ⊆ `sonarcloud.needs`** and **critical-path
  emitters ⊆ `diff-coverage.needs`** (and `mutation-testing.needs` where it consumes them) so a new
  `fast-tests-<group>` cannot silently drop its `coverage-*.xml` from Sonar.
- **Relevant requirements**: C-005, FR-006, FR-007.
- **Affected surfaces**: `sonarcloud.needs` (`:2517-2552`), `diff-coverage.needs` (`:2370-2387`);
  `test_coverage_consumer_needs.py`.
- **Sequencing/depends-on**: same WP as IC-01 (needs-lists live in `ci-quality.yml`).
- **Risks**: do **NOT** intersect `slow-tests.needs` — it lists fast jobs ONLY and would red on arrival
  (spec correction). `mutation-testing` is `if: false` (disabled) but still parsed — mirror its consumer set.

### IC-06 — Same-tier selection uniqueness (NFR-003)

- **Purpose**: a mechanized invariant asserts no test is selected by >1 fast shard nor >1 integration
  shard (distinct from the existing report-only cross-tier duplicate warning); total `run_all` selected
  count unchanged; orphan count stays 0 (baseline 28 573).
- **Relevant requirements**: NFR-003, SC-004.
- **Affected surfaces**: `_gate_coverage.py` (same-tier relation over `Gate` list);
  `test_same_tier_uniqueness.py`; `_gate_coverage_baseline.json` (refreshed, unchanged totals).
- **Sequencing/depends-on**: WP-red (authored before the split); guards IC-01's `--ignore`/`ignore_args`.
- **Risks**: nested `tests/specify_cli/<D>` roots (orchestrator_api, bulk_edit) double-run unless the
  integration-matrix `ignore_args` is hand-updated (FR-004, NOT covered by FR-012's whole-tree check);
  the migration double-root + `and not slow` must consolidate without double-running the `@slow` perf test.

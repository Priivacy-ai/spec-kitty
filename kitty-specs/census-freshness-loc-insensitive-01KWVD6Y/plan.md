# Implementation Plan: LOC-insensitive census freshness gate

**Branch**: `fix/census-freshness-loc-insensitive` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/census-freshness-loc-insensitive-01KWVD6Y/spec.md`
**Tracker**: [Priivacy-ai/spec-kitty#2416](https://github.com/Priivacy-ai/spec-kitty/issues/2416)

## Summary

Narrow the CI-topology census freshness gate so it stops reddening unrelated PRs on
exact line-count churn. The fix is applied at the **shared derivation**
(`tests/architectural/_gate_coverage.py::live_derived_worklist`): drop the exact `loc`
field from worklist entries and stop LOC-driven ordering, so the committed census
carries only membership + routing plan (`dir`, `cone_roots`, `target_group`,
`target_shard`). The freshness test compares an order/LOC-insensitive dir-keyed index;
the LOC floor is re-verified against the **live** tree instead of a stored snapshot.
Because the `--verify-census` CLI consumes the same derivation, both surfaces become
LOC-insensitive by construction. All three anti-tamper teeth (hand-trim,
floor-crossing, new-hot-dir) plus the order-insensitivity tooth are preserved by
non-vacuous self-mutation tests, and the ATDD red-first reproduction uses a
rank-altering churn so FR-001 and FR-007 cannot ship vacuously.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest 9.0.3 (`_pytest.mark.expression`), PyYAML — no new dependencies
**Storage**: Committed JSON artifact `tests/architectural/ci_topology_census.json` (regenerated via `--emit-census`)
**Testing**: pytest, targeted surface `tests/architectural/` (charter tiered-testing rule); run via `.venv/bin/python -m pytest … -p no:cacheprovider` headless (`PWHEADLESS=1`); `uv run` rebuilds the editable package (~75s) so the venv python is preferred for iteration
**Target Platform**: CI (Linux primary; census derivation is OS-agnostic newline counting)
**Project Type**: single (library/CLI test-enforcement surface)
**Performance Goals**: freshness check stays a pure source-tree read + already-parsed workflow models; **no new subprocess or pytest-collection step** (NFR-002)
**Constraints**: zero `src/` changes (NFR-003); `mypy --strict` + `ruff` clean, zero new suppressions; cyclomatic complexity ≤ 15; no version numbers in scope; single canonical authority (reuse frozen `_PRE_MISSION_MAPPED_SRC_DIRS` + `_COMPOSITE_ROUTING`, add no second authority)
**Scale/Scope**: 1 production-test module (`_gate_coverage.py`), 1 consumer test module (`test_ci_topology_worklist.py`), 1 census artifact; 32 worklist dirs, `t_loc = 500`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Charter rule | Status | Note |
|--------------|--------|------|
| Single canonical authority (Governing Principles; DIR-044) | PASS | Fix at the one shared derivation; frozen baseline + composite-routing table remain the sole membership/routing authorities; no second freshness authority introduced. |
| ATDD-first (C-011) | PASS | Red-first rank-altering-churn test committed as a separate first commit; reviewer verifies RED on base, GREEN on final. |
| Architectural-gate discipline / non-vacuity (DIR-043) | PASS | Narrowed gate ships with self-mutation teeth tests (drop-dir, phantom-dir, routing-edit, floor-crossing); a gate change cannot self-validate. |
| Campsite cleaning — domain-matched debt (DIR-025) | PASS | Only the census freshness surface is touched; no unrelated debt folded; `arch_blind_groups` de-LOC explicitly deferred (unfalsifiable today). |
| Canonical sources (DIR-044) | PASS | Regenerate the census with the documented `--emit-census` CLI, never a hand-edit. |
| Terminology canon | PASS | No `feature*` terms introduced; domain terms (census, worklist, routing) unchanged. |
| Reviewer ≠ implementer (mission hygiene) | PASS | Review runs as a distinct role/agent. |
| Tiered testing surface (Testing Requirements) | PASS | Targeted `tests/architectural/`; full arch suite at pre-merge. |

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/census-freshness-loc-insensitive-01KWVD6Y/
├── plan.md              # This file
├── research.md          # Phase 0 output (decision + alternatives)
├── data-model.md        # Phase 1 output (census entity: before/after shape)
├── quickstart.md        # Phase 1 output (how to verify the gate + teeth)
├── tracer-*.md          # Mission tracer files (tooling-friction / approach / design-decisions)
└── tasks/               # Phase 2 output (/spec-kitty.tasks) — not created here
```

### Source Code (repository root)

```
tests/architectural/
├── _gate_coverage.py            # EDIT: live_derived_worklist (drop loc, sort by dir),
│                                #       add worklist_routing_index() helper
├── ci_topology_census.json      # REGENERATE via `--emit-census` (worklist loses loc)
└── test_ci_topology_worklist.py # EDIT freshness test → dir-keyed index compare;
                                  # meets-floor test → live loc; ADD red-first + teeth tests
```

**Structure Decision**: Single project. The entire change is confined to three files
under `tests/architectural/`. No `src/` file is touched (NFR-003), so there is no
production runtime surface — the "product" here is the CI enforcement gate itself.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these
> into executable WPs. Given the tight coupling (one derivation, one consumer test,
> one artifact) and the ATDD ordering constraint, these two concerns are expected to
> collapse into **one work package** with test-first commit ordering.

### IC-01 — Derivation-level LOC-drop + live-floor

- **Purpose**: Remove exact `loc` from the shared worklist derivation and re-anchor the floor guarantee to the live tree, so both the freshness test and `--verify-census` stop reddening on LOC churn.
- **Relevant requirements**: FR-001, FR-006, FR-007, C-001, C-002.
- **Affected surfaces**: `_gate_coverage.py` (`live_derived_worklist` emits `{dir, cone_roots, target_group, target_shard}` sorted by `dir`; new pure `worklist_routing_index()` helper; `build_census`/`_emit_census` inherit the change); `ci_topology_census.json` (regenerated).
- **Sequencing/depends-on**: none.
- **Risks**: `test_every_worklist_dir_meets_loc_floor` reads `entry["loc"]` today — it must be re-pointed to live `src_package_loc()` or it breaks. The census MUST be regenerated in the same WP or the freshness test reds on the leftover stored loc.

### IC-02 — Non-vacuous test teeth (ATDD + self-mutation)

- **Purpose**: Prove the narrowed gate still bites on every tamper/membership change and that LOC-only churn (incl. a rank-swap) stays green — the anti-vacuity contract.
- **Relevant requirements**: FR-002, FR-003, FR-004, FR-005, FR-008, NFR-004, C-003, C-004; success criteria SC-001..SC-007.
- **Affected surfaces**: `test_ci_topology_worklist.py` — rewrite `test_census_worklist_matches_live_derivation` to the dir-keyed index compare; add red-first rank-altering-churn test (FR-001+FR-007); add self-mutation teeth tests (drop-dir, phantom-dir, routing-edit, floor-crossing via `t_loc` param).
- **Sequencing/depends-on**: the ATDD red-first test is authored/committed BEFORE IC-01 (charter C-011); the remaining teeth land with IC-01.
- **Risks**: teeth tests must exercise the pre-existing entry point (the `==`/index compare), not a private shadow, or they become vacuous. Floor-crossing is simulated via the `t_loc` parameter with a **dynamic** raised floor `t_high = min(live loc of committed members) + 1` (post-plan gate polish D6 — avoids a magic constant going stale if `task_utils`=505/`saas_client`=552/`events`=574/`paths`=577 grow later) — no source-tree mutation needed. The test asserts the `t_high` derivation differs from the live `t_loc=500` derivation, so it fails loud (not silently green) if the sub-`t_high` band ever empties.

# Implementation Plan: Mission-Type DRG Node + Cross-Grain Integrity Gate (S0 + seam completion)

**Mission:** resolver-seam-completion-01KXK0KG
**Branch:** feat/2651-resolver-seam-completion (planning base = merge target; lands via fork PR to upstream/main)
**Spec:** [spec.md](spec.md) · **Design:** ADR 2026-07-15-1 (S0, G1–G6), 2026-07-14-2 (grain union, Enduring-verification)

## Summary

Model `mission_type` as a first-class DRG node (ADR S0, first step), and land cross-grain
disjointness (FR-013) as a **doctrine-integrity / DRG consistency gate on real content** with a
non-vacuity twin — the ADR-decided home, not a swallowed hot-resolver raise. Wire the live
action-grain into the resolver **lazily** (thunk; retire `_EMPTY_GRAIN`), sourced from the
**overlay-aware** `missions_root`, reconcile the two enduring test-side unions into one source,
and campsite the seam — with activation gating byte-identical.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal — `charter` (`mission_type_profiles`, `pack_context`, `drg`), `doctrine` (`missions/action_index`, `drg/{models,validator,migration/extractor,loader}`, `graph.yaml`), `runtime.next`; pydantic, ruamel.yaml. No new external deps.
**Testing**: pytest (`tests/charter`, `tests/doctrine/drg`, `tests/doctrine`, `tests/integration`, `tests/next`); `PWHEADLESS=1 uv run pytest -n auto --dist loadfile`; ruff + `mypy --strict`; DRG freshness gate (`spec-kitty doctrine regenerate-graph --check`).
**Target Platform**: Linux/macOS CLI (dev + CI).
**Performance Goals**: no eager `load_action_index` I/O on the hot `next`/FSM resolution path; the hot `.action_sequence` shape stays cheap (lazy governance thunk).
**Constraints**: activation gating byte-identical (C-001); single-seam/single-source (C-002); `src/charter` MUST NOT import `specify_cli`, and typing tightening MUST NOT cross the charter→doctrine boundary (C-001 layer rule); parity scaffold disposable (C-003); resolver raise is a lazy fast-fail subordinate to the gate (C-004).
**Scale/Scope**: 4 built-in mission types × 6–8 action indices each; ~1 large module (`mission_type_profiles.py`, 894 LOC) + DRG generator/validator + 2 test-union sites + 1 new integrity gate.

## Charter Check

Charter mode `compact`. Governing principles honored: single canonical authority (the integrity
gate + reconciling the two test unions removes second sources); architectural alignment (enforcement
lands in the DRG/doctrine-integrity layer per both ADRs, not the hot loop); DDD tiered rigour
(charter→doctrine boundary preserved). No conflicts. No new charter activations required.

## Project Structure

### Documentation (this mission)
- `kitty-specs/resolver-seam-completion-01KXK0KG/{spec.md, plan.md, research.md, data-model.md, quickstart.md}`

### Source Code (repository root)
- `src/doctrine/drg/{models.py, validator.py, migration/extractor.py, loader.py}` — DRG node-kind + generator (IC-01/02).
- `src/doctrine/graph.yaml` — generated output (regenerated, IC-02).
- `src/charter/activation/mission_type_profiles.py` — resolver seam: lazy governance thunk, retire `_EMPTY_GRAIN`, aggregation, typing (IC-06/07/10).
- `src/doctrine/missions/action_index.py` — per-action loader (consumed by IC-07).
- `src/charter/` + `src/specify_cli/cli/commands/charter/activate.py` — cascade fix (IC-03).
- New gate: `tests/doctrine/drg/test_cross_grain_integrity.py` (or a doctrine-integrity module) — IC-04/05.
- `tests/doctrine/test_mission_type_governance_isolation.py`, `tests/integration/test_mission_type_resolution_integration.py` — reconcile unions (IC-08).
- `tests/specify_cli/next/test_runtime_bridge_dispatch.py` — NFR-001 threshold fix (IC-09).

## Complexity Tracking

The one genuine complexity is the **eager→lazy governance refactor** (IC-06): governance is built
eagerly at construction today (`:452→:562→from_grains:590`), and the FR-013 raise currently fires
there. Thunking it moves the firing point to first `.governance` access and severs the
governance-failure/`action_sequence` coupling (C-001 robustness win) — justified, not incidental.
Adding a DRG node kind (IC-01) touches generated output + freshness; contained by regenerating and
`--check`.

## Implementation Concern Map

Dependency spine (corrected by the post-plan squad):
**{IC-07, IC-11} → IC-06 → {IC-08, IC-09, IC-10}** (IC-07 and IC-11 are *parallel* prereqs of IC-06; IC-11 gates the `_EMPTY_GRAIN` flip, not the pure adapter; **IC-10 is NOT independent — it mutates the same file and must linearize last**);
**IC-01 → IC-02 → [IC-03 optional]**; **IC-07 → IC-04 → IC-05** (IC-04 MUST reuse IC-07's adapter — building its own union would be the C-002 second-source violation this mission removes); IC-12 spans all.

**Post-plan de-risk (pedro, empirical):** the live type∩action union was run against all 4 shipped types — **zero cross-grain collisions** — so flipping `_EMPTY_GRAIN`→live union does not red-main on shipped content; IC-11's pre-flight finds nothing to fix and folds into IC-04's first green run.

### IC-01 — `mission_type` DRG node-kind registration
Register `mission_type` as a node kind in `src/doctrine/drg/models.py` + `validator.py` (and the kind vocabulary), so a `urn: mission_type:<type>` / `kind: mission_type` node is legal. Scope: kind enum/registry + URN scheme + validation. Tests: validator accepts the kind; rejects malformed.

### IC-02 — DRG generator emits `mission_type` nodes + freshness
Extend `src/doctrine/drg/migration/extractor.py` (the `drg-migration-v1` generator) to emit one `mission_type` node per built-in type (from `missions/mission_types/*.yaml`); regenerate `src/doctrine/graph.yaml`; keep `regenerate-graph --check` green. Tests: generated graph contains 4 mission_type nodes; freshness gate passes. **Depends on IC-01.**

### IC-03 — cascade for `mission-type` (OPTIONAL / recommend defer)
With a DRG node present, `charter activate mission-type <t> --cascade …` resolves a `_source_urn` (retires the `activate.py:88-90,319-321` short-circuit) — **but the node has no outgoing edges** (edges are S0-continuation), so it would "resolve the URN, warn nothing to cascade" — cosmetic. **Recommend deferring to S0-continuation** (when edges land). If kept, it MUST also fix the symmetric `deactivate.py:61-62,92-93` short-circuit and add the `_KIND_MAP` "mission_type" entry (`extractor.py:122-132`). **Depends on IC-02.** SC-001's cascade claim is softened accordingly (below).

### IC-04 — doctrine-integrity gate (load-bearing FR-013 enforcer)
A doctrine-module + integration gate that, for every shipped `(type, action)`, loads the action-grain via **real** `load_action_index` file I/O (asserting each loaded grain **non-empty**, PLAUSIBLE-1), unions with the type-grain from the overlay-aware root, and asserts cross-grain URN disjointness across all types. Non-vacuous, measurable, protects the tree. **Depends on IC-07** (shared union logic — the gate consumes production's union, not a private copy).

### IC-05 — non-vacuity twin
A purpose-authored temp-tree with a deliberate type∩action URN collision, loaded through the same `load_action_index` file seam, that MUST make the gate fail — proving IC-04 is not vacuously green (doctrine ships disjoint by design). **Depends on IC-04.**

### IC-06 — lazy action-grain union in the resolver (retire `_EMPTY_GRAIN`)
Make `governance` a deferred/memoised slot (thunk, mirroring `_expected_artifacts_thunk` `:334-354,474-479`); the action-grain union + `from_grains` FR-013 fast-fail fire on first `.governance` access, never on the hot `.action_sequence` path. **The sole construction-time force is the `:469` `provenance=governance.provenance` read** — reworked by having `_resolve_governance_slot` return `(provenance, text, governance_thunk)` (provenance is already computed independently at `:588` via `repo.get_provenance`). **Keep EAGER:** `governance_text`, `provenance`, `action_sequence`, and the `UnknownMissionTypeError` **registration** guard (`:583-584` — registration-based, must NOT move lazy). **Move to thunk:** only the `from_grains` union (`:590-594`) + FR-013 raise (C-004 lazy fast-fail). Retire `_EMPTY_GRAIN` (`:592,684,690`). Note: `governance` becomes a `compare=False` thunk (like the existing two) — `__eq__` ignores it; determinism asserts still pass. Fix the now-false `:311` docstring. **Depends on IC-07, IC-11.**

### IC-07 — action-grain aggregation (builtin root) + adapter
Enumerate `<type>/actions/*/index.yaml`, `load_action_index` each, union the per-action `ActionIndex` dataclasses into the `Mapping[str, list[str]]` `from_grains` expects (dedup per `_merge_disjoint_grain`). **Root = `MissionTypeProfileRepository._default_built_in_dir()`** (= `src/doctrine/missions`, which the resolver already builds via `_mission_type_profile_repository(repo_root)` at `:746`) — **NOT** the resolver's `repo_root` (which would miss and silently return empty grains). **SCOPE CAP (post-plan, both lenses):** the action-grain is **builtin-root only** in this mission. Full project/org action-index **overlay symmetry** with the type-grain is **NOT mechanically achievable** through `load_action_index`'s single-`Path` signature and there is no project `actions/` override layout today — it is a **tracked follow-up**, not in scope (else it balloons into a second overlay engine). The `data-model.md` symmetry invariant is downgraded accordingly. `ActionIndex→Mapping` is a trivial pure, unit-tested projection (its 7 fields map 1:1 to `_GOVERNANCE_KINDS`). **Foundational.**

### IC-08 — reconcile the two test-side unions to one source
Rewrite `test_mission_type_governance_isolation.py:_resolve_union` and `test_mission_type_resolution_integration.py:_resolve_union_from_mission` to assert against production's unioned bundle (or promote one to *be* IC-04's gate). No second union implementation survives (C-002). **Depends on IC-06.**

### IC-09 — NFR-001 correct threshold + hot-path spy
Replace the mis-targeted `PackContext.from_config` p99 gate (`test_runtime_bridge_dispatch.py:303`) with a `load_action_index` spy asserting it is NOT called on the real `resolve_mission_type_context(...).action_sequence` hot path. Note `:262` already exercises the resolver but **mocks** `action_sequence` (`:267`) — the spy must run against the real resolution, not the mock. **Depends on IC-06.**

### IC-10 — campsite (same-file lane — sequence LAST after IC-06)
`_load_mission_type_profile` (`:769`) has a **live test asserting it must exist** (`test_mission_type_profile_resolution.py:74-98`) → **repoint the test, not a pure delete**. Remove dead `except ImportError → CANONICAL_MISSION_TYPES` (`:388-395`) — coordinate with #2657 which touches the same `existing_mission_types` fallback (distinct: this removes the ImportError branch, #2657 removes all-built-in default semantics; avoid concurrent clobber). Tighten `expected_artifacts` typing at all 3 sites (`:334,:343,:637`) via a `TypedDict`/alias (NOT a pydantic model crossing charter→doctrine). Fix `test_resolved_mission_type_context.py:11-12` docstring; add a `*parity_scaffold*` reappearance-guard. **Depends on IC-06; strictly serial on `mission_type_profiles.py`.**

### IC-11 — pre-flight cross-grain dup scan (fold into IC-04; do NOT ship a second scanner)
A read-only scan of shipped `governance-profile.yaml × actions/*/index.yaml` for existing cross-grain URN dupes before IC-06 flips `_EMPTY_GRAIN`. **Empirically already clean (pedro): zero collisions across all 4 types** — so this is a one-shot gating check, not a fix. **Fold it into IC-04** (the integrity gate's first green run IS the pre-flight) or run as a throwaway spike — do **not** ship a surviving second scanner alongside IC-04 (C-002). **Parallel prereq of IC-06 with IC-07.**

## Proposed WP Grouping (starting shape for /tasks — post-plan squad)

| WP | ICs | Lane | Depends on |
|----|-----|------|------------|
| **WP01** — `mission_type` DRG node + generator | IC-01, IC-02 | DRG | — |
| **WP02** — action-grain aggregation adapter (builtin root) + dup-scan spike | IC-07 (+IC-11) | Resolver | — (foundational) |
| **WP03** — lazy governance thunk + regression pins | IC-06, IC-12 | Resolver | WP02 |
| **WP04** — cross-grain integrity gate + non-vacuity twin | IC-04, IC-05 (absorbs IC-11) | Gate | WP02 |
| **WP05** — test-union reconciliation + NFR spy | IC-08, IC-09 | Test | WP03 |
| **WP06** — resolver campsite | IC-10 | Resolver | WP03 (same-file serial) |
| **WP07** — mission-type cascade (**OPTIONAL / recommend defer**) | IC-03 | DRG | WP01 |

**Parallelism:** WP01 (DRG lane) ∥ WP02 (resolver lane) — disjoint files. Critical path: **WP02 → WP03 → WP06** (all serial on `mission_type_profiles.py`). WP04 + WP05 are parallel tails after their deps. **File-linearization:** `mission_type_profiles.py` is single-lane serial `IC-07 → IC-06 → IC-10`.

## SC-001 softening (post-plan)

If IC-03/WP07 is deferred, SC-001's cascade clause reads: "`mission_type` has a DRG node per built-in type; freshness gate green" — full cascade **edge traversal** is S0-continuation (a `mission_type` node with no outgoing edges resolves its URN but has nothing to cascade).

### IC-12 — C-001 activation-gating byte-identical regression pins (spans all)
Pin `existing_mission_types` / `activated_mission_types` / action-sequence outputs unchanged; assert the thunk severs the eager-collision→`action_sequence`-abort coupling. Full charter + `next` suites green.

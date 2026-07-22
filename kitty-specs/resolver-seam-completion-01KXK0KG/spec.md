# Feature Specification: Mission-Type DRG Node + Cross-Grain Integrity Gate (S0 + seam completion)

**Mission:** resolver-seam-completion-01KXK0KG
**Type:** software-dev
**Issues:** #2651 (resolver-seam completion) + first step of ADR **S0** (mission_type as a first-class DRG node)
**Design authority:** [ADR 2026-07-15-1](../../docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md) (Decision 2, S0; G1–G6), [ADR 2026-07-14-2](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md) (grain union; Enduring-verification = doctrine-integrity test)
**Adjudication:** the cross-grain-disjointness enforcement home (doctrine-integrity gate, not a swallowed hot-resolver raise) and the lazy-union framing are the outcome of an ADR-anchored second-opinion adjudication (architect + doctrine lenses) reconciling a post-spec review against the merged ADRs above; the binding decisions are those ADRs. Forward-note: **#2656** (mission-instance addendum) builds on this reworked `ResolvedGovernance.from_grains` and is correctly `blocked_by` #2651.

## Overview

Two ADR strands converge here. (1) #883 unioned governance at two grains but **deferred wiring the live action-grain** (`action_grain=_EMPTY_GRAIN`, `mission_type_profiles.py:592`), and its cross-grain disjointness invariant is only exercised on synthetic data. (2) The coherence ADR's **S0** makes `mission_type` a **first-class DRG node** — and daphne's adjudication established that under S0 the *doctrinally-correct home* for cross-grain disjointness is a **DRG consistency gate over the unioned (type ⊕ action) governance**, not a hot-resolver raise (which is verifiably swallowed on every runtime path, and whose eager form would regress NFR-001).

This mission therefore **models `mission_type` as a DRG node, makes cross-grain disjointness a DRG/doctrine-integrity gate on real content, wires the live action-grain lazily (retiring `_EMPTY_GRAIN`), and campsites the seam** — a coherent bundle whose enforcement lands in the graph, not the hot path. It is a precursor that de-risks S3 (the runtime consume-path gating).

## Intent Summary (confirmed)

- **Primary actor:** the doctrine/charter mission-type authority (DRG) and the maintainers/pack-authors who rely on cross-grain integrity.
- **Trigger:** the ADR is merged; the operator bundled #2651's integrity gate with S0's DRG-node modelling.
- **Desired outcome:** `mission_type` is a first-class DRG node; cross-grain disjointness is enforced as a **doctrine-integrity/DRG consistency gate** on real (type × action) content with a non-vacuity twin; the resolver carries the live action-grain **lazily**; `_EMPTY_GRAIN` retired; the two test-side union implementations reconciled; seam campsite done.
- **Load-bearing invariant:** activation gating (`existing_mission_types` / `activated_mission_types` / action-sequence) is **byte-identical**; the cross-grain-disjointness enforcement is load-bearing in the gate, and the resolver raise is a bounded, lazily-evaluated fast-fail — never eager.
- **Boundary:** this mission does **not** gate the runtime template/consume path (that is S3); it does not model `step_contract`/`gate`/`asset` as DRG nodes (S0 continuation).

## User Scenarios & Testing

1. **`mission_type` is a graph citizen.** After regeneration, `graph.yaml` contains a `mission_type` node per built-in type; `spec-kitty doctrine regenerate-graph --check` is fresh; the freshness gate is green.
2. **Cross-grain integrity is enforced on real content.** The doctrine-integrity gate loads every `(type, action)` via real `load_action_index` file I/O, unions with the type-grain, and asserts disjointness across the whole shipped tree — with a non-vacuity twin (a purpose-authored temp-tree collision, loaded through the same file seam, that MUST make the gate fail). "No shipped collision exists today" is expected — the gate is forward-looking protection for future org/pack-authored grains.
3. *(Enabled, not delivered here)* The `mission_type` DRG node makes cascade **resolvable** for a mission type; full `--cascade` edge traversal is S0-continuation (a node with no outgoing edges resolves its URN but has nothing to cascade).
4. **Hot path stays cheap.** The runtime `next`/FSM resolution path triggers **no** `load_action_index` I/O; the resolver's action-grain union materializes lazily (thunk), and the cross-grain-disjointness fast-fail fires only on first `.governance` access, never on the hot `.action_sequence` path.
5. **One union authority.** The two enduring test-side unions (`_resolve_union`, `_resolve_union_from_mission`) assert against production's single unioned source (or one is promoted to *be* the integrity gate) — no second implementation of the reduction survives.

## Domain Language

- **DRG node / `graph.yaml`** — the Doctrine Reference Graph; generated, freshness-gated. `mission_type` currently has **0 nodes**.
- **type-grain / action-grain** — `governance-profile.yaml selected_*` vs the union of `actions/*/index.yaml` scope edges (`load_action_index`).
- **doctrine-integrity gate** — the ADR-decided (2026-07-14-2 Enduring) home for cross-grain-disjointness: a doctrine-module + integration test / DRG consistency check over the unioned grain, with a non-vacuity twin.
- **overlay-aware `missions_root`** — the builtin→org→project resolution the type-grain already uses (`MissionTypeProfileRepository`); the action-grain must share it.
- **transitional parity scaffold** — disposable swap-proof; **deleted before landing** (never retained; a reappearance guard enforces it).

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `mission_type` becomes a first-class DRG node: the graph generator emits a `mission_type` node per built-in type into `graph.yaml`, and `regenerate-graph --check` / the freshness gate stay green. | Planned |
| FR-002 | Cross-grain disjointness is enforced by a **doctrine-integrity gate** that unions each `(type, action)` — loaded through real `load_action_index` file I/O — with the type-grain and asserts disjointness across all shipped types, asserting each loaded grain **non-empty**. | Planned |
| FR-003 | The gate carries a **non-vacuity twin**: a purpose-authored temp-tree with a deliberate type∩action URN collision, loaded through the same file seam, that MUST make the gate fail (proving it is not vacuously green). | Planned |
| FR-004 | The resolver unions the **live** action-grain into `ResolvedGovernance` **lazily** (thunk, mirroring `expected_artifacts`/`step_contracts`), retiring `action_grain=_EMPTY_GRAIN` (`:592`); the cross-grain-disjointness `CrossGrainDoubleDeclarationError` fast-fail fires on first `.governance` access, never on the hot `.action_sequence` path. | Planned |
| FR-005 | The action-grain is aggregated correctly: enumerate `<type>/actions/*/index.yaml`, load each, union `ActionIndex` → the `Mapping[str, list[str]]` shape `from_grains` expects, sourced from the **overlay-aware `missions_root`** the type-grain uses (not the resolver's `repo_root`). | Planned |
| FR-006 | The two enduring test-side unions (`tests/doctrine/test_mission_type_governance_isolation.py` `_resolve_union`, `tests/integration/test_mission_type_resolution_integration.py` `_resolve_union_from_mission`) are reconciled to a single source: rewritten to assert against production's unioned bundle, or one promoted to be the integrity gate. No second union implementation survives. | Planned |
| FR-007 | Campsite: delete the dead `_load_mission_type_profile` wrapper (`:769`) + **repoint** its test; remove the dead `except ImportError → CANONICAL_MISSION_TYPES` fallback (`:388-395`); tighten `expected_artifacts` typing at all **three** sites (`:334`, `:343`, `:637`) via a `TypedDict`/alias (not a pydantic model that crosses the charter→doctrine boundary); fix the stale docstrings (`:311` "eagerly on hot path" becomes false; `tests/charter/test_resolved_mission_type_context.py:11-12`); add a `*parity_scaffold*` reappearance-guard. | Planned |

## Non-Functional Requirements

| ID | Requirement | Threshold |
|----|-------------|-----------|
| NFR-001 | The action-grain union adds no eager DRG-load I/O to the hot `next`/FSM resolution path. | A gate measures `resolve_mission_type_context(..., mission_type=X).action_sequence` (the hot shape) **and** a spy asserts `load_action_index` is **not** called on that path. (The pre-existing `PackContext.from_config` p99 gate is *not* the correct threshold — it never invokes the resolver.) |
| NFR-002 | Every new branch/helper/node-kind has a direct test in the same PR. | `ruff` and `mypy --strict` pass with zero new issues; the DRG freshness gate is green. |

## Constraints

| ID | Constraint |
|----|-----------|
| C-001 | **Activation gating byte-identical** — `existing_mission_types` / `activated_mission_types` / the action-sequence gate are unchanged and regression-pinned; thunking governance also severs the eager-collision-aborts-`action_sequence` coupling. |
| C-002 | No second resolution path or second union authority is introduced (single-seam, single-source — the reason FR-006 reconciles the test unions). |
| C-003 | The transitional parity scaffold is added at start and **deleted before landing** — never retained; the reappearance guard enforces it. Enduring verification is behavioural (doctrine-module + integration + DRG-freshness). |
| C-004 | The resolver-embedded cross-grain-disjointness raise is a **bounded lazy fast-fail**, subordinate to the doctrine-integrity gate as the load-bearing enforcer; it is never the sole enforcement and never eager. |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | `graph.yaml` has a `mission_type` node per built-in type; freshness gate green. (Cascade *edge traversal* is S0-continuation, out of scope.) |
| SC-002 | The doctrine-integrity gate fails on a purpose-authored collision fixture and passes on the (disjoint) shipped tree — provably non-vacuous. |
| SC-003 | The hot `.action_sequence` path triggers zero `load_action_index` calls (spy-verified); the full charter + `next` suites pass with byte-identical activation-gating outputs. |
| SC-004 | No second implementation of the type⊕action union remains in the tree; no `parity_scaffold` artifact survives. |

## Key Entities

- `mission_type` DRG node (new, in `graph.yaml`).
- `ResolvedGovernance` / `ResolvedMissionType` — `action_grain` slot filled lazily (thunk) from `_EMPTY_GRAIN`.
- `load_action_index` (`doctrine/missions/action_index.py:26`) — per-action loader, aggregated + overlay-sourced.
- The doctrine-integrity gate — the load-bearing cross-grain-disjointness enforcer.

## Coverage

Closes **#2651** (resolver-seam completion, re-scoped per adjudication). Delivers the **first step of ADR S0** (`mission_type` as a DRG node) and the DRG-home for cross-grain integrity. Unblocks **#2658**/#2659 under epic **#2652**; relates ADR **#2655**, and the S0 continuation (step_contract/gate/asset nodes).

## Assumptions

- The DRG generator can be extended to emit a `mission_type` node kind without a schema break; if it needs a new node-kind registration, that is in-scope (grounded in `/plan`).
- Sourcing the action-grain from the overlay-aware root is the in-scope minimum; full project-level action-index **override layering** may be a bounded follow-up **only if** the union already reads the overlay-merged root.
- A pre-flight scan of shipped `governance-profile.yaml` × `actions/*/index.yaml` for existing cross-grain URN duplicates runs before retiring `_EMPTY_GRAIN` (guards against red-main; seeds the gate's assertion).

## Out of Scope (later slices)

- Gating the runtime template/consume path through activation so deactivation makes a type unrunnable (**S3** / #2659).
- Modelling `step_contract` / `gate` / `asset` as DRG nodes (S0 continuation).
- Mission-type **cascade edge traversal** and the `deactivate.py` symmetry (needs the `mission_type` node's outgoing edges, which are S0 continuation — cosmetic without them).
- Wiring `template_set` file-selection through the artefact (#2658 / S4).
- The mission-instance governance addendum (#2656) and provisioned default charter (#2657).

# Tracer — Design Decisions (M3)

## Locked at finalize (evidence in spec.md "Respec vs pre-M0 baseline")
- **Fork (d) → per-type DATA source, not revive-v1.** `mission_v1` guard cluster verified dead in prod; live runtime has its own `artifact_exists` (engine.py:1445). Reviving re-adds a parallel dead engine.
- **Fork (e) → NAME from step-contract short-key vocab; SETS from `expected-artifacts.yaml`.** `step.yaml` does not exist; the two vocabularies do not join.
- **Fork (f) → pin-and-defer third artifact kind.** No WP adds a 3rd built-in kind; pin the named raise (AC-12).
- **KDD-3 → consume landed `canonical_mission_type_key`; no parallel reader (NFR-002 = preserve, not build).** M3↔M5 interlock already satisfied on main.
- **KDD-8 → #3407 is route-not-rebuild.** `_GUARD_TABLES["plan"]` already exists; fix is the `runtime_bridge.py:797` family hardcode only.
- **C-001 → relocate `ExpectedArtifactManifest` to `src/doctrine/missions/`; charter slot stays `Mapping[str, Any]`.**

## Resolved at plan (ADR docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md)
- **Fork (e) RE-LOCKED → `expected-artifacts.yaml` `path_pattern`** single filename authority (POST-SPEC squad §S2 source-adjudication; `step.yaml` exists but carries template ref only; MissionStepTemplateRef covers 2/10).
- **FR-001 predicate = `bundle.merged.node_urns()` membership** (not empty-grain; declared-but-starved → bootstrap+empty is legitimate — §S1).
- **NFR-001 single-load proof** in plan.md §2 + NEW load-count red-first test (existing import-time test can't witness a runtime double-load).
- **WP cut lines** (plan.md §3): WP01 ADR foundation; WP02 A; WP03 B; WP04 C (L, ordered subtasks); WP05 D. A/B/C/D independent.
- **Per-symbol ownership vs M4**: WP04 touches repository.py near `get_expected_artifacts:362`; M4 owns `get_action_index:316`. Different symbol.
- **FR-015 carrier** = direct action URN, not mission_type edge (§S5).

## Still deferred to WP01 implementation (verify empirically)
- `load_validated_graph` memoization confirmation (WP02).
- Exhaustive per-type `path_pattern` coverage audit for all 10 tags (WP04).
- Interview validation mechanism (static label-union vs loaded nodes) + custom-family gate (`_GUARD_TABLES` registration vs strict-raise).

## (append as decisions are made)

# Implementation Plan: Project-Tier DRG Node Emission

**Branch**: `spec/project-tier-drg-node-emission` | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/project-tier-drg-node-emission-01M0DM94/spec.md`

## Summary

Emit hand-authored **project-tier `agent_profile`** artefacts as DRG nodes so the charter cascade can reach them. Two halves ship together: (1) **kind-admission** — re-key `charter/synthesizer/project_drg.py::_KIND_TO_NODE_KIND` from `dict[str, NodeKind]` to `dict[ArtifactKind, NodeKind]` and admit `AGENT_PROFILE`, reconciling with the M1 totality gate; (2) **artefact-driven emission** — a filesystem-walk emitter that enumerates `.kittify/doctrine/agent_profiles/*.agent.yaml` and lands `agent_profile:<id>` nodes in the project overlay `graph.yaml` (the only project graph the cascade reads). The synthesizer today is answer-driven, so the map extension alone reproduces the defect — the walk is required.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic v2 (`doctrine.drg.models`), ruamel.yaml (graph serialisation); internal `doctrine.drg`, `doctrine.artifact_kinds`, `charter.synthesizer`
**Storage**: YAML on disk — project overlay graph at `.kittify/doctrine/graph.yaml`; project profiles at `.kittify/doctrine/agent_profiles/*.agent.yaml`
**Testing**: pytest (`tests/charter/synthesizer/`, `tests/doctrine/drg/`, `tests/charter/`), mypy --strict, ruff
**Target Platform**: Linux/macOS/Windows CLI (cross-platform)
**Project Type**: single (CLI library)
**Performance Goals**: charter synthesize/context CLI operations stay < 2 s for a typical project (≤ 50 authored project profiles); the profile filesystem walk is O(files) with a single recursive glob
**Constraints**: `charter` must not import `specify_cli` (C-001); node-kind conversion derives from the canonical `ArtifactKind`↔`NodeKind` superset (C-002); golden movement bounded to `agent_profile` emission, no cascade relation-set change and no org read-path change (C-003); red-first ATDD (C-004); agent_profile only, asset/procedure out (C-005)
**Scale/Scope**: one module of new emission logic + a map/gate reconciliation; ~2 source surfaces, ~2 test surfaces

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority / derive-don't-restate** (`DIRECTIVE_044`): node-kind conversion derives from the `NodeKind ⊇ ArtifactKind` superset (guarded by `test_nodekind_artifactkind.py`); the canonical total authority is `doctrine/drg/migration/extractor.py::_KIND_MAP`. The re-keyed `_KIND_TO_NODE_KIND` is an explicit **allowlist** (its keys = the emittable project-tier kinds), kept as a gate-visible literal — not a hidden second kind enumeration. **PASS (by design).**
- **Architectural gate discipline** (`DIRECTIVE_043`): the M1 totality gate (`tests/doctrine/drg/test_kind_mapping_totality.py`) is the arch gate. Re-keying moves the map from the string-keyed scan to the enum-keyed scan; we reconcile **non-vacuously** — add to `_EXEMPT_GET_PARTIALS` with a written rationale (the `.get`-read partial case) **and** remove the now-stale `_STRING_KEYED_COVERAGE_WITNESS` + its test in the same change. No gate weakening. **PASS.**
- **ATDD-first / red-first** (`C-011`, `DIRECTIVE_041`): each WP lands a failing-first test before implementation — kind-admission (`_node_kind_for("agent_profile")`) and cascade-visibility (hand-authored profile → node in `graph.yaml`). **PASS.**
- **Architectural alignment / layering** (`DIRECTIVE_001`, C-001): `charter` imports **down** into `doctrine` only; reusable graph-walk logic lands under `src/doctrine/drg/` per `project_drg.py`'s KD-1 rule, with `project_drg.py` staying a thin composer. **PASS.**
- **Terminology canon**: no `feature*` for the mission object; overloaded terms (`cascade`, `routing`, `primary`/`merge`) are named by sense in the spec's Domain Language. **PASS.**
- **Tiered rigour**: this is core doctrine-resolution logic → highest rigour (focused unit tests on the emitter + gate, integration test on the live synthesize→cascade path). **PASS.**
- **Bounded golden re-ledger** (C-003): emitting new project nodes may move golden fixtures; every movement is attributable to `agent_profile` emission and explained. M2 (org bridge) and M5 (cascade relation set) surfaces are untouched. **PASS (verified at review).**

No violations requiring Complexity Tracking.

## Design Approach

### Seams (traced against current `main` + M1)

| Concern | Location | Role in M6 |
|---------|----------|------------|
| Kind→NodeKind map (answer-driven allowlist) | `src/charter/synthesizer/project_drg.py:45` `_KIND_TO_NODE_KIND`; `:52` `_node_kind_for` | Re-key to `ArtifactKind`; admit `AGENT_PROFILE` |
| Answer-driven emitter | `src/charter/synthesizer/project_drg.py:116` `emit_project_layer` | Unchanged emit contract; additive-only guards reused by the walk path |
| Canonical total authority | `src/doctrine/drg/migration/extractor.py:240` `_KIND_MAP`; superset invariant `tests/doctrine/drg/test_nodekind_artifactkind.py` | Derivation source for node-kind |
| Built-in walk pattern | `src/doctrine/drg/migration/extractor.py:1041` `_discover_built_in_nodes_in_dir` | Pattern to mirror (glob `*.agent.yaml` recursive, id-key `profile-id`, `NodeKind.AGENT_PROFILE`) |
| Project profile reader | `src/doctrine/agent_profiles/repository.py:404` (project layer, `overlay_scan_is_recursive`) | Single-authority reader for "what project profiles exist" |
| Emit/persist seam | `src/charter/synthesizer/orchestrator.py:283-297` `_validation_callback`; `src/specify_cli/cli/commands/charter/_synthesis.py:245-252` | Where the walk-emitted nodes merge into the overlay before `persist` |
| Persist → promote → live graph | `project_drg.py:375` `persist` → `src/charter/synthesizer/write_pipeline.py:585` `_promote_graph_overlay` → `.kittify/doctrine/graph.yaml` | Path that carries nodes to the cascade-read file |
| Cascade project-graph read | `src/charter/_drg_helpers.py:163-170` `load_validated_graph`; `src/doctrine/drg/loader.py:33/81` `has_graph_files`/`load_graph_or_dir` | Reads `.kittify/doctrine/graph.yaml` — the reachability target |
| Totality gate | `tests/doctrine/drg/test_kind_mapping_totality.py` (`_EXEMPT_GET_PARTIALS`, `_STRING_KEYED_COVERAGE_WITNESS`) | Reconcile enum-key migration |

### Decisions

1. **Node source = filesystem-walk emitter** (seed decision 1). Enumerate authored project-tier profiles; do **not** rely on synthesis answers. Prefer reusing the existing project-tier profile reader (`AgentProfileRepository` project layer) as the single authority for "which project profiles exist"; if its public surface does not cleanly expose the raw project-tier ids, fall back to a recursive `*.agent.yaml` glob mirroring the built-in extractor convention. **Reusable graph-walk logic lands under `src/doctrine/drg/`** (KD-1); `project_drg.py` composes it.
2. **Map stays a partial allowlist, enum-keyed literal** (seed decision + M1 handshake). Keys = the emittable project-tier kinds (`DIRECTIVE`, `TACTIC`, `STYLEGUIDE`, `AGENT_PROFILE`). Values written explicitly (`NodeKind.DIRECTIVE`, …) so the enum-keyed gate scan sees a literal. `_node_kind_for(kind: str)` converts str→`ArtifactKind` (catching `ValueError`→`None`) then reads via `.get` — preserving the "skip unsupported kind" semantics and the `.get`-partial exemption contract. Making it total is rejected: it would falsely claim non-emittable kinds (`asset`/`template`/`procedure`/…) are emittable.
3. **Edges are out of scope** (seed decision 2 + C-003). M6 emits the **node** only. Authoring inbound edges for orphaned artefacts is M5. The emitted project profile node must be **valid without inbound edges** — verified red-first against `assert_valid` and the orphan lints.
4. **Asset deferred** (seed decision 3). No `asset:*` node emitted; asset stays reference-only behind #3037.

### Key risk to verify red-first

An **edgeless** project `agent_profile` node must pass `assert_valid(merged)` and the orphan/exhaustiveness lints (`tests/doctrine/drg/test_kind_cascade_exhaustive.py`, `test_tiered_standards_non_orphan.py`). If an orphan node trips a hard invariant, scope-adjacent edge handling would be forced — the plan's first implementation step probes this so the WP slicing stays honest.

## Project Structure

### Documentation (this mission)

```
kitty-specs/project-tier-drg-node-emission-01M0DM94/
├── plan.md              # This file
├── research.md          # Phase 0 — seam trace + risk probe
├── data-model.md        # Phase 1 — node/edge shape, emittable-kind set
├── quickstart.md        # Phase 1 — how to author + verify a project profile node
├── contracts/           # Phase 1 — emitter contract, gate-reconciliation contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── charter/synthesizer/
│   ├── project_drg.py          # re-key _KIND_TO_NODE_KIND → ArtifactKind; compose the walk emitter
│   └── orchestrator.py         # wire walk-emitted nodes into the _validation_callback seam
├── specify_cli/cli/commands/charter/
│   └── _synthesis.py           # CLI-tier _validation_callback: same wiring
└── doctrine/drg/
    └── (new) project_scan.py   # reusable project-tier profile → DRGNode walk (KD-1 home) [name TBD in tasks]

tests/
├── charter/synthesizer/
│   └── test_project_drg.py     # emitter unit coverage (walk, additive-only, dedupe)
├── charter/
│   └── test_project_profile_cascade_reach.py  # ATDD: hand-authored profile → node in graph.yaml, cascade-reachable (new)
└── doctrine/drg/
    └── test_kind_mapping_totality.py  # gate reconciliation (exemption + witness removal)
```

**Structure Decision**: single-project CLI library. New reusable walk logic under `src/doctrine/drg/` (lowest layer, importable by charter); `charter.synthesizer.project_drg` composes it; the CLI/orchestrator seams wire it into the existing persist→promote chain. Exact new-module name finalised in `/spec-kitty.tasks`.

## Parallel Work Analysis

### Dependency Graph

```
WP01 (kind-admission + gate reconciliation) ──► WP02 (filesystem-walk emitter + wiring + cascade reachability)
```

Sequential: both WPs touch `src/charter/synthesizer/project_drg.py`, so ownership overlap forces order (no-overlap is the real guard). WP01 establishes the admitted kind + green totality gate; WP02 builds the emitter that lands the admitted `agent_profile` node and proves cascade reach.

### Work Distribution

- **WP01 — Kind-admission + totality-gate reconciliation.** Re-key `_KIND_TO_NODE_KIND` to `dict[ArtifactKind, NodeKind]`, add `AGENT_PROFILE`; update `_node_kind_for` (str→ArtifactKind→`.get`). Reconcile `test_kind_mapping_totality.py`: add the map to `_EXEMPT_GET_PARTIALS` with rationale; remove `_STRING_KEYED_COVERAGE_WITNESS` + `test_string_keyed_kind_map_coverage_sees_previously_hidden_maps`. Red-first: `_node_kind_for("agent_profile") is NodeKind.AGENT_PROFILE`. Surfaces: `tests/doctrine/drg/test_kind_mapping_totality.py`, `tests/charter/synthesizer/test_project_drg.py`.
- **WP02 — Artefact-driven emitter + wiring + reachability.** New reusable walk under `src/doctrine/drg/` producing `agent_profile:<id>` nodes (additive-only against built-in, dedupe, fail-loud on malformed); compose it in `project_drg.py`; wire into the `_validation_callback` seam in `orchestrator.py` + `_synthesis.py` so nodes flow through `persist`→`_promote_graph_overlay` into `.kittify/doctrine/graph.yaml`. Red-first (C-004): hand-authored project profile → node present in project graph + cascade-reachable + valid without inbound edges. Surfaces: `tests/charter/synthesizer/test_project_drg.py`, new `tests/charter/test_project_profile_cascade_reach.py`, `tests/charter/test_merged_graph_on_live_path.py`.

### Coordination Points

- **Sync**: WP02 starts after WP01 merges (shared `project_drg.py`).
- **Integration test**: the live synthesize→promote→`load_validated_graph`→cascade path (WP02's reachability test) is the end-to-end proof; golden-fixture deltas reviewed for `agent_profile`-only attribution.

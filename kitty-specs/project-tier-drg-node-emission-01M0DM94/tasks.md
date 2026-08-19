# Tasks — Project-Tier DRG Node Emission

**Mission**: `project-tier-drg-node-emission-01M0DM94` (M6 of the charter-resolution program) · Closes #3038 (agent_profile half); asset half deferred behind #3037
**Branch strategy**: planning base `spec/project-tier-drg-node-emission` → merge target `spec/project-tier-drg-node-emission` (one PR to `main` at completion). Execution worktrees are allocated per computed lane from `lanes.json`.

Subtask rows below are **reference rows** (event-sourced completion via `spec-kitty agent tasks mark-status`), not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red (ATDD/C-004): hand-authored project `agent_profile` → assert `agent_profile:<id>` node in `.kittify/doctrine/graph.yaml` + cascade-reachable (fails pre-fix: node absent) | WP01 | |
| T002 | Red: `_node_kind_for("agent_profile")` returns `None` on base (kind not admitted) | WP01 | [P] |
| T003 | Risk probe: prove an **edgeless** `agent_profile` project node passes `assert_valid` + orphan/exhaustiveness lints (escalate if it trips a hard invariant) | WP01 | |
| T004 | Re-key `_KIND_TO_NODE_KIND` → `dict[ArtifactKind, NodeKind]`, add `AGENT_PROFILE`; update `_node_kind_for` (str→`ArtifactKind`→`.get`) | WP01 | |
| T005 | Totality-gate reconciliation: add map to `_EXEMPT_GET_PARTIALS` w/ rationale; remove `_STRING_KEYED_COVERAGE_WITNESS` + `test_string_keyed_kind_map_coverage_sees_previously_hidden_maps` | WP01 | |
| T006 | New reusable walk under `src/doctrine/drg/` → project `agent_profile:<id>` nodes (recursive `*.agent.yaml`, id-key `profile-id`, additive-only, dedupe, fail-loud) | WP01 | |
| T007 | Compose the walk in `project_drg.py`; wire into the `_validation_callback` seam (`orchestrator.py`, `_synthesis.py`) so nodes reach `graph.yaml` via `persist`→`_promote_graph_overlay` | WP01 | |
| T008 | Green: T001/T002 pass; malformed profile fails loud (NFR-002); `_node_kind_for("asset") is None` (asset boundary, INV-4) | WP01 | |
| T009 | Golden-count attribution (C-003): any DRG golden delta is `agent_profile`-emission-only; cascade relation-set (M5) + org read-path bridge (M2) byte-unchanged; record result | WP01 | |

---

## Work Packages

### WP01 — Emit project-tier agent_profile as a cascade-reachable DRG node
- **Goal**: A hand-authored project-tier `agent_profile` becomes an `agent_profile:<id>` DRG node in the project overlay `graph.yaml` the cascade reads — closing the kind-admission gap for the agent_profile half of #3038. Ships both halves together: kind-admission (enum-keyed map + gate reconciliation) and artefact-driven filesystem-walk emission.
- **Priority**: P1. **MVP** (the whole mission).
- **Independent test**: author `.kittify/doctrine/agent_profiles/reviewer-rhonda.agent.yaml` (no synthesis answer); after synthesize, `graph.yaml` contains `agent_profile:reviewer-rhonda` and `load_validated_graph(...).get_node(...)` is non-None. RED on the pre-fix base (node absent), GREEN after.
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, NFR-001, NFR-002, NFR-003, C-001, C-002, C-003, C-004, C-005.
- **Subtasks**: T001, T002, T003, T004, T005, T006, T007, T008, T009
- **Dependencies**: none (M1 already landed on the base).
- **Risks**: edgeless node vs orphan lints (T003 probes red-first); golden ripple beyond agent_profile (T009 STOPs and escalates — belongs to M2/M5, not M6); `charter` importing `specify_cli` (forbidden — reusable walk lands in `src/doctrine/drg/`, C-001).
- **Est. prompt size**: ~520 lines.

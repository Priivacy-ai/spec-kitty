---
work_package_id: WP01
title: Emit project-tier agent_profile as a cascade-reachable DRG node
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
- C-005
planning_base_branch: spec/project-tier-drg-node-emission
merge_target_branch: spec/project-tier-drg-node-emission
branch_strategy: Planning artifacts for this mission were generated on spec/project-tier-drg-node-emission. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into spec/project-tier-drg-node-emission unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
history:
- Created by /spec-kitty.tasks (M6 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/synthesizer/
create_intent:
- src/doctrine/drg/project_scan.py
- tests/charter/test_project_profile_cascade_reach.py
execution_mode: code_change
owned_files:
- src/charter/synthesizer/project_drg.py
- src/charter/synthesizer/orchestrator.py
- src/specify_cli/cli/commands/charter/_synthesis.py
- src/doctrine/drg/project_scan.py
- tests/doctrine/drg/test_kind_mapping_totality.py
- tests/charter/synthesizer/test_project_drg.py
- tests/charter/test_project_profile_cascade_reach.py
role: implementer
tags: []
tracker_refs:
- '3038'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and
tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved
initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Make a **hand-authored project-tier `agent_profile`** become a DRG node the charter **cascade** can reach. Two halves, shipped together (the map extension alone reproduces the defect because the synthesizer is answer-driven):

1. **Kind-admission** — re-key `charter/synthesizer/project_drg.py::_KIND_TO_NODE_KIND` to `dict[ArtifactKind, NodeKind]`, admit `AGENT_PROFILE`, and reconcile the M1 totality gate.
2. **Artefact-driven emission** — a filesystem-walk emitter that lands `agent_profile:<id>` nodes in `.kittify/doctrine/graph.yaml`.

- **SC-001 (FR-001/002/003)**: a hand-authored `.kittify/doctrine/agent_profiles/<name>.agent.yaml` (no synthesis answer) yields exactly one `agent_profile:<id>` node in the project graph the cascade reads — measured 0→1 vs base.
- **SC-002 (FR-004/NFR-003, C-002)**: `_KIND_TO_NODE_KIND` is `ArtifactKind`-keyed, total-or-exempt under the totality gate; the string-keyed coverage witness for it is removed; full `test_kind_mapping_totality.py` green.
- **SC-003 (FR-006/C-005, INV-4)**: no `asset:*` project node emitted; asset stays reference-only.
- **SC-004 (C-003)**: every golden DRG delta is `agent_profile`-emission-attributable and explained; M2/M5 surfaces byte-unchanged.
- **SC-005 (FR-007/NFR-002)**: a malformed project `agent_profile` file fails loud (names the file) at emission — zero silent skips.

## Context & Constraints

Read `contracts/emitter-and-gate.md`, `data-model.md`, `research.md`, and the current code at the seams in `plan.md`'s design table. Key facts:

- **Canonical node-kind** derives from `NodeKind ⊇ ArtifactKind` (guarded by `tests/doctrine/drg/test_nodekind_artifactkind.py`); `NodeKind("agent_profile")` resolves directly. Canonical total authority: `src/doctrine/drg/migration/extractor.py:240 _KIND_MAP`.
- **Built-in walk pattern to mirror**: `src/doctrine/drg/migration/extractor.py:1041 _discover_built_in_nodes_in_dir` (glob `*.agent.yaml` **recursive**, id-key `profile-id`, `urn = artifact_to_urn(kind, id)`, `NodeKind.AGENT_PROFILE`).
- **Project reader (reuse candidate)**: `src/doctrine/agent_profiles/repository.py:404` project layer (`overlay_scan_is_recursive(ArtifactKind.AGENT_PROFILE)`, id-key `profile-id`).
- **Emit/persist/promote/read chain**: `project_drg.py:116 emit_project_layer` / `:375 persist` → hook seam `orchestrator.py:283-297 _validation_callback` + `_synthesis.py:245-252` → `write_pipeline.py:585 _promote_graph_overlay` → `.kittify/doctrine/graph.yaml` → cascade read `_drg_helpers.py:163-170 load_validated_graph`.
- **Totality gate**: `tests/doctrine/drg/test_kind_mapping_totality.py` — enum-keyed guard `test_kind_keyed_dicts_are_total_or_exempt` (total-or-`_EXEMPT_GET_PARTIALS`); the map is currently the string-keyed `_STRING_KEYED_COVERAGE_WITNESS`.

**Constraints**: `charter` must **not** import `specify_cli` (C-001) — the reusable walk lands under `src/doctrine/drg/`, `project_drg.py` composes it (KD-1). Zero suppressions / zero `ruff`/`mypy --strict` issues (NFR-003). No cascade relation-set change (M5), no org read-path bridge change (M2) (C-003). Edge authoring is out of scope — emit the **node** only; it must be valid without inbound edges.

## Branch Strategy
Planning base **`spec/project-tier-drg-node-emission`**; merge target **`spec/project-tier-drg-node-emission`**. Worktree per computed lane from `lanes.json`. One PR to `main` at mission completion.

## Subtasks & Detailed Guidance

### T001 — Red (ATDD/C-004): cascade-reachability of a hand-authored project profile
Write `tests/charter/test_project_profile_cascade_reach.py`. In a temp project root: author `.kittify/doctrine/agent_profiles/reviewer-rhonda.agent.yaml` with `profile-id: reviewer-rhonda` (no synthesis interview answer). Drive the project-overlay emission path (call `emit_project_layer` + the new walk, or the synthesize orchestration seam) and assert the resulting project `graph.yaml` / merged graph contains node `agent_profile:reviewer-rhonda` of kind `agent_profile`, and `load_validated_graph(project_root).get_node("agent_profile:reviewer-rhonda")` is non-None. **Must be RED on the pre-fix tree** (node absent). Confirm red on the merge-base before implementing.

### T002 — Red [P]: admission gap
In `tests/charter/synthesizer/test_project_drg.py`, assert `_node_kind_for("agent_profile") is NodeKind.AGENT_PROFILE`. RED on base (returns `None`).

### T003 — Risk probe: edgeless node validity
Before building the emitter, prove an `agent_profile` project node **with no edges** passes `assert_valid(merged)` (`_drg_helpers.py`) and the orphan/exhaustiveness lints (`tests/doctrine/drg/test_kind_cascade_exhaustive.py`, `test_tiered_standards_non_orphan.py`). Fastest check: construct a `DRGGraph` = built-in + a single edgeless `agent_profile:probe` node and run `assert_valid`. **If it trips a hard invariant**, STOP and escalate (blocked) — edge authoring is M5, and node-only emission would need a scope decision. Record the outcome in the Activity Log.

### T004 — Re-key the admission map
In `project_drg.py`: change `_KIND_TO_NODE_KIND` to `dict[ArtifactKind, NodeKind]` with explicit entries `DIRECTIVE/TACTIC/STYLEGUIDE/AGENT_PROFILE` → matching `NodeKind` members (keys = the emittable project-tier allowlist). Rewrite `_node_kind_for(kind: str)` to `try: ak = ArtifactKind(kind) except ValueError: return None` then `return _KIND_TO_NODE_KIND.get(ak)` — keep it `.get`-read. Update the docstring to state the allowlist semantics and that absence (asset/procedure/…) is contractual. Import `ArtifactKind` from `doctrine.artifact_kinds` (C-001-legal: charter→doctrine).

### T005 — Totality-gate reconciliation (atomic with T004)
In `tests/doctrine/drg/test_kind_mapping_totality.py`: (a) add `"charter.synthesizer.project_drg::_KIND_TO_NODE_KIND"` to `_EXEMPT_GET_PARTIALS` with a rationale comment (emittable-project-tier-kind allowlist; sole read site `_node_kind_for` reads via `.get`; deliberate partial — agent_profile emission is M6/#3038). (b) **Remove** `_STRING_KEYED_COVERAGE_WITNESS` and `test_string_keyed_kind_map_coverage_sees_previously_hidden_maps` (the map left the string-keyed scan; the witness would false-fail). Leave every other guard intact. The enum-keyed guard must now discover the map and pass via the exemption.

### T006 — Reusable project-tier profile walk (new module under `src/doctrine/drg/`)
Add `src/doctrine/drg/project_scan.py` (name at your discretion; must live under `doctrine/drg/`). Provide a function that enumerates project-tier `agent_profile` artefacts under `<project_root>/.kittify/doctrine/agent_profiles/` (recursive `*.agent.yaml`, id-key `profile-id`) and returns `list[DRGNode]` of kind `NodeKind.AGENT_PROFILE`, urn `agent_profile:<profile-id>`, `provenance="project"`. Reuse `AgentProfileRepository`'s project reader if its public surface cleanly yields raw project-tier ids; else mirror `_discover_built_in_nodes_in_dir`. **Fail loud** on a malformed/unparseable profile file, naming the file (NFR-002) — no silent skip. Additive-only + dedupe are applied at compose time (T007). Unit-test this module directly in `tests/charter/synthesizer/test_project_drg.py` or a sibling.

### T007 — Compose + wire into the emit/persist seam
In `project_drg.py`, compose the walk so its nodes merge into the project overlay `DRGGraph` before `persist`, reusing the existing additive-only guards (reject built-in-URN shadow → `ProjectDRGValidationError`; overlay dedupe). Wire the call into the `_validation_callback` seam in `orchestrator.py` (`:283-297`) and `_synthesis.py` (`:245-252`) so walked nodes flow through `persist`→`_promote_graph_overlay` into `.kittify/doctrine/graph.yaml`. Do not duplicate emit logic across the two seams — factor a shared helper if needed. Keep `charter`→`doctrine` layering (C-001).

### T008 — Green + boundaries
Make T001/T002 green. Add: a malformed-profile test (loud error naming the file, NFR-002); an `_node_kind_for("asset") is None` assertion (INV-4/asset boundary); an additive-only test (project profile whose URN collides with a built-in profile URN → `ProjectDRGValidationError`); a dedupe test (same profile emitted once). Run the emitter + gate + project_drg suites green.

### T009 — Golden-count attribution (C-003)
Run the DRG/cascade golden suites and confirm any movement is **only** new `agent_profile` project nodes:
```bash
PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest tests/doctrine/drg tests/charter -k "golden or cascade or graph or project_drg" -q
```
Confirm the cascade relation-set definition (`REFERENCE_RELATIONS`) and the org read-path bridge (`merge_three_layers` / `org_pack_loader`) are byte-unchanged in the diff. **If any unrelated golden count moved, STOP and escalate** — it belongs to M2/M5, not M6. Record the attribution in the Activity Log.
- Record: `spec-kitty agent tasks mark-status T001 T002 T003 T004 T005 T006 T007 T008 T009 --status done --mission project-tier-drg-node-emission-01M0DM94`.

## Test Strategy
Markers per package (`doctrine`/`fast` for the gate; charter markers for emitter/reachability). Prove red-first on the merge-base for T001/T002, then green. Run:
```bash
PATH=.venv/bin:$PATH SPEC_KITTY_SYNC_DISABLE=1 pytest \
  tests/charter/test_project_profile_cascade_reach.py \
  tests/charter/synthesizer/test_project_drg.py \
  tests/doctrine/drg/test_kind_mapping_totality.py \
  tests/doctrine/drg/test_nodekind_artifactkind.py -q
```

## Risks & Mitigations
- **Edgeless node trips an orphan/validity invariant** → T003 probes red-first; escalate rather than silently authoring edges (M5 scope).
- **Golden ripple beyond agent_profile** → T009 runs golden suites and STOPs on unrelated movement (C-003 guard).
- **`charter` imports `specify_cli`** → reusable walk lives in `src/doctrine/drg/` (C-001); charter composes downward.
- **Double emission (answer-driven + walk)** → overlay dedupe guard (INV-2); test in T008.
- **Gate weakening** → only add the one exemption + remove the now-stale witness; keep the enum-keyed guard and string-authority guards intact.

## Review Guidance
Verify: T001 was RED on the merge-base and GREEN on the final commit; `_KIND_TO_NODE_KIND` is `ArtifactKind`-keyed + in `_EXEMPT_GET_PARTIALS` with rationale; `_STRING_KEYED_COVERAGE_WITNESS` + its test removed; enum-keyed guard still passes and still catches a dropped kind; the walk lives under `src/doctrine/drg/` (no `specify_cli` import in `charter`); node lands in `.kittify/doctrine/graph.yaml` and is cascade-reachable; edgeless node valid; no `asset:*` node; malformed profile fails loud; golden movement is agent_profile-only and explained; M2/M5 surfaces untouched; zero suppressions; `ruff`/`mypy --strict` clean.

## Activity Log
- (implementer appends entries here)

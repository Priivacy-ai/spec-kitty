---
work_package_id: WP06
title: Graph-back extractor pass + DRG re-baseline (Concern C)
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-009
- FR-011
- NFR-002
tracker_refs: []
planning_base_branch: feat/mission-step-creatability
merge_target_branch: feat/mission-step-creatability
branch_strategy: Planning artifacts for this mission were generated on feat/mission-step-creatability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-step-creatability unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/migration/extractor.py
create_intent:
- tests/doctrine/drg/test_instantiates_edges.py
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/action.graph.yaml
- src/doctrine/template.graph.yaml
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/drg/test_instantiates_edges.py
role: implementer
tags: []
shell_pid: "2670112"
shell_pid_created_at: "1784291540.32"
---

## ⚡ Do This First: Load Agent Profile
Load `/ad-hoc-profile-load python-pedro` (implementer) before anything else.

## Objective
Emit the `mission_type → step → template` chain into the shipped DRG: mint `template:<mission>/<file>` nodes and `action:<type>/<step> --instantiates--> template` edges, then re-baseline the DRG counts + arch markers intentionally. Depends on WP02/03/04 (their step template refs are the input — **N is computed here, after authoring**). `extractor.py` sole owner (C-012).

## Context & FROZEN
- **Why a new pass** (not "unskip templates"): templates are NOT skipped (`_SKIP_REF_TYPES` is empty). A step's template ref is a structured `MissionStepTemplateRef` field, not a `references:` list entry, so no existing pass traverses it. Model the new pass on `extract_mission_type_edges` (`extractor.py:864`, which already mints from the step projection).
- **Consume WP01's `iter_template_refs(steps)`** — do NOT write a second traversal of `step.template` (that re-creates the whack-a-field the mission kills).
- Edges are `action`-sourced → land in `action.graph.yaml`. `template.graph.yaml` gains **nodes only**; the 16 bare `template:<name>` exemplars (#2712) stay untouched (`edges:[]`).
- Node URN via `template_catalog.template_urn` (mission-qualified `template:<mission>/<file>`).

## Subtasks
### T027 — New extractor pass
- Add the pass in `extractor.py`, wired into `generate_graph`: for every `(step, ref)` from `iter_template_refs`, mint node `template:<mission_type>/<template_file>` (kind TEMPLATE) + emit edge `action:<mission_type>/<step> --instantiates--> template:<mission_type>/<template_file>` (`Relation.INSTANTIATES`). Sort edge emission by `(source_urn, target_urn)` (FR-011).

### T028 — Regenerate + re-baseline counts
- Run `spec-kitty doctrine regenerate-graph` to materialize `action.graph.yaml`/`template.graph.yaml`. Compute **N** = total steps carrying a `template` ref across all four types (software-dev's 2 included). Bump `_EXPECTED_NODE_COUNT` 280→`280+N` and `_EXPECTED_EDGE_COUNT` 757→`757+N` in `test_extractor_projection.py:40-41` with a `# S-C / #2724` rationale comment. `_EXPECTED_ORPHAN_COUNT` stays **10**.

### T029 — Positive assertion + arch-marker sweep
- Add `tests/doctrine/drg/test_instantiates_edges.py` asserting each expected `action:<type>/<step> --instantiates--> template:<type>/<file>` edge exists in the shipped graph. **If a new test file trips `_ARCH_SHARD_N_FILES`, append it to `tests/_arch_shard_map.py`** (arch-gate campsite idiom). Sweep + re-baseline every arch marker: orphan-residual (`tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py:78` `DOCUMENTED_ORPHAN_RESIDUAL` ceiling 14 — should NOT need bumping since orphans stay 10; this file is not an edit target, only verify), template cardinality golden-counts (`test_template_discovery.py`). **Expected N=8** (software-dev 2 + documentation/research/plan × {spec,plan}) → counts land at 288/765/10; still compute-then-pin from the actual authored refs.

### T030 — Verify
- `spec-kitty doctrine regenerate-graph --check` green (freshness/byte-identity); `tests/doctrine/drg/` + `tests/architectural/` green; confirm the 16 bare exemplars remain `edges:[]`.

## Branch Strategy
Base `feat/mission-step-creatability`; worktree per `lanes.json`. `spec-kitty agent action implement WP06 --agent <tool>:<model>:python-pedro:implementer` (after WP02/03/04 approved).

## Definition of Done
- New pass emits nodes+edges via `iter_template_refs`; counts bumped to `280+N`/`757+N`, orphans=10; positive instantiates assertion green; every arch marker re-baselined; freshness green; ruff/mypy clean, complexity ≤15.

## Risks & Reviewer Guidance
- Reviewer: confirm the pass consumes `iter_template_refs` (no second traversal); edges are action-sourced in `action.graph.yaml`; N matches the authored ref count (software-dev+3-types); orphans unchanged; no bare-exemplar drift; every golden-count/shard marker accounted for.

## Activity Log

- 2026-07-17T11:57:35Z – claude:sonnet:python-pedro:implementer – shell_pid=2604847 – Assigned agent via action command
- 2026-07-17T12:31:10Z – claude:sonnet:python-pedro:implementer – shell_pid=2604847 – N=8 (software-dev 2 + documentation/research/plan x {spec,plan}); counts 288 nodes / 765 edges / 10 orphans (unchanged); new extract_template_instantiation_edges pass consumes iter_template_refs (no re-traversal), edges action-sourced in action.graph.yaml, 8 template nodes-only in template.graph.yaml; positive instantiates assertion added (test_instantiates_edges.py); 16 bare exemplars untouched (edges:[]); forced companion edit removed template_id_for/template_urn from dead-symbol allowlist; no arch shard-map edit needed; ruff/mypy clean, freshness green, tests/doctrine/drg + tests/architectural green
- 2026-07-17T12:32:24Z – claude:opus:reviewer-renata:reviewer – shell_pid=2670112 – Started review via action command
- 2026-07-17T12:54:16Z – user – shell_pid=2670112 – Review passed: N=8 (software-dev 2 + documentation/research/plan x{spec,plan}), counts 288/765/10 verified by re-running (direct extractor 8 nodes/8 edges + generate_graph 288/765/10 + freshness byte-identical). Single-traversal confirmed: extract_template_instantiation_edges consumes iter_template_refs (no second step.template walk, C-012/C-003). Orphans genuinely 10 - all pre-existing non-template nodes; each of the 8 new template:<mission>/<file> nodes carries an instantiates in-edge. Edges action-sourced in action.graph.yaml, template.graph.yaml nodes-only ending edges:[]; 16 bare exemplars untouched (disjoint from instantiates targets). Positive assertion test_instantiates_edges.py asserts each expected edge against the freshly regenerated shipped graph + bare-exemplar safety (non-synthetic). Dead-symbol edit justified: template_id_for/template_urn now live-called by extractor (removed), template_node/template_nodes still uncalled (kept); gate green. tests/doctrine/drg + full tests/architectural (1021 passed) + orphan-residual(14 unchanged) green; ruff/mypy clean. Scope clean: 6 owned files, no WP05 overlap.

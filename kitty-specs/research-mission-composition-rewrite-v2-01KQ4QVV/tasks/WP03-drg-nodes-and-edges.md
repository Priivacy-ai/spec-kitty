---
work_package_id: WP03
title: DRG Action Nodes + Edges with Validity AND Resolution Proof
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
history:
- timestamp: '2026-04-26T11:46:43Z'
  actor: claude
  note: Created during /spec-kitty.tasks for mission research-mission-composition-rewrite-v2-01KQ4QVV
authoritative_surface: src/doctrine/graph.yaml
execution_mode: code_change
mission_id: 01KQ4QVVZ4DC6CXA1XCZZAQ8AG
mission_slug: research-mission-composition-rewrite-v2-01KQ4QVV
owned_files:
- src/doctrine/graph.yaml
- tests/specify_cli/test_research_drg_nodes.py
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

# WP03 — DRG Action Nodes + Edges with Validity AND Resolution Proof

## Objective

The validated DRG (`<doctrine_root>/graph.yaml`) is what `_dispatch_via_composition` consumes via `resolve_context()` to populate `artifact_urns` for an action. The v1 attempt added action doctrine bundles on disk but never added DRG nodes — so `resolve_context()` returned empty. This WP closes that gap.

Two proofs are mandatory: **(a)** `assert_valid()` accepts the new graph shape, **(b)** `resolve_context(graph, f"action:research/{action}", depth=...).artifact_urns` is non-empty for each of 5 actions.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: lane-based, allocated by `spec-kitty implement WP03`.

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Authoritative References

- `kitty-specs/research-mission-composition-rewrite-v2-01KQ4QVV/plan.md` — D2 (DRG authoring) + per-action edge map
- `src/doctrine/graph.yaml` — read software-dev nodes (lines 5-18) + surrounding edges
- `src/charter/_drg_helpers.py:19-39` — `load_validated_graph()` and `assert_valid()`
- `src/specify_cli/next/_internal_runtime/engine.py:962-1019` — `resolve_context()`
- v1 attempt at `attempt/research-composition-mission-100-broken` — note that v1 did NOT add graph nodes; you cannot copy from v1 here.

## Subtask T010 — Audit graph.yaml node + edge format

**Steps**:
1. Read `src/doctrine/graph.yaml` from the top. Identify the document structure: `nodes:` list and `edges:` list.
2. Find the 5 software-dev action nodes (around lines 5-18). Note the URN format `action:software-dev/<action>`, `kind: action`, `label: <action_name>`.
3. Find the edges where `source: action:software-dev/<action>`. Note relations used (typically `scope`) and target URN format (`directive:<slug>` or `tactic:<slug>`).
4. Count software-dev's edges per action (helps you size research's edges).
5. Note any other relation types in the graph (`vocabulary`, `requires`, etc.) that research might also need.
6. Record findings in your commit message.

**Files**: read-only.

## Subtask T011 — Add 5 action:research/* nodes

**Steps**:
1. Edit `src/doctrine/graph.yaml`. Add 5 new node entries to the `nodes:` list:
   ```yaml
   - urn: action:research/scoping
     kind: action
     label: scoping
   - urn: action:research/methodology
     kind: action
     label: methodology
   - urn: action:research/gathering
     kind: action
     label: gathering
   - urn: action:research/synthesis
     kind: action
     label: synthesis
   - urn: action:research/output
     kind: action
     label: output
   ```
2. Place them adjacent to the software-dev action nodes for readability.
3. Do NOT modify any existing node.

**Files**: `src/doctrine/graph.yaml` (additive).

## Subtask T012 — Add per-action scope edges

**Steps**:
1. Add edges to the `edges:` list per the plan D2 edge map:

   | Source | Targets (relation: scope) |
   |---|---|
   | `action:research/scoping` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement`, `tactic:requirements-validation-workflow`, `tactic:premortem-risk-identification` |
   | `action:research/methodology` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement`, `tactic:adr-drafting-workflow`, `tactic:requirements-validation-workflow` |
   | `action:research/gathering` | `directive:003-decision-documentation-requirement`, `directive:037-living-documentation-sync`, `tactic:requirements-validation-workflow` |
   | `action:research/synthesis` | `directive:003-decision-documentation-requirement`, `directive:010-specification-fidelity-requirement`, `tactic:premortem-risk-identification`, `tactic:requirements-validation-workflow` |
   | `action:research/output` | `directive:010-specification-fidelity-requirement`, `directive:037-living-documentation-sync`, `tactic:requirements-validation-workflow` |

2. Each edge: `source: <action urn>`, `target: <directive or tactic urn>`, `relation: scope`.
3. Before adding any edge, verify the target URN exists in `nodes:` (grep `directive:003-decision-documentation-requirement` etc. in `graph.yaml`). If a target is missing, escalate — do NOT add a dangling edge.

**Files**: `src/doctrine/graph.yaml` (additive).

## Subtask T013 — PROOF (mandatory): assert_valid passes

**Steps**:
1. Run:
   ```bash
   uv run python -c "from charter._drg_helpers import load_validated_graph; from pathlib import Path; g = load_validated_graph(Path('.')); print('VALID', len(g.nodes), 'nodes')"
   ```
2. Expected: `VALID <N>` with N greater than baseline. No exception.
3. If `assert_valid()` raises (cycles, missing target nodes), fix the offending edge in T012 and rerun.
4. Capture output in your commit message under `assert_valid proof:`.

**Files**: no edits in T013 (proof step). Edits in T011/T012 only.

## Subtask T014 — PROOF (mandatory): resolve_context returns non-empty artifact_urns

**Steps**:
1. Run:
   ```python
   from pathlib import Path
   from charter._drg_helpers import load_validated_graph
   from specify_cli.next._internal_runtime.engine import resolve_context

   g = load_validated_graph(Path('.'))
   for action in ['scoping', 'methodology', 'gathering', 'synthesis', 'output']:
       urn = f'action:research/{action}'
       node = g.get_node(urn)
       assert node, f"Missing node: {urn}"
       ctx = resolve_context(g, urn, depth=2)  # match composition's actual depth
       assert ctx.artifact_urns, f"Empty artifact_urns for {urn}"
       print(f"{urn}: {len(ctx.artifact_urns)} artifact_urns")
   ```
2. Expected: 5 lines with non-zero artifact_urns counts.
3. If any action returns empty, the edges in T012 are insufficient — add more or check that the resolver is walking the relations you used (`scope` may need to be supplemented).
4. Confirm exact `depth=` argument by reading `_dispatch_via_composition`'s call into `resolve_context` (around `executor.py:153`); use that same depth in this proof.
5. Capture output in your commit message under `resolve_context proof:`.

**Files**: no edits in T014.

## Subtask T015 — Test asserting both proofs

**Steps**:
1. Create `tests/specify_cli/test_research_drg_nodes.py`.
2. Three tests:
   - `test_research_action_nodes_exist`: parametrized over 5 actions; `load_validated_graph(repo).get_node(...)` returns truthy.
   - `test_research_action_resolve_context_non_empty`: parametrized over 5 actions; `resolve_context(...).artifact_urns` is non-empty.
   - `test_drg_assert_valid_passes`: `load_validated_graph(repo)` succeeds (no exception).
3. **Do NOT mock `load_validated_graph` or `resolve_context`** — these are the C-007 forbidden surfaces. Read the real graph.
4. Run: `uv run pytest tests/specify_cli/test_research_drg_nodes.py -v`. All 11 tests pass (3 + 5 + 5 - duplicate counts).
5. Run regression sweep: `uv run pytest tests/specify_cli/`. No new failures.

**Files**: `tests/specify_cli/test_research_drg_nodes.py` (new).

## Definition of Done

- [ ] `src/doctrine/graph.yaml` has 5 new action nodes + per-action edges per the plan D2 map.
- [ ] No existing nodes/edges modified.
- [ ] `assert_valid()` passes (T013 proof).
- [ ] `resolve_context().artifact_urns` is non-empty for all 5 actions (T014 proof).
- [ ] `tests/specify_cli/test_research_drg_nodes.py` exists with 3 test functions; all pass.
- [ ] No mocks of `load_validated_graph` or `resolve_context` in the test file.
- [ ] mypy --strict + ruff zero new findings.

## Test Strategy

WP03 is the first WP that adds formal tests. The tests are real — they read the actual shipped graph from disk. C-007 forbidden surfaces (`load_validated_graph`, `resolve_context`) are NOT mocked.

## Risks

| Risk | Mitigation |
|---|---|
| Edge target URNs (e.g. `tactic:adr-drafting-workflow`) don't exist in `graph.yaml`. | T012 step 3 verifies each target before adding. |
| `resolve_context()` depth value differs from what composition uses. | T014 step 4 reads the actual depth from `executor.py:153`. |
| `assert_valid()` rejects cycles or duplicate URNs. | The new nodes are unique; edges only outbound from new nodes. No cycle risk. |

## Reviewer Guidance

- Diff `src/doctrine/graph.yaml`. Confirm 5 new nodes + N new edges (where N matches the plan D2 map). No other changes.
- Run T013 + T014 proofs yourself. Both must produce the documented output.
- Run `pytest tests/specify_cli/test_research_drg_nodes.py -v` — all tests pass.
- `grep -E "patch|MagicMock|Mock\\(" tests/specify_cli/test_research_drg_nodes.py` should return zero hits against `load_validated_graph` or `resolve_context`.

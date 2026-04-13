---
work_package_id: WP03
title: build_context_v2
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-009
- NFR-002
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "73314"
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
owned_files:
- src/doctrine/drg/query.py
- src/charter/context.py
- tests/doctrine/drg/test_query.py
- tests/charter/test_context_v2.py
tags: []
---

# WP03: build_context_v2

## Objective

Implement `build_context_v2(profile, action, depth)` in `src/charter/context.py` that queries the Doctrine Reference Graph to assemble governance context. The function composes DRG query primitives from `src/doctrine/drg/query.py` -- it does NOT embed graph traversal logic.

## Context

The existing `build_charter_context()` in `src/charter/context.py` assembles governance context by:
1. Loading action index files from disk
2. Intersecting with project-selected directives
3. Loading doctrine artifacts via `DoctrineService`
4. Rendering formatted text

`build_context_v2()` replaces this with:
1. Loading the merged DRG
2. Walking graph edges by type (scope, requires, suggests, vocabulary)
3. Materializing resolved artifacts via `DoctrineService`
4. Rendering formatted text

The DRG package (`src/doctrine/drg/`) provides query primitives. Charter-specific assembly policy (how to compose the walk results into a prompt block) stays in `src/charter/context.py`.

**Key constraint (FR-009)**: No per-action filtering logic in `build_context_v2`. Context size is determined entirely by graph topology (the `scope` edges in `graph.yaml`). If a surface is too large or too small, the fix is adjusting edges in `graph.yaml`, never adding if-statements in the function body.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T019: Implement DRG query primitives

**Purpose**: Provide reusable graph traversal functions in the DRG package. These are pure graph operations with no charter semantics.

**Steps**:
1. Create `src/doctrine/drg/query.py`
2. Implement `walk_edges(graph: DRGGraph, start_urns: set[str], relations: set[Relation], max_depth: int | None = None) -> set[str]`:
   - BFS/DFS from `start_urns` following only edges matching `relations`
   - If `max_depth` is None: walk until exhausted (transitive closure)
   - If `max_depth` is set: walk up to that many hops
   - Return set of all visited node URNs (including start nodes)
3. Implement `resolve_context(graph: DRGGraph, action_urn: str, depth: int = 2) -> ResolvedContext`:
   - Step 1: Walk `scope` edges from `action_urn` (depth 1) -> scoped artifacts
   - Step 2: Walk `requires` edges from scoped artifacts (transitive) -> hard dependencies
   - Step 3: Walk `suggests` edges from scoped artifacts (to `depth` hops) -> soft recommendations
   - Step 4: Walk `vocabulary` edges from all resolved nodes (depth 1) -> glossary scopes
   - Return `ResolvedContext(artifact_urns=set[str], glossary_scopes=set[str])`
4. Define `ResolvedContext` dataclass:
   ```python
   @dataclass(frozen=True)
   class ResolvedContext:
       artifact_urns: frozenset[str]  # All resolved artifact URNs
       glossary_scopes: frozenset[str]  # Glossary scope URNs
   ```
5. Export from `src/doctrine/drg/__init__.py`

**Design note**: `resolve_context` is the main entry point. It is still a pure graph operation -- it doesn't know about charter rendering, doctrine service materialization, or prompt formatting.

**Files**: `src/doctrine/drg/query.py`

**Validation**:
- [ ] `walk_edges` respects `max_depth` limit
- [ ] `walk_edges` with `max_depth=None` walks transitively
- [ ] `resolve_context` includes scope, requires, suggests, vocabulary results
- [ ] Results are deterministic for the same graph

### T020: Implement `build_context_v2()` in `src/charter/context.py`

**Purpose**: Compose DRG query primitives with charter-specific rendering to produce governance context text.

**Steps**:
1. In `src/charter/context.py`, add the function:
   ```python
   def build_context_v2(
       repo_root: Path,
       *,
       profile: str | None = None,
       action: str,
       depth: int = 2,
   ) -> CharterContextResult:
   ```
2. Implementation flow:
   a. Resolve doctrine root and load merged DRG:
      ```python
      from doctrine.drg import load_graph, merge_layers, resolve_context
      shipped_graph = load_graph(doctrine_root / "graph.yaml")
      project_graph_path = repo_root / ".kittify" / "doctrine" / "graph.yaml"
      project_graph = load_graph(project_graph_path) if project_graph_path.exists() else None
      merged = merge_layers(shipped_graph, project_graph)
      ```
   b. Resolve mission from governance config (reuse existing `load_governance_config`):
      ```python
      governance = load_governance_config(repo_root)
      template_set = governance.doctrine.template_set or "software-dev-default"
      mission = template_set.removesuffix("-default")
      ```
   c. Build action URN: `f"action:{mission}/{action}"`
   d. Query the DRG: `resolved = resolve_context(merged, action_urn, depth=depth)`
   e. Materialize artifacts: Load each artifact via `DoctrineService` and format
   f. Render the same text structure as `build_charter_context()`:
      - Charter Context header
      - Policy Summary
      - Directives section (from resolved artifacts of kind `directive`)
      - Tactics section (from resolved artifacts of kind `tactic`)
      - Extended sections at depth >= 3 (styleguides, toolguides)
      - Reference Docs section
3. **Profile dimension**: In Phase 0, `profile` is accepted but ignored (no profile-scoped edges exist in the DRG yet). Document this in the docstring. Phase 4 will add profile-based filtering.
4. Return `CharterContextResult` with the same fields as `build_charter_context()`

**Key constraint**: No if-statements that check action names and conditionally filter artifacts. The DRG's `scope` edges already determine what each action gets. The rendering logic is generic.

**Files**: `src/charter/context.py`

**Validation**:
- [ ] Function signature matches specification
- [ ] Returns `CharterContextResult` with all fields populated
- [ ] No per-action filtering logic in the function body
- [ ] Profile parameter accepted but documented as ignored in Phase 0
- [ ] Uses DRG query primitives (not reimplementing traversal)

### T021: Unit tests for query primitives

**Purpose**: Test graph traversal with various graph topologies.

**Steps**:
1. Create `tests/doctrine/drg/test_query.py`
2. Test `walk_edges`:
   - Simple chain: A -> B -> C with `requires`; walk from A should reach C
   - Depth limit: walk from A with `max_depth=1` should reach B but not C
   - Multiple relations: walk only `requires` edges ignores `suggests` edges
   - Empty start set: returns empty
   - Start nodes with no outgoing edges: returns just start nodes
3. Test `resolve_context`:
   - Fixture graph with action node having scope, requires, suggests, vocabulary edges
   - Verify artifact_urns includes scope + requires + suggests results
   - Verify glossary_scopes includes vocabulary results
   - Verify depth parameter limits suggests walk
   - Verify deterministic output (same graph -> same result)
4. Create `tests/charter/test_context_v2.py`:
   - Test `build_context_v2` with a real repo root (use `tmp_path` with fixture charter + graph)
   - Test that output text contains expected directive/tactic sections
   - Test that profile=None doesn't crash
   - Test depth=1 vs depth=2 vs depth=3 produce different context sizes

**Files**: `tests/doctrine/drg/test_query.py`, `tests/charter/test_context_v2.py`

**Validation**:
- [ ] 90%+ coverage on `query.py`
- [ ] All edge traversal scenarios covered
- [ ] `build_context_v2` tested with fixture data

### T022: Verify no per-action filtering logic

**Purpose**: Structural audit confirming FR-009 compliance.

**Steps**:
1. In the test suite, add a test that reads the source of `build_context_v2` and asserts:
   - No string literals matching action names (`"specify"`, `"plan"`, `"implement"`, `"review"`, `"tasks"`) appear in the function body
   - No if-statements that branch on the `action` parameter to filter artifacts
2. This is a structural test, not a behavioral one. It prevents future regression where someone adds per-action filtering logic.
3. Alternative: use `ast.parse` to inspect the function's AST for conditional branches on `action`

**Files**: `tests/charter/test_context_v2.py` (extend)

**Validation**:
- [ ] Test passes with current implementation
- [ ] Test would fail if someone added `if action == "specify": ...` filtering

## Definition of Done

1. `src/doctrine/drg/query.py` exists with `walk_edges` and `resolve_context`
2. `build_context_v2()` exists in `src/charter/context.py`
3. Function composes DRG primitives (does not embed traversal logic)
4. No per-action filtering logic (FR-009 verified by structural test)
5. Profile parameter accepted but documented as Phase 0 degenerate
6. Unit tests cover query primitives and context builder
7. 90%+ coverage, mypy --strict clean

## Risks

- **Materialization mismatch**: `build_context_v2` must render artifacts in the same format as `build_charter_context`. If the rendering differs (e.g., different directive line format), the invariant test (WP04) will flag it.
- **Missing vocabulary edges**: If no `vocabulary` edges exist in `graph.yaml` yet, glossary_scopes will be empty. This is expected in Phase 0 and should not fail.
- **DoctrineService import**: `build_context_v2` needs `DoctrineService` to materialize artifacts. Import it lazily (inside the function) to avoid circular imports.

## Reviewer Guidance

- Verify `build_context_v2` does NOT reimplment graph walking -- it must call `resolve_context` from `src/doctrine/drg/query.py`
- Verify no action-name string literals in the function body
- Verify rendering format matches `build_charter_context` output (same line formatting, same section headers)
- Verify profile is truly ignored (not silently altering output)

## Activity Log

- 2026-04-13T09:14:48Z – claude:opus-4-6:implementer:implementer – shell_pid=62811 – Started implementation via action command
- 2026-04-13T09:23:07Z – claude:opus-4-6:implementer:implementer – shell_pid=62811 – build_context_v2 implemented with DRG query composition
- 2026-04-13T09:23:35Z – claude:opus-4-6:reviewer:reviewer – shell_pid=73314 – Started review via action command

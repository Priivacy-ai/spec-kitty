---
work_package_id: WP02
title: Migration Extractor and Surface Calibration
dependencies:
- WP01
requirement_refs:
- C-001
- C-007
- FR-004
- FR-005
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "62442"
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: src/doctrine/drg/migration/
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/__init__.py
- src/doctrine/drg/migration/extractor.py
- src/doctrine/drg/migration/calibrator.py
- src/doctrine/drg/migration/id_normalizer.py
- src/doctrine/graph.yaml
- src/doctrine/missions/software-dev/actions/tasks/index.yaml
- tests/doctrine/drg/migration/__init__.py
- tests/doctrine/drg/migration/test_extractor.py
- tests/doctrine/drg/migration/test_calibrator.py
- tests/doctrine/drg/migration/test_id_normalizer.py
tags: []
---

# WP02: Migration Extractor and Surface Calibration

## Objective

Walk all shipped doctrine artifacts and action index files, extract every inline reference field, and emit equivalent typed edges into `graph.yaml`. Apply per-action surface calibration so each action receives the right minimum-effective-dose governance surface.

## Context

Inline references are scattered across three artifact categories:

**Directives** (`src/doctrine/directives/shipped/*.directive.yaml`):
- `tactic_refs: [id, ...]` -- list of tactic IDs (slugs)
- `references: [{type, id, when?}, ...]` -- typed refs to directives, tactics, styleguides

**Tactics** (`src/doctrine/tactics/shipped/*.tactic.yaml`):
- `references: [{type, id, name?, when?}, ...]` -- typed refs to tactics, styleguides

**Paradigms** (`src/doctrine/paradigms/shipped/*.paradigm.yaml`):
- `tactic_refs: [id, ...]` -- tactic IDs
- `directive_refs: [id, ...]` -- directive IDs (DIRECTIVE_NNN format)
- `opposed_by: [{type, id, reason}, ...]` -- conflict refs

**Action indices** (`src/doctrine/missions/software-dev/actions/*/index.yaml`):
- `directives: [slug, ...]` -- directive slugs (NNN-name format)
- `tactics: [id, ...]` -- tactic IDs
- `styleguides: [id, ...]` -- styleguide IDs
- `toolguides: [id, ...]` -- toolguide IDs
- `procedures: [id, ...]` -- procedure IDs

Current action surface sizes: specify(3), plan(4), implement(13), review(5), tasks(no index).

**Calibration gap**: `review` surface (5) is far below `implement` (13), violating the `≈` relation. `tasks` has no index at all.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T011: Implement `id_normalizer.py`

**Purpose**: Normalize directive IDs between the two formats used across the codebase.

**Steps**:
1. Create `src/doctrine/drg/migration/id_normalizer.py`
2. Implement `normalize_directive_id(raw: str) -> str`:
   - If matches `^DIRECTIVE_\d+$` -> return as-is
   - If starts with digits (e.g., `024-locality-of-change`) -> extract digits, zero-pad to 3, return `DIRECTIVE_NNN`
   - Otherwise -> return `raw.upper()` (fallback)
3. Implement `directive_to_urn(raw: str) -> str`:
   - Returns `f"directive:{normalize_directive_id(raw)}"`
4. Implement `artifact_to_urn(kind: str, raw_id: str) -> str`:
   - For directives: use `directive_to_urn`
   - For all others: `f"{kind}:{raw_id}"`

**Reference**: The existing `_normalize_directive_id()` in `src/charter/context.py:133-144` already handles this logic. Reuse the same algorithm but in a standalone module.

**Files**: `src/doctrine/drg/migration/id_normalizer.py`

**Validation**:
- [ ] `normalize_directive_id("024-locality-of-change")` returns `"DIRECTIVE_024"`
- [ ] `normalize_directive_id("DIRECTIVE_024")` returns `"DIRECTIVE_024"`
- [ ] `normalize_directive_id("3-short")` returns `"DIRECTIVE_003"`
- [ ] `directive_to_urn("024-locality-of-change")` returns `"directive:DIRECTIVE_024"`

### T012: Implement artifact walker

**Purpose**: Walk shipped directive, tactic, and paradigm YAML files and extract all inline references as DRG edges.

**Steps**:
1. Create `src/doctrine/drg/migration/extractor.py`
2. Implement `extract_artifact_edges(doctrine_root: Path) -> tuple[list[DRGNode], list[DRGEdge]]`:
   - Walk `{doctrine_root}/directives/shipped/*.directive.yaml`:
     - Create node: `directive:{id}` with label from `title`
     - For each `tactic_refs` entry: emit `requires` edge to `tactic:{id}`
     - For each `references` entry: emit `requires` edge if `type=directive`, `suggests` edge if `type=tactic|styleguide`; carry `when` metadata
   - Walk `{doctrine_root}/tactics/shipped/*.tactic.yaml`:
     - Create node: `tactic:{id}` with label from `name`
     - For each `references` entry: emit `suggests` edge; carry `when` metadata
   - Walk `{doctrine_root}/paradigms/shipped/*.paradigm.yaml`:
     - Create node: `paradigm:{id}` with label from `name`
     - For each `tactic_refs` entry: emit `requires` edge to `tactic:{id}`
     - For each `directive_refs` entry: emit `requires` edge to `directive:{normalize(id)}`
     - For each `opposed_by` entry: emit `replaces` edge to `{type}:{id}`; carry `reason` metadata
3. Also create nodes for any targets that don't have their own YAML file (e.g., referenced tactics that exist as shipped but weren't walked yet)
4. Use `ruamel.yaml` for loading (consistent with project)

**Edge case**: A directive's `tactic_refs` may reference a tactic that also appears as a node from the tactics walker. Deduplicate nodes by URN.

**Files**: `src/doctrine/drg/migration/extractor.py`

**Validation**:
- [ ] Walks all shipped directives (~13 files)
- [ ] Walks all shipped tactics (~43 files)
- [ ] Walks all shipped paradigms (3 files)
- [ ] No duplicate nodes in output
- [ ] Edge count matches inline ref count per file

### T013: Implement action index walker

**Purpose**: Walk action index files and extract action-to-artifact `scope` edges.

**Steps**:
1. In `extractor.py`, implement `extract_action_edges(doctrine_root: Path) -> tuple[list[DRGNode], list[DRGEdge]]`:
   - Walk `{doctrine_root}/missions/*/actions/*/index.yaml`
   - For each index file:
     - Parse `action` field and derive mission name from path
     - Create node: `action:{mission}/{action}` (e.g., `action:software-dev/specify`)
     - For each `directives` entry: emit `scope` edge to `directive:{normalize(slug)}`
     - For each `tactics` entry: emit `scope` edge to `tactic:{id}`
     - For each `styleguides` entry: emit `scope` edge to `styleguide:{id}`
     - For each `toolguides` entry: emit `scope` edge to `toolguide:{id}`
     - For each `procedures` entry: emit `scope` edge to `procedure:{id}`
2. Handle empty lists gracefully (no edges emitted for `[]`)
3. Ensure directive slug normalization: `024-locality-of-change` -> `directive:DIRECTIVE_024`

**Files**: `src/doctrine/drg/migration/extractor.py`

**Validation**:
- [ ] Walks all 4 existing action indices (specify, plan, implement, review)
- [ ] Creates action nodes with correct URNs
- [ ] Directive slugs are normalized to `DIRECTIVE_NNN` format
- [ ] Empty lists produce no edges

### T014: Create `tasks` action index

**Purpose**: The `tasks` action has no index today. Create one with appropriate scope.

**Steps**:
1. Create `src/doctrine/missions/software-dev/actions/tasks/index.yaml`
2. The `tasks` action breaks a plan into work packages. It needs:
   - Planning context (what was decided) -- overlap with `plan`
   - Some implementation awareness (what will be built) -- lighter than `implement`
   - Decision documentation -- same as `plan`
3. Proposed content:
   ```yaml
   action: tasks
   directives:
     - 003-decision-documentation-requirement
     - 010-specification-fidelity-requirement
     - 024-locality-of-change
   tactics:
     - requirements-validation-workflow
     - adr-drafting-workflow
     - problem-decomposition
   styleguides: []
   toolguides: []
   procedures: []
   ```
4. This gives tasks 6 total refs: heavier than plan (4) but lighter than implement (13)
5. The calibration test (WP05) will verify this satisfies the inequality

**Files**: `src/doctrine/missions/software-dev/actions/tasks/index.yaml`

**Validation**:
- [ ] File exists and is valid YAML
- [ ] Surface size: `|tasks|` > `|plan|` and `|tasks|` < `|implement|`

### T015: Implement surface calibrator

**Purpose**: Adjust scope edges so action surfaces respect minimum-effective-dose inequalities.

**Steps**:
1. Create `src/doctrine/drg/migration/calibrator.py`
2. Implement `calibrate_surfaces(nodes: list[DRGNode], edges: list[DRGEdge]) -> list[DRGEdge]`:
   - Measure current surface for each action node (count of `scope` edges from that action)
   - Check inequalities:
     ```
     |specify| < |plan| < |implement|
     |tasks|   < |implement|
     |review|  ≈ |implement|  (within 80%)
     ```
   - If `review` surface is < 80% of `implement` surface: add scope edges from `implement`'s scope that are missing from `review`. Specifically, review should share the implementation-relevant directives and tactics that help reviewers judge correctness.
   - Return the full edge list with calibration adjustments applied
3. Implement `measure_surface(action_urn: str, edges: list[DRGEdge]) -> int`:
   - Count distinct targets of `scope` edges from the given action node
4. The calibrator ONLY adjusts `scope` edges between action nodes and artifacts. It does not add filtering logic.

**Calibration for review**: The review action should include directives and tactics that help a reviewer evaluate implementation quality. Copy missing `scope` edges from `implement` to `review` until `|review|` >= 80% of `|implement|`.

**Files**: `src/doctrine/drg/migration/calibrator.py`

**Validation**:
- [ ] After calibration, all inequalities hold
- [ ] Calibrator only adds `scope` edges, never removes
- [ ] Review surface approaches implement surface (>= 80%)

### T016: Generate `graph.yaml`

**Purpose**: Compose the extractor and calibrator to produce the final graph file.

**Steps**:
1. In `extractor.py`, implement `generate_graph(doctrine_root: Path, output_path: Path) -> DRGGraph`:
   - Call `extract_artifact_edges()` to get artifact nodes + edges
   - Call `extract_action_edges()` to get action nodes + edges
   - Merge all nodes (deduplicate by URN) and all edges
   - Call `calibrate_surfaces()` to adjust scope edges
   - Also create nodes for any styleguides, toolguides, procedures, agent profiles referenced in edges but not yet as nodes (scan `shipped/` dirs for them)
   - Create `DRGGraph` with `schema_version="1.0"`, `generated_at` (ISO timestamp), `generated_by="drg-migration-v1"`
   - Validate with `assert_valid()`
   - Write to `output_path` as YAML (sorted keys for deterministic output)
   - Return the graph
2. The default output path is `src/doctrine/graph.yaml`
3. Running `generate_graph()` twice with the same input must produce identical output (idempotent)

**Files**: `src/doctrine/drg/migration/extractor.py`, `src/doctrine/graph.yaml` (generated)

**Validation**:
- [ ] `graph.yaml` exists and validates
- [ ] Running migration twice produces identical file (diff returns empty)
- [ ] All node URNs are unique
- [ ] All edge triples are unique

### T017: Validate edge count

**Purpose**: Prove the extractor captured every inline reference.

**Steps**:
1. In tests, implement a completeness check:
   - Walk all shipped artifacts and count every inline reference field entry
   - Load `graph.yaml` and count edges
   - Assert `len(graph.edges) >= total_inline_refs`
   - The `>=` accounts for calibration-added edges
2. Also verify no inline reference was silently dropped:
   - For each artifact file, collect its inline refs
   - Verify each has a corresponding edge in the graph
   - Report any mismatches

**Files**: `tests/doctrine/drg/migration/test_extractor.py`

**Validation**:
- [ ] Edge count >= inline reference count
- [ ] No individual artifact has missing edges
- [ ] Calibration edges are accounted for in the >= comparison

### T018: Unit tests

**Purpose**: Comprehensive test coverage for the migration package.

**Steps**:
1. Create `tests/doctrine/drg/migration/test_id_normalizer.py`:
   - Test all ID format conversions
   - Test edge cases (single digit, already-normalized, unknown format)
2. Create `tests/doctrine/drg/migration/test_extractor.py`:
   - Test artifact walker against a small fixture set (or against real shipped artifacts)
   - Test action index walker
   - Test `generate_graph()` end-to-end
   - Test idempotency (run twice, compare)
   - Test edge count completeness (T017)
3. Create `tests/doctrine/drg/migration/test_calibrator.py`:
   - Test calibration with surfaces that already satisfy inequalities (no-op)
   - Test calibration with review surface too low (adds edges)
   - Test that calibrator only adds `scope` edges
   - Test surface measurement function

**Files**: `tests/doctrine/drg/migration/test_*.py`

**Validation**:
- [ ] 90%+ coverage on all migration module files
- [ ] mypy --strict clean
- [ ] Tests run in < 10s (no heavy I/O)

## Definition of Done

1. `graph.yaml` exists at `src/doctrine/graph.yaml` and validates
2. Edge count >= sum of all inline reference fields across shipped artifacts
3. Calibration inequalities hold for all actions
4. Migration is idempotent
5. `tasks` action index exists with appropriate scope
6. No inline reference fields modified in any YAML (C-001)
7. 90%+ test coverage, mypy --strict clean

## Risks

- **Tactic/styleguide/toolguide not found**: Some referenced IDs may not have a corresponding shipped YAML file. The extractor should still create a node for them (they exist as "known but not loaded" artifacts).
- **Action index discovery**: Only `software-dev` has action indices today. If other missions (research, documentation) gain indices later, the walker should handle them. For now, document that only `software-dev` actions are extracted.
- **Calibration is a judgment call**: The review scope adjustment is based on the 80% threshold and borrowing from implement. If this produces poor governance context, the fix is adjusting the threshold or the specific edges, not adding filtering logic.

## Reviewer Guidance

- Verify directive ID normalization handles both `DIRECTIVE_NNN` and `NNN-slug` formats
- Verify the `tasks` action index has appropriate scope (not too heavy, not too light)
- Verify calibration only adds `scope` edges (no other relation types)
- Verify `graph.yaml` is deterministic (sorted keys, consistent formatting)
- Verify no shipped YAML files were modified (only new files created)

## Activity Log

- 2026-04-13T08:59:25Z – claude:opus-4-6:implementer:implementer – shell_pid=52893 – Started implementation via action command
- 2026-04-13T09:11:30Z – claude:opus-4-6:implementer:implementer – shell_pid=52893 – Migration extractor complete, graph.yaml generated and validated
- 2026-04-13T09:11:55Z – claude:opus-4-6:reviewer:reviewer – shell_pid=62442 – Started review via action command

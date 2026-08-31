---
work_package_id: WP01
title: DRG Schema and Pydantic Model
dependencies: []
requirement_refs:
- FR-002
- FR-003
- NFR-001
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-drg-phase-zero-01KP2YCE
base_commit: 27b6f3dfab55187448bf01fadf3a0868cfa66177
created_at: '2026-04-13T08:50:55.803063+00:00'
subtasks:
- T005
- T006
- T007
- T008
- T009
- T010
shell_pid: "52457"
agent: "claude:opus-4-6:reviewer:reviewer"
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: src/doctrine/drg/
execution_mode: code_change
owned_files:
- src/doctrine/drg/__init__.py
- src/doctrine/drg/models.py
- src/doctrine/drg/loader.py
- src/doctrine/drg/validator.py
- tests/doctrine/drg/__init__.py
- tests/doctrine/drg/conftest.py
- tests/doctrine/drg/test_models.py
- tests/doctrine/drg/test_loader.py
- tests/doctrine/drg/test_validator.py
- tests/doctrine/drg/fixtures/**
tags: []
---

# WP01: DRG Schema and Pydantic Model

## Objective

Define the Doctrine Reference Graph schema as Pydantic models with validation for graph integrity. This is the foundation for all subsequent WPs.

## Context

The DRG represents doctrine artifacts as nodes and their relationships as typed edges in a YAML graph document. See [data-model.md](../data-model.md) for the complete schema specification.

Key design decisions:
- URN format: `{kind}:{id}` (e.g., `directive:DIRECTIVE_001`)
- 9 node kinds: `directive`, `tactic`, `paradigm`, `styleguide`, `toolguide`, `procedure`, `agent_profile`, `action`, `glossary_scope`
- 8 edge relations: `requires`, `suggests`, `applies`, `scope`, `vocabulary`, `instantiates`, `replaces`, `delegates_to`
- `schema_version: "1.0"` in the YAML document

This package is strictly doctrine-graph infrastructure. It does NOT contain charter-specific assembly policy (profile x action x depth expansion). That lives in `src/charter/context.py`.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T005: Define `NodeKind` and `Relation` enums

**Purpose**: Create the canonical enumeration types for graph node kinds and edge relation types.

**Steps**:
1. Create `src/doctrine/drg/__init__.py` with public API exports
2. Create `src/doctrine/drg/models.py`
3. Define `NodeKind(StrEnum)`:
   ```python
   class NodeKind(StrEnum):
       DIRECTIVE = "directive"
       TACTIC = "tactic"
       PARADIGM = "paradigm"
       STYLEGUIDE = "styleguide"
       TOOLGUIDE = "toolguide"
       PROCEDURE = "procedure"
       AGENT_PROFILE = "agent_profile"
       ACTION = "action"
       GLOSSARY_SCOPE = "glossary_scope"
   ```
4. Define `Relation(StrEnum)`:
   ```python
   class Relation(StrEnum):
       REQUIRES = "requires"
       SUGGESTS = "suggests"
       APPLIES = "applies"
       SCOPE = "scope"
       VOCABULARY = "vocabulary"
       INSTANTIATES = "instantiates"
       REPLACES = "replaces"
       DELEGATES_TO = "delegates_to"
   ```
5. Note alignment with `src/doctrine/artifact_kinds.py::ArtifactKind` -- `NodeKind` is a superset (adds `action` and `glossary_scope`)

**Files**: `src/doctrine/drg/models.py`, `src/doctrine/drg/__init__.py`

### T006: Implement `DRGNode`, `DRGEdge`, `DRGGraph` Pydantic models

**Purpose**: Define the Pydantic v2 models that parse and validate `graph.yaml`.

**Steps**:
1. In `src/doctrine/drg/models.py`, define:

   ```python
   class DRGNode(BaseModel):
       urn: str  # validated by pattern
       kind: NodeKind
       label: str | None = None

   class DRGEdge(BaseModel):
       source: str  # node URN
       target: str  # node URN
       relation: Relation
       when: str | None = None      # applicability context
       reason: str | None = None    # opposition/conflict justification

   class DRGGraph(BaseModel):
       schema_version: str = Field(pattern=r"^1\.0$")
       generated_at: str            # ISO 8601
       generated_by: str
       nodes: list[DRGNode]
       edges: list[DRGEdge]
   ```

2. Add a URN pattern validator: `^[a-z_]+:[A-Za-z0-9_/.-]+$`
3. Add a model validator that checks `kind` matches the kind prefix in `urn` (e.g., `directive:DIRECTIVE_001` must have `kind=NodeKind.DIRECTIVE`)
4. Add convenience methods:
   - `DRGGraph.node_urns() -> set[str]` -- all node URNs
   - `DRGGraph.edges_from(urn, relation=None) -> list[DRGEdge]` -- outgoing edges
   - `DRGGraph.get_node(urn) -> DRGNode | None` -- lookup by URN

**Files**: `src/doctrine/drg/models.py`

**Validation**:
- [ ] Pydantic model round-trips through YAML
- [ ] URN validation rejects malformed URNs
- [ ] Kind/URN consistency check works

### T007: Implement `load_graph()` and `merge_layers()`

**Purpose**: Load `graph.yaml` from disk and support merging shipped + project layers.

**Steps**:
1. Create `src/doctrine/drg/loader.py`
2. Implement `load_graph(path: Path) -> DRGGraph`:
   - Read YAML file using `ruamel.yaml` (consistent with project conventions)
   - Parse into `DRGGraph` Pydantic model
   - Return validated model
   - Raise `DRGLoadError` on file not found, YAML parse error, or validation error
3. Implement `merge_layers(shipped: DRGGraph, project: DRGGraph | None) -> DRGGraph`:
   - Start with all nodes/edges from shipped
   - If project layer exists: add new nodes (by URN), override labels for existing URNs, add all edges (additive only)
   - Return merged graph (not yet validated -- caller should validate)
4. Export from `__init__.py`

**Files**: `src/doctrine/drg/loader.py`

**Validation**:
- [ ] `load_graph` reads a valid YAML and returns `DRGGraph`
- [ ] `load_graph` raises `DRGLoadError` on missing file
- [ ] `merge_layers` correctly merges two graphs
- [ ] Project layer adds nodes, overrides labels, adds edges
- [ ] Project layer does not remove shipped nodes/edges

### T008: Implement validator

**Purpose**: Validate graph integrity beyond what Pydantic field validators catch.

**Steps**:
1. Create `src/doctrine/drg/validator.py`
2. Implement `validate_graph(graph: DRGGraph) -> list[str]` returning a list of error messages (empty = valid):
   - **Dangling references**: Every `source` and `target` in edges must exist in `node_urns()`
   - **Unknown relations**: Already enforced by Pydantic enum, but double-check
   - **Malformed URNs**: Already enforced by pattern, but validate the kind prefix parses
   - **Cycles in `requires`**: Build adjacency list for `requires` edges only, run DFS, detect back edges
   - **Duplicate edges**: `(source, target, relation)` triple must be unique
3. Implement `assert_valid(graph: DRGGraph) -> None` that raises `DRGValidationError` if errors exist
4. Export from `__init__.py`

**Cycle detection detail**: Only `requires` edges must be acyclic (they represent hard dependencies). `suggests`, `replaces`, and other relations may have cycles.

**Files**: `src/doctrine/drg/validator.py`

**Validation**:
- [ ] Detects dangling references
- [ ] Detects cycles in `requires` subgraph
- [ ] Detects duplicate edges
- [ ] Accepts valid graphs without false positives
- [ ] Returns specific error messages (not just "invalid")

### T009: Create fixture graphs

**Purpose**: Provide test fixtures for all validation scenarios.

**Steps**:
1. Create `tests/doctrine/drg/fixtures/` directory
2. Create `valid_graph.yaml` -- a small but realistic graph with ~10 nodes and ~15 edges covering all relation types
3. Create `dangling_ref_graph.yaml` -- an edge targeting a non-existent node
4. Create `cyclic_requires_graph.yaml` -- a cycle in `requires` edges (A requires B, B requires C, C requires A)
5. Create `malformed_urn_graph.yaml` -- a node with URN like `bad urn!`
6. Create `duplicate_edge_graph.yaml` -- same (source, target, relation) twice
7. Create `kind_mismatch_graph.yaml` -- URN prefix doesn't match kind field
8. Create `empty_graph.yaml` -- valid graph with zero nodes and zero edges

**Files**: `tests/doctrine/drg/fixtures/*.yaml`

### T010: Unit tests

**Purpose**: Comprehensive test coverage for models, loader, and validator.

**Steps**:
1. Create `tests/doctrine/drg/conftest.py` with shared fixtures (load YAML fixtures, tmp_path helpers)
2. Create `tests/doctrine/drg/test_models.py`:
   - Test DRGNode creation and URN validation
   - Test DRGEdge creation
   - Test DRGGraph creation and convenience methods
   - Test rejection of malformed URNs, bad schema_version, kind/URN mismatch
3. Create `tests/doctrine/drg/test_loader.py`:
   - Test `load_graph` with valid YAML
   - Test `load_graph` with missing file -> `DRGLoadError`
   - Test `load_graph` with invalid YAML -> `DRGLoadError`
   - Test `merge_layers` with None project layer (passthrough)
   - Test `merge_layers` with additive project layer
   - Test `merge_layers` label override
4. Create `tests/doctrine/drg/test_validator.py`:
   - Test validation passes for valid graph
   - Test dangling reference detection
   - Test cycle detection in `requires` (but not in `suggests`)
   - Test duplicate edge detection
   - Test `assert_valid` raises on errors, passes on valid

**Files**: `tests/doctrine/drg/test_models.py`, `tests/doctrine/drg/test_loader.py`, `tests/doctrine/drg/test_validator.py`, `tests/doctrine/drg/conftest.py`

**Validation**:
- [ ] All fixtures load correctly in tests
- [ ] 90%+ line coverage on `models.py`, `loader.py`, `validator.py`
- [ ] mypy --strict clean on all new files

## Definition of Done

1. `src/doctrine/drg/` package exists with `models.py`, `loader.py`, `validator.py`
2. All Pydantic models validate correctly per data-model.md
3. Validator catches all specified integrity violations
4. Layer merging works (shipped + project additive merge)
5. Fixture graphs cover all validation scenarios
6. 90%+ test coverage, mypy --strict clean

## Risks

- **Pydantic v2 migration**: Ensure using Pydantic v2 BaseModel (check project's pinned version). If project uses v1, adapt field definitions accordingly.
- **YAML library choice**: Use `ruamel.yaml` (project standard), not PyYAML. Round-trip safety matters for potential future writes.

## Reviewer Guidance

- Verify URN format regex is strict enough (no spaces, no special chars beyond `_/.-`)
- Verify cycle detection only applies to `requires` edges
- Verify `merge_layers` is additive-only (no deletion semantics)
- Check that `DRGGraph` convenience methods use efficient lookups (dict, not linear scan)

## Activity Log

- 2026-04-13T08:50:56Z – claude:opus-4-6:implementer:implementer – shell_pid=38776 – Assigned agent via action command
- 2026-04-13T08:56:51Z – claude:opus-4-6:implementer:implementer – shell_pid=38776 – DRG schema and model implemented with full test coverage
- 2026-04-13T08:57:09Z – claude:opus-4-6:reviewer:reviewer – shell_pid=52457 – Started review via action command
- 2026-04-13T08:59:08Z – claude:opus-4-6:reviewer:reviewer – shell_pid=52457 – Review passed: 59/59 tests pass, 100% coverage, mypy --strict clean. All acceptance criteria met: Pydantic models validate URNs and reject malformed shapes; validator catches dangling refs, duplicate edges, requires-only cycles; merge_layers is additive-only; all 7 fixtures present; no files outside owned_files scope; package has zero charter-specific imports.

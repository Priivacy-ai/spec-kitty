---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Dependency Graph Utilities (TDD Foundation)"
phase: "Phase 0 - Test Infrastructure"
lane: "done"
dependencies: []
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-07T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Dependency Graph Utilities (TDD Foundation)

**Implementation command:**
```bash
spec-kitty implement WP01
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: Update `review_status: acknowledged` when you begin addressing feedback.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially. Reviewers will populate it if needed.]*

---

## Objectives & Success Criteria

**Primary Goal**: Create `src/specify_cli/core/dependency_graph.py` module with utilities for parsing WP dependencies, detecting circular dependencies, and validating dependency graphs.

**Success Criteria**:
- ✅ All unit tests pass (T001-T005)
- ✅ dependency_graph.py module implements all required functions
- ✅ Cycle detection works correctly for various graph shapes (no cycles, simple cycles, complex DAGs)
- ✅ Test coverage >90% for dependency_graph.py

**TDD Mandate**: Tests must be written FIRST (T001-T005), should FAIL initially, then implementation (T006) makes them pass.

---

## Context & Constraints

**Why this WP matters**: Dependency graph utilities are foundational for the entire workspace-per-WP feature. Without correct cycle detection and validation, we could generate invalid task structures or allow users to create dependent workspaces in wrong order.

**Reference Documents**:
- [plan.md](../plan.md) - Section 1.3: Dependency Graph Utilities (function signatures)
- [data-model.md](../data-model.md) - DependencyGraph entity definition, cycle detection algorithm
- [spec.md](../spec.md) - FR-012 through FR-015 (dependency validation requirements)

**Constitutional Alignment**:
- Principle V (File-Based Everything): Dependencies stored in WP frontmatter, parsed from files
- Technical Standards: Python 3.11+, type hints required, pytest for testing

**Constraints**:
- Must work with YAML frontmatter (ruamel.yaml parser)
- Performance: <100ms for 50 WPs, <500ms cycle detection for complex graphs
- No external dependencies beyond existing Spec Kitty stack

---

## Subtasks & Detailed Guidance

### Subtask T001 – Write tests for dependency parsing

**Purpose**: Validate parse_wp_dependencies() reads dependencies from WP frontmatter correctly.

**Steps**:
1. Create `tests/specify_cli/test_dependency_graph.py`
2. Write test cases for parse_wp_dependencies():
   - Test parsing WP with no dependencies (empty list)
   - Test parsing WP with single dependency
   - Test parsing WP with multiple dependencies
   - Test parsing WP with missing dependencies field (defaults to [])
   - Test parsing invalid frontmatter (error handling)

**Files**: `tests/specify_cli/test_dependency_graph.py`

**Parallel?**: Can run in parallel with T002-T005 (different test functions)

**Example Test**:
```python
def test_parse_wp_dependencies_single():
    """Test parsing WP with single dependency."""
    wp_content = """---
work_package_id: "WP02"
dependencies: ["WP01"]
---
# Content
"""
    wp_file = tmp_path / "WP02.md"
    wp_file.write_text(wp_content)

    deps = parse_wp_dependencies(wp_file)
    assert deps == ["WP01"]
```

---

### Subtask T002 – Write tests for graph building

**Purpose**: Validate build_dependency_graph() scans all WPs and creates correct adjacency list.

**Steps**:
1. In `tests/specify_cli/test_dependency_graph.py`, add test cases for build_dependency_graph()
2. Test cases:
   - Empty feature (no WPs) → empty graph
   - Single WP with no dependencies → {"WP01": []}
   - Linear chain: WP01 → WP02 → WP03
   - Fan-out: WP01 → [WP02, WP03, WP04]
   - Complex DAG (diamond pattern)

**Files**: `tests/specify_cli/test_dependency_graph.py`

**Parallel?**: Yes, can write in parallel with T001, T003-T005

**Example Test**:
```python
def test_build_graph_linear_chain(tmp_path):
    """Test graph building with linear dependency chain."""
    feature_dir = tmp_path / "kitty-specs" / "010-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (no deps)
    (tasks_dir / "WP01.md").write_text("---\nwork_package_id: WP01\ndependencies: []\n---")
    # Create WP02 (depends on WP01)
    (tasks_dir / "WP02.md").write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---")

    graph = build_dependency_graph(feature_dir)
    assert graph == {"WP01": [], "WP02": ["WP01"]}
```

---

### Subtask T003 – Write tests for cycle detection

**Purpose**: Validate detect_cycles() correctly identifies circular dependencies using DFS algorithm.

**Steps**:
1. Add test cases for detect_cycles() to test_dependency_graph.py
2. Test cases:
   - Acyclic graph (no cycles) → returns None
   - Simple cycle: WP01 → WP02 → WP01
   - Self-dependency: WP01 → WP01
   - Complex cycle: WP01 → WP02 → WP03 → WP01
   - Multiple cycles in same graph

**Files**: `tests/specify_cli/test_dependency_graph.py`

**Parallel?**: Yes, independent test function

**Example Test**:
```python
def test_detect_cycles_simple():
    """Test detection of simple circular dependency."""
    graph = {"WP01": ["WP02"], "WP02": ["WP01"]}
    cycles = detect_cycles(graph)

    assert cycles is not None
    assert len(cycles) == 1
    # Cycle should be ["WP01", "WP02", "WP01"] or similar
    assert "WP01" in cycles[0] and "WP02" in cycles[0]

def test_detect_cycles_none():
    """Test acyclic graph returns None."""
    graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}
    cycles = detect_cycles(graph)
    assert cycles is None
```

---

### Subtask T004 – Write tests for dependency validation

**Purpose**: Validate validate_dependencies() catches invalid dependencies (missing WPs, self-deps, etc.).

**Steps**:
1. Add test cases for validate_dependencies()
2. Test cases:
   - Valid dependencies → (True, [])
   - Missing dependency (WP99 doesn't exist) → (False, ["WP99 not found"])
   - Self-dependency (WP01 depends on WP01) → (False, ["Cannot depend on self"])
   - Circular dependency → (False, ["Circular dependency detected"])
   - Invalid WP ID format ("WP1" instead of "WP01") → (False, ["Invalid WP ID"])

**Files**: `tests/specify_cli/test_dependency_graph.py`

**Parallel?**: Yes, independent test function

**Example Test**:
```python
def test_validate_dependencies_missing():
    """Test validation catches missing dependencies."""
    graph = {"WP01": [], "WP02": ["WP01"]}
    is_valid, errors = validate_dependencies("WP03", ["WP99"], graph)

    assert is_valid is False
    assert any("WP99" in err for err in errors)
```

---

### Subtask T005 – Write tests for dependent lookup

**Purpose**: Validate get_dependents() correctly finds WPs that depend on a given WP (inverse graph query).

**Steps**:
1. Add test cases for get_dependents()
2. Test cases:
   - WP with no dependents → []
   - WP with single dependent → ["WP02"]
   - WP with multiple dependents (fan-out) → ["WP02", "WP03", "WP04"]
   - Query non-existent WP → []

**Files**: `tests/specify_cli/test_dependency_graph.py`

**Parallel?**: Yes, independent test function

**Example Test**:
```python
def test_get_dependents_fan_out():
    """Test finding dependents in fan-out pattern."""
    graph = {
        "WP01": [],
        "WP02": ["WP01"],
        "WP03": ["WP01"],
        "WP04": ["WP01"]
    }
    dependents = get_dependents("WP01", graph)
    assert set(dependents) == {"WP02", "WP03", "WP04"}
```

---

### Subtask T006 – Implement dependency_graph.py module

**Purpose**: Create the actual implementation to make all tests (T001-T005) pass.

**Steps**:
1. Create `src/specify_cli/core/dependency_graph.py`
2. Implement functions in order:
   - `parse_wp_dependencies(wp_file: Path) -> list[str]`
   - `build_dependency_graph(feature_dir: Path) -> dict[str, list[str]]`
   - `detect_cycles(graph: dict[str, list[str]]) -> list[list[str]] | None`
   - `validate_dependencies(wp_id: str, declared_deps: list[str], graph: dict[str, list[str]]) -> tuple[bool, list[str]]`
   - `get_dependents(wp_id: str, graph: dict[str, list[str]]) -> list[str]`
3. Use ruamel.yaml for frontmatter parsing (consistent with existing code)
4. Implement DFS cycle detection per data-model.md algorithm
5. Add type hints for all functions (Python 3.11+)
6. Run tests - verify all pass

**Files**: `src/specify_cli/core/dependency_graph.py`

**Implementation Details**:

**parse_wp_dependencies**:
```python
def parse_wp_dependencies(wp_file: Path) -> list[str]:
    """Parse dependencies from WP frontmatter."""
    from ruamel.yaml import YAML
    yaml = YAML()

    with open(wp_file) as f:
        content = f.read()
        # Split frontmatter from content
        if not content.startswith('---'):
            return []

        parts = content.split('---', 2)
        if len(parts) < 3:
            return []

        frontmatter = yaml.load(parts[1])
        return frontmatter.get('dependencies', [])
```

**detect_cycles (DFS)**:
```python
def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]] | None:
    """Detect circular dependencies using DFS with coloring."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {wp: WHITE for wp in graph}
    cycles = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbor in graph.get(node, []):
            if color.get(neighbor, WHITE) == GRAY:
                # Back edge - cycle found
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color.get(neighbor, WHITE) == WHITE:
                dfs(neighbor, path)

        path.pop()
        color[node] = BLACK

    for wp in graph:
        if color[wp] == WHITE:
            dfs(wp, [])

    return cycles if cycles else None
```

**Parallel?**: No (implements all functions sequentially)

**Notes**: Follow existing Spec Kitty patterns (pathlib for paths, type hints, docstrings)

---

### Subtask T007 – Verify test coverage

**Purpose**: Ensure dependency_graph.py has >90% test coverage.

**Steps**:
1. Run pytest with coverage: `pytest tests/specify_cli/test_dependency_graph.py --cov=src/specify_cli/core/dependency_graph.py --cov-report=term-missing`
2. Review coverage report, identify untested lines
3. Add tests for uncovered branches (error paths, edge cases)
4. Re-run until coverage >90%

**Files**: N/A (validation step)

**Success**: Coverage report shows >90% for dependency_graph.py

---

## Test Strategy

**All tests in**: `tests/specify_cli/test_dependency_graph.py`

**Test execution**:
```bash
# Run from current worktree (where new code lives)
pytest tests/specify_cli/test_dependency_graph.py -v
pytest tests/specify_cli/test_dependency_graph.py --cov=src/specify_cli/core/dependency_graph.py --cov-report=term-missing
```

**Expected initial state**: All tests FAIL (module doesn't exist yet)
**After T006**: All tests PASS

**Note**: Do NOT cd to main repo - tests must run against code in this worktree.

**Test categories**:
- Parsing tests (T001): 5 test cases
- Graph building tests (T002): 5 test cases
- Cycle detection tests (T003): 5 test cases
- Validation tests (T004): 5 test cases
- Dependent lookup tests (T005): 4 test cases

**Total**: ~24 unit tests for dependency_graph.py

---

## Risks & Mitigations

**Risk 1: Cycle detection algorithm incorrect**
- Impact: Invalid dependency graphs allowed → runtime errors during implement
- Mitigation: Comprehensive test cases covering all graph topologies, reference DFS algorithm from data-model.md

**Risk 2: Frontmatter parsing inconsistent with existing code**
- Impact: Can't parse WP files → dependency tracking broken
- Mitigation: Use same ruamel.yaml approach as existing frontmatter.py module, test with real WP file examples

**Risk 3: Performance degradation with large graphs**
- Impact: Slow cycle detection for features with many WPs
- Mitigation: DFS is O(V+E), test with 50 WPs, verify <500ms constraint

---

## Definition of Done Checklist

- [ ] Test file created: tests/specify_cli/test_dependency_graph.py
- [ ] All unit tests written (T001-T005) - tests FAIL initially
- [ ] Module created: src/specify_cli/core/dependency_graph.py
- [ ] All functions implemented with type hints
- [ ] All tests PASS
- [ ] Test coverage >90% verified
- [ ] Code follows Spec Kitty conventions (pathlib, docstrings)

---

## Review Guidance

**Reviewers should verify**:
1. Tests were written FIRST (check git history - test file committed before implementation)
2. Test coverage is comprehensive (no obvious edge cases missing)
3. Cycle detection algorithm matches data-model.md specification (DFS with coloring)
4. Error messages are clear and actionable
5. Type hints present for all public functions

**Key Acceptance Checkpoint**: Run tests, verify 100% pass with >90% coverage.

---

## Activity Log

- 2026-01-07T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

Move this WP between lanes using:
```bash
spec-kitty agent tasks move-task WP01 --to <lane>
```

Or edit the `lane:` field in frontmatter directly.
- 2026-01-08T09:07:58Z – agent – lane=doing – Started implementation via workflow command
- 2026-01-08T09:20:16Z – unknown – lane=for_review – All tests passing (25/25). Module complete with comprehensive docstrings and type hints. TDD approach validated - tests written first, implementation made them pass.
- 2026-01-08T09:23:53Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:27:51Z – unknown – lane=for_review – Review feedback addressed: (1) Now using FrontmatterManager.read() for consistent parsing (UTF-8-sig BOM, proper --- detection). (2) Validates filename WP ID matches frontmatter work_package_id (frontmatter is canonical). All 25 tests still PASS.
- 2026-01-08T09:28:02Z – unknown – lane=for_review – Review feedback addressed: (1) Now using FrontmatterManager.read() instead of custom YAML parsing - ensures UTF-8-sig BOM handling, proper closing --- detection, consistent configuration. (2) Validates filename WP ID matches frontmatter work_package_id - prevents silent graph corruption from misnamed files. All 25 tests still PASS after fixes.
- 2026-01-08T09:35:45Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:55:42Z – unknown – lane=for_review – Ready for review
- 2026-01-08T09:56:04Z – agent – lane=doing – Started review via workflow command
- 2026-01-08T09:57:02Z – unknown – lane=done – Review passed. Implementation meets all requirements: (1) All 25 tests passing with comprehensive coverage, (2) TDD approach validated - tests written first, (3) Proper type hints and docstrings throughout, (4) Uses FrontmatterManager for consistent parsing, (5) DFS cycle detection correctly implemented per spec, (6) All edge cases handled properly. Code quality is excellent, ready for merge.

---
work_package_id: WP10
title: "Architectural Dependency Tests (PyTestArch)"
lane: planned
dependencies: [WP03]
requirement_refs:
- FR-018
- ADR 2026-03-27-1
planning_base_branch: feature/agent-profile-implementation
merge_target_branch: feature/agent-profile-implementation
branch_strategy: Planning artifacts for this feature were generated on feature/agent-profile-implementation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/agent-profile-implementation unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
phase: Phase 1 - New API
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-27T06:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt added during /spec-kitty.analyze architectural review
---

# Work Package Prompt: WP10 -- Architectural Dependency Tests (PyTestArch)

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`**

*[This section is empty initially.]*

---

## Objectives & Success Criteria

1. `pytestarch` added as dev dependency in `pyproject.toml`
2. `tests/architectural/conftest.py` provides session-scoped `evaluable` and `landscape` fixtures
3. `tests/architectural/test_layer_rules.py` encodes all 2.x package boundary invariants
4. All tests pass on current codebase (no pre-existing violations)
5. Tests are marked `@pytest.mark.architectural` for CI filtering
6. ADR `2026-03-27-1-pytestarch-architectural-dependency-testing.md` committed

**Success gate**: `pytest tests/architectural/ -v` passes. Introducing `from specify_cli import X` into any `src/doctrine/` file causes test failure.

## Context & Constraints

- **ADR**: `architecture/2.x/adr/2026-03-27-1-pytestarch-architectural-dependency-testing.md`
- **2.x landscape**: `architecture/2.x/00_landscape/README.md`
- **Dependency chain**: kernel (root) <- doctrine <- constitution <- specify_cli
- **Special case**: constitution may import `specify_cli.runtime` (not other specify_cli submodules)
- **PyTestArch**: v4.0.1, AST-based, session-scoped evaluable graph

## Branch Strategy

- **Strategy**: workspace-per-WP
- **Planning base branch**: feature/agent-profile-implementation
- **Merge target branch**: feature/agent-profile-implementation

**Implementation command**: `spec-kitty implement WP10 --base WP03`

(Depends on WP03 because `ConstitutionTemplateResolver` must exist for the tests to pass — it validates that resolve methods are in constitution, not doctrine.)

## Subtasks & Detailed Guidance

### Subtask T044 -- Add pytestarch dev dependency

- **Purpose**: Make PyTestArch available in the test environment.
- **Steps**:
  1. Add `pytestarch>=4.0.0` to the `[project.optional-dependencies] test` section in `pyproject.toml`
  2. Run `pip install -e ".[test]"` to verify installation
  3. Verify: `python -c "from pytestarch import get_evaluable_architecture; print('OK')"`
- **Files**: `pyproject.toml`

### Subtask T045 -- Create test fixtures

- **Purpose**: Session-scoped fixtures for evaluable architecture and layer definitions.
- **Steps**:
  1. Create `tests/architectural/__init__.py` (empty)
  2. Create `tests/architectural/conftest.py`:
     ```python
     """Architectural dependency test fixtures."""
     from __future__ import annotations

     from pathlib import Path

     import pytest
     from pytestarch import LayeredArchitecture, get_evaluable_architecture

     SRC = Path(__file__).resolve().parents[2] / "src"
     ROOT = SRC.parent


     @pytest.fixture(scope="session")
     def evaluable():
         """Session-scoped evaluable architecture for all src/ packages."""
         return get_evaluable_architecture(
             root_path=str(ROOT),
             module_path=str(SRC),
             exclude_external_libraries=True,
         )


     @pytest.fixture(scope="session")
     def landscape():
         """2.x C4 landscape: kernel <- doctrine <- constitution <- specify_cli."""
         return (
             LayeredArchitecture()
             .layer("kernel")
             .containing_modules("kernel")
             .layer("doctrine")
             .containing_modules("doctrine")
             .layer("constitution")
             .containing_modules("constitution")
             .layer("specify_cli")
             .containing_modules("specify_cli")
         )
     ```
  3. **Note**: The `evaluable` fixture parses all AST in `src/` once per session. This includes lazy imports inside method bodies — intentional.
- **Files**: `tests/architectural/__init__.py` (new), `tests/architectural/conftest.py` (new)

### Subtask T046 -- Encode layer invariant tests

- **Purpose**: The core architectural rules as executable tests.
- **Steps**:
  1. Create `tests/architectural/test_layer_rules.py`:
     ```python
     """2.x package boundary invariants.

     These tests enforce the dependency direction documented in
     architecture/2.x/00_landscape/README.md:

         kernel (root) <- doctrine <- constitution <- specify_cli

     A violation here means a package imports from a package it should not.
     See ADR 2026-03-27-1 for rationale.
     """
     from __future__ import annotations

     import pytest
     from pytestarch import LayerRule, Rule

     pytestmark = pytest.mark.architectural


     # --- Invariant 1: kernel is the true root (zero outgoing deps) ---

     class TestKernelIsolation:
         """kernel must not import from any other landscape container."""

         def test_kernel_does_not_import_doctrine(self, evaluable, landscape):
             (LayerRule()
              .based_on(landscape)
              .layers_that().are_named("kernel")
              .should_not()
              .access_layers_that().are_named("doctrine")
              ).assert_applies(evaluable)

         def test_kernel_does_not_import_constitution(self, evaluable, landscape):
             (LayerRule()
              .based_on(landscape)
              .layers_that().are_named("kernel")
              .should_not()
              .access_layers_that().are_named("constitution")
              ).assert_applies(evaluable)

         def test_kernel_does_not_import_specify_cli(self, evaluable, landscape):
             (LayerRule()
              .based_on(landscape)
              .layers_that().are_named("kernel")
              .should_not()
              .access_layers_that().are_named("specify_cli")
              ).assert_applies(evaluable)


     # --- Invariant 2: doctrine depends only on kernel ---

     class TestDoctrineIsolation:
         """doctrine must not import from specify_cli or constitution."""

         def test_doctrine_does_not_import_specify_cli(self, evaluable, landscape):
             (LayerRule()
              .based_on(landscape)
              .layers_that().are_named("doctrine")
              .should_not()
              .access_layers_that().are_named("specify_cli")
              ).assert_applies(evaluable)

         def test_doctrine_does_not_import_constitution(self, evaluable, landscape):
             (LayerRule()
              .based_on(landscape)
              .layers_that().are_named("doctrine")
              .should_not()
              .access_layers_that().are_named("constitution")
              ).assert_applies(evaluable)


     # --- Invariant 3: constitution boundary ---

     class TestConstitutionBoundary:
         """constitution may import doctrine + kernel + specify_cli.runtime only."""

         def test_constitution_does_not_import_specify_cli_non_runtime(self, evaluable):
             (Rule()
              .modules_that().are_sub_modules_of("constitution")
              .should_not()
              .import_modules_that().have_name_matching(
                  r"specify_cli\.(?!runtime).*"
              )
              ).assert_applies(evaluable)
     ```
  2. **Register the marker** in `pyproject.toml` under `[tool.pytest.ini_options]`:
     ```toml
     markers = [
         "architectural: marks tests as architectural boundary checks (run with '-m architectural')",
     ]
     ```
     (Append to existing markers list if present.)
- **Files**: `tests/architectural/test_layer_rules.py` (new), `pyproject.toml`

### Subtask T047 -- Validate and smoke test

- **Purpose**: Confirm the tests pass on current codebase and catch intentional violations.
- **Steps**:
  1. Run: `pytest tests/architectural/ -v`
  2. All tests should pass (no pre-existing violations after AR-1 fix in WP03)
  3. **Negative test** (manual, do not commit): temporarily add `from specify_cli import something` to `src/doctrine/missions/repository.py`, re-run tests, confirm `test_doctrine_does_not_import_specify_cli` fails. Remove the line.
  4. If any pre-existing violations are found, document them and either fix or add explicit exclusions with comments explaining why.
- **Files**: None (validation only)

## Test Strategy

```bash
# Run architectural tests
pytest tests/architectural/ -v

# Run with marker filter (as CI would)
pytest -m architectural -v

# Verify negative case (do NOT commit)
echo "from specify_cli import cli" >> src/doctrine/missions/repository.py
pytest tests/architectural/test_layer_rules.py::TestDoctrineIsolation -v
# Expected: FAIL
git checkout src/doctrine/missions/repository.py
```

## Risks & Mitigations

1. **Pre-existing violations**: The current codebase may have boundary violations we haven't found. T047 serves as the discovery step. Any found violations are fixed or explicitly excluded with justification.
2. **AST parse performance**: Session-scoped fixture runs once. If slow (>5s), add `level_limit=3` to constrain depth.
3. **Regex for constitution exception**: The `(?!runtime)` negative lookahead in the constitution test may need tuning if legitimate `specify_cli` imports beyond `runtime` are added in future. Document the pattern.

## Review Guidance

- Verify all 3 invariant classes are present and match the 2.x landscape
- Verify the constitution exception correctly permits `specify_cli.runtime` imports
- Verify the `architectural` marker is registered
- Verify the session fixture scans `src/` not the whole repo
- Verify the ADR is committed alongside the tests

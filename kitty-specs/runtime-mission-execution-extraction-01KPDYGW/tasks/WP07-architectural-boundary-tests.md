---
work_package_id: WP07
title: Architectural Boundary Tests
dependencies:
- WP06
requirement_refs:
- FR-007
- FR-008
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "805151"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/conftest.py
- tests/architectural/test_layer_rules.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

Do not begin implementation until the profile is active.

---

## Objective

Extend the existing pytestarch architectural test suite to enforce the `runtime` package boundary. After this WP, CI will fail any PR that adds a forbidden import into `runtime` (Rich, Typer, or `specify_cli.cli.*`) or imports from `runtime` into a non-CLI package.

---

## Context

**Read before starting**:
- `tests/architectural/test_layer_rules.py` — current layer definitions and rule structure
- `tests/architectural/conftest.py` — the `landscape` fixture that builds the pytestarch module graph
- `architecture/2.x/05_ownership_manifest.yaml` → `runtime_mission_execution.dependency_rules` — the authoritative list of allowed/forbidden edges

**Current `_DEFINED_LAYERS`** (from the source file):
```python
_DEFINED_LAYERS: frozenset[str] = frozenset(
    ["kernel", "doctrine", "charter", "specify_cli"]
)
```

**WP02 temporary exclusion**: WP02 added `runtime` to `_EXCLUDED_FROM_LAYER_ENFORCEMENT`. This WP removes that exclusion and moves `runtime` into `_DEFINED_LAYERS` properly.

**Dependency rules from ownership manifest**:
```yaml
dependency_rules:
  may_call:
    - charter_governance
    - doctrine
    - lifecycle_status
    - glossary
  may_be_called_by:
    - cli_shell
```

Translated to pytestarch assertions:
- `runtime` must NOT import from `specify_cli.cli` (cli_shell boundary)
- `runtime` must NOT import from `rich` or `typer` (presentation purity)
- Only `specify_cli` layer may import from `runtime` (may_be_called_by: cli_shell)
- `runtime` MAY import from `charter`, `doctrine`, `specify_cli.status`, `specify_cli.glossary` (may_call)

---

## Subtask T027 — Extend `conftest.py` Landscape Fixture

**Purpose**: Register `runtime` as a top-level module in the pytestarch landscape so it participates in layer-boundary analysis.

**Steps**:

1. Read `tests/architectural/conftest.py` in full. Locate the `landscape` fixture (likely a `@pytest.fixture` that calls `get_evaluated_modules()` or similar pytestarch API).

2. Add `runtime` to the module list in the same way that `kernel`, `doctrine`, `charter`, `specify_cli` are registered. The exact API depends on the pytestarch version in use — follow the existing pattern exactly.

   Example (if the fixture lists packages by name):
   ```python
   @pytest.fixture(scope="session")
   def landscape():
       return get_evaluated_modules(
           path=str(SRC_DIR),
           modules=["kernel", "doctrine", "charter", "specify_cli", "runtime"],  # add runtime
       )
   ```

3. Remove `runtime` from `_EXCLUDED_FROM_LAYER_ENFORCEMENT` in `test_layer_rules.py` (the temporary entry added in WP02).

**Files touched**: `tests/architectural/conftest.py`, `tests/architectural/test_layer_rules.py` (removal of temporary exclusion)

**Validation**: `pytest tests/architectural/test_layer_rules.py::TestLayerCoverage::test_no_unregistered_src_packages -v` still passes (runtime now registered, exclusion removed).

---

## Subtask T028 — Add `runtime` to `_DEFINED_LAYERS` + `TestRuntimeBoundary`

**Purpose**: Add the runtime layer definition and the three boundary assertions to `test_layer_rules.py`.

**Steps**:

1. Add `"runtime"` to `_DEFINED_LAYERS`:
   ```python
   _DEFINED_LAYERS: frozenset[str] = frozenset(
       ["kernel", "doctrine", "charter", "specify_cli", "runtime"]  # add runtime
   )
   ```

2. Add a new `TestRuntimeBoundary` test class after the existing test classes:

   ```python
   class TestRuntimeBoundary:
       """Enforce the runtime dependency boundary (FR-007, FR-008, C-009).

       Rules from architecture/2.x/05_ownership_manifest.yaml:
         - runtime.may_call: charter_governance, doctrine, lifecycle_status, glossary
         - runtime.may_be_called_by: cli_shell (specify_cli only)
         - runtime must NOT import: specify_cli.cli.*, rich, typer
       """

       def test_runtime_does_not_import_from_cli_shell(self, landscape: ModuleTree) -> None:
           """Runtime must not reach into the CLI command layer."""
           (
               LayerRule()
               .modules_that()
               .are_named("runtime")
               .should_not()
               .import_modules_that()
               .are_named("specify_cli.cli")
               .check(landscape)
           )

       def test_runtime_does_not_import_rich_or_typer(self, landscape: ModuleTree) -> None:
           """Runtime must not import presentation libraries directly (PresentationSink routes output)."""
           for lib in ("rich", "typer"):
               (
                   LayerRule()
                   .modules_that()
                   .are_named("runtime")
                   .should_not()
                   .import_modules_that()
                   .are_named(lib)
                   .check(landscape)
               )

       def test_only_specify_cli_imports_runtime(self, landscape: ModuleTree) -> None:
           """Only the CLI shell layer (specify_cli) may depend on runtime."""
           (
               LayerRule()
               .modules_that()
               .are_not_named("specify_cli")
               .should_not()
               .import_modules_that()
               .are_named("runtime")
               .check(landscape)
           )
   ```

   Adjust the pytestarch API calls to match the version and idioms already in use in `test_layer_rules.py`. Do not introduce new patterns if existing ones work.

**Files touched**: `tests/architectural/test_layer_rules.py`

**Validation**: `pytest tests/architectural/test_layer_rules.py::TestRuntimeBoundary -v` — must pass with zero failures.

---

## Subtask T029 — Run Full Architectural Tests + Fix Violations

**Purpose**: Run the complete architectural test suite. If any of the new rules fail, locate the import violation and fix it (either in `src/runtime/` or by adjusting the rule if it's a false positive).

**Steps**:

1. Run:
   ```bash
   pytest tests/architectural/ -v --tb=short
   ```

2. For each failure:
   - **If `TestRuntimeBoundary` failure**: the violation is in `src/runtime/`. Find the offending import with `rg "from rich|from typer|from specify_cli.cli" src/runtime/`. Remove or route through `PresentationSink`.
   - **If `TestLayerCoverage` failure**: a new top-level package was added without registration. Add it to `_DEFINED_LAYERS` or `_EXCLUDED_FROM_LAYER_ENFORCEMENT` with a comment.
   - **If other tests regress**: investigate whether the WP02–WP06 changes introduced unexpected imports.

3. Re-run until all tests pass:
   ```bash
   pytest tests/architectural/ -v
   ```

**Files touched**: Possibly `src/runtime/**` (to remove forbidden imports), `tests/architectural/test_layer_rules.py` (if rule needs refinement)

**Validation**: `pytest tests/architectural/ -v` exits 0 with all tests green.

**NFR-005 timing check**: Record the wall-clock runtime in the PR description:
```bash
time pytest tests/architectural/ -v
```
Flag in the PR if total time exceeds 5 seconds (NFR-005 target). No automated assertion needed — manual gate at review time.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP07 --agent claude`.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] `runtime` removed from `_EXCLUDED_FROM_LAYER_ENFORCEMENT`; added to `_DEFINED_LAYERS`
- [ ] `runtime` added to the `landscape` fixture in `conftest.py`
- [ ] `TestRuntimeBoundary` class exists with 3 assertions (no cli shell import, no rich/typer import, only specify_cli may import runtime)
- [ ] `pytest tests/architectural/ -v` exits 0 with zero failures

---

## Reviewer Guidance

- Confirm `_EXCLUDED_FROM_LAYER_ENFORCEMENT` no longer contains `"runtime"`
- Confirm `_DEFINED_LAYERS` contains `"runtime"`
- Run `pytest tests/architectural/ -v` and paste the passing output in the PR
- Confirm `TestRuntimeBoundary` has all 3 tests (not just 2)

## Activity Log

- 2026-04-23T09:06:05Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=805151 – Started implementation via action command
- 2026-04-23T09:09:52Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=805151 – Runtime boundary tests added; all 12 architectural layer-rule tests pass in 2.04s (NFR-005 met). runtime moved from _EXCLUDED to _DEFINED_LAYERS, TestRuntimeBoundary added with 4 assertions.
- 2026-04-23T09:10:24Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=805151 – Approved (orchestrator): 12 architectural tests pass in 2.14s (NFR-005 ✓), runtime in _DEFINED_LAYERS, TestRuntimeBoundary 4 assertions green, no forbidden imports detected

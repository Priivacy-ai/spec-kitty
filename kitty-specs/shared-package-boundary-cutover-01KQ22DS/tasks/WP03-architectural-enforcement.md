---
work_package_id: WP03
title: Architectural Enforcement of the Runtime Boundary
dependencies:
- WP02
requirement_refs:
- FR-011
- NFR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
history:
- at: '2026-04-25T10:31:00+00:00'
  actor: planner
  event: created
authoritative_surface: tests/architectural/test_shared_package_boundary.py
execution_mode: code_change
owned_files:
- tests/architectural/test_shared_package_boundary.py
- tests/architectural/test_pyproject_shape.py
tags: []
---

# WP03 — Architectural Enforcement of the Runtime Boundary

## Objective

Make the cutover constraints (C-001, C-002, C-005) mechanically enforced so any
future PR that re-introduces the hybrid pattern fails CI immediately with a
clear message naming the offending file and the rule it violates. Use the
existing `pytestarch` infrastructure per ADR 2026-03-27-1.

## Context

ADR 2026-03-27-1 established `pytestarch` as the architectural-rule layer.
Existing rules live in `tests/architectural/test_layer_rules.py`. This WP adds
a sibling test module focused on the shared-package boundary, plus a
`pyproject.toml` shape assertion module.

The rules to enforce:

| Rule | Constraint | Violation example |
|------|-----------|-------------------|
| R1 | C-001: no production module under `src/` may import `spec_kitty_runtime` (top-level, sub-module, lazy). | `from spec_kitty_runtime.engine import _read_snapshot` |
| R2 | C-002: no production module may import `specify_cli.spec_kitty_events.*`. | `from specify_cli.spec_kitty_events.models import Event` |
| R3 | C-003: `specify_cli.tracker` MUST NOT re-export tracker public symbols. | `from spec_kitty_tracker import OwnershipMode` followed by `__all__ = ['OwnershipMode']` in `specify_cli/tracker/__init__.py`. |
| R4 | C-004: `pyproject.toml` `[project.dependencies]` MUST NOT pin events / tracker exactly (`==X.Y.Z`). | `"spec-kitty-events==4.0.0"` |
| R5 | C-005: `[tool.uv.sources]` MUST NOT contain a `path` or `editable` entry for `spec-kitty-events` or `spec-kitty-tracker`. | `spec-kitty-events = { path = "../spec-kitty-events", editable = true }` |
| R6 | FR-006: `pyproject.toml` `[project.dependencies]` MUST NOT list `spec-kitty-runtime`. | `"spec-kitty-runtime>=0.4"` |

R1, R2, R3 live in `test_shared_package_boundary.py` (pytestarch). R4, R5, R6
live in `test_pyproject_shape.py` (TOML shape assertions).

NFR-006 caps the runtime of these tests at ≤30 seconds in the fast / unit gate.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: lane A (depends on WP02).

## Implementation

### Subtask T014 — Pytestarch rule: no `spec_kitty_runtime` production imports [P]

**Purpose**: Lock C-001 with an AST-based rule that catches lazy imports too
(per the ADR's rationale).

**Steps**:

1. Create `tests/architectural/test_shared_package_boundary.py`. Use the
   existing test infra patterns from `test_layer_rules.py` (LayeredArchitecture,
   LayerRule, the existing `landscape` conftest fixture).

2. Define a rule:
   ```python
   def test_no_production_imports_of_spec_kitty_runtime(landscape):
       # All modules under src/specify_cli, src/charter, src/doctrine, src/kernel
       # MUST NOT import any module starting with "spec_kitty_runtime".
       rule = (
           LayerRule()
           .layers(landscape)
           .layer("production")
           .should_not()
           .be_imported_by_anything_that_imports("spec_kitty_runtime")
       )
       # OR (whichever pytestarch idiom matches the existing repo style)
       # — see test_layer_rules.py for the matching invocation pattern.
       rule.assert_applies()
   ```

   The pytestarch fluent API may need adjusting to match the repo's existing
   conventions. Consult `tests/architectural/test_layer_rules.py` and the
   `landscape` fixture in `tests/architectural/conftest.py` for the canonical
   invocation pattern. Add a `production` layer if not already present (it
   covers `src/specify_cli`, `src/charter`, `src/doctrine`, `src/kernel`).

3. Add an injection-test sibling at the bottom of the file: a parametrized
   test that synthetically injects a `from spec_kitty_runtime import X` import
   into a temporary module file and asserts the rule fails. Use `tmp_path` and
   `pytestarch`'s ability to scan a custom path. This proves the rule is
   real, not a no-op.

**Files**: `tests/architectural/test_shared_package_boundary.py`.

**Validation**:
- The rule passes on the post-WP02 tree.
- The injection test fails when the injection is present and passes when it
  isn't.
- Test runtime ≤ 10 seconds.

### Subtask T015 — Pytestarch rule: no vendored events imports + no tracker re-export [P]

**Purpose**: Lock C-002 (vendored events) and C-003 (tracker re-export).

**Steps**:

1. Add to `tests/architectural/test_shared_package_boundary.py`:

   ```python
   def test_no_production_imports_of_vendored_events(landscape):
       # No production module may import specify_cli.spec_kitty_events.*
       # (the vendored copy that WP05 deletes).
       rule = ...  # pytestarch idiom
       rule.assert_applies()


   def test_specify_cli_tracker_does_not_reexport_tracker_public_surface():
       # specify_cli.tracker.__init__ must NOT include any tracker public
       # symbols in __all__.
       import specify_cli.tracker as cli_tracker
       cli_tracker_all = getattr(cli_tracker, "__all__", [])
       # Sample of tracker public symbols (kept in sync with
       # contracts/tracker_consumer_surface.md):
       tracker_public = {
           "FieldOwner", "OwnershipMode", "OwnershipPolicy", "SyncEngine",
           "ExternalRef",
       }
       overlap = set(cli_tracker_all) & tracker_public
       assert not overlap, (
           f"specify_cli.tracker re-exports tracker public symbols: {overlap}. "
           "Per C-003, the CLI-internal tracker module must not re-export the "
           "public PyPI tracker surface. Use direct `from spec_kitty_tracker "
           "import X` at the call site instead."
       )
   ```

2. The vendored-events rule is the same pytestarch idiom as T014, with the
   import-target string changed to `specify_cli.spec_kitty_events`.

3. Note: WP05 deletes `src/specify_cli/spec_kitty_events/`. Until WP05 lands,
   this rule has the wrinkle that `specify_cli.spec_kitty_events.*`
   self-references inside the vendored tree itself are still present. The rule
   MUST scope to "production modules outside the vendored tree" for the
   pre-WP05 window. Comment this in the test. After WP05 lands (and as part of
   that WP's validation), the scope simplifies to "all production modules"
   because the vendored tree is gone.

**Files**: `tests/architectural/test_shared_package_boundary.py` (extended).

**Validation**:
- Both new rules pass.
- The vendored-events rule's scope comment correctly tracks WP05's status.

### Subtask T016 — `pyproject.toml` shape assertions [P]

**Purpose**: Lock C-004, C-005, FR-006 with TOML-shape assertions independent of
import-graph rules.

**Steps**:

1. Create `tests/architectural/test_pyproject_shape.py`:

   ```python
   from pathlib import Path
   import tomllib

   import pytest

   pytestmark = pytest.mark.architectural

   PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


   def _load_pyproject() -> dict:
       return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


   def test_pyproject_does_not_list_spec_kitty_runtime():
       data = _load_pyproject()
       deps = data["project"]["dependencies"]
       offending = [d for d in deps if d.startswith("spec-kitty-runtime")]
       assert not offending, (
           f"pyproject.toml lists spec-kitty-runtime: {offending}. "
           "Per FR-006, the CLI must not depend on the retired runtime PyPI package."
       )


   def test_pyproject_uses_compatible_ranges_for_shared_packages():
       data = _load_pyproject()
       deps = data["project"]["dependencies"]
       for prefix in ("spec-kitty-events", "spec-kitty-tracker"):
           matching = [d for d in deps if d.startswith(prefix)]
           assert matching, f"pyproject.toml does not list {prefix}"
           for entry in matching:
               assert "==" not in entry, (
                   f"pyproject.toml pins {prefix} exactly: {entry}. "
                   "Per C-004, exact pins live in uv.lock; pyproject.toml "
                   "uses compatible ranges (>=X.Y,<X+1)."
               )


   def test_pyproject_has_no_committed_editable_sources_for_shared_packages():
       data = _load_pyproject()
       sources = data.get("tool", {}).get("uv", {}).get("sources", {})
       for pkg in ("spec-kitty-events", "spec-kitty-tracker", "spec-kitty-runtime"):
           assert pkg not in sources, (
               f"[tool.uv.sources] contains {pkg}: {sources[pkg]}. "
               "Per C-005, editable / path sources for shared packages must "
               "live in developer-only configuration, not committed pyproject.toml."
           )
   ```

2. The first two tests will FAIL on the pre-WP08 tree (events / tracker are
   exact-pinned today). That is **intended**: WP03 sets the gate; WP08 rewrites
   `pyproject.toml` to satisfy it.

   To avoid blocking lane A on lane B's WP08 work, gate these two tests with
   `@pytest.mark.skipif("not WP08_landed", ...)` style markers. The simplest
   pattern: read a flag file written by WP08's commit (`pyproject.toml`'s
   exact-pin status). Or: the test itself is added by WP03 but its assertions
   become live in WP08's scope.

   **Decision**: Write the assertions as no-ops with `pytest.xfail("WP08 lands the metadata cutover")` for the duration of WP03..WP07. WP08 removes the `xfail` markers as part of its own subtask T030. This keeps lane discipline clean.

3. The third test (no editable sources) IS satisfied today only if the existing
   `[tool.uv.sources]` editable entry for events is removed. WP08 owns that
   removal. Same `xfail` pattern.

**Files**: `tests/architectural/test_pyproject_shape.py`.

**Validation**:
- The file is importable and parses cleanly.
- Tests are `xfail`-marked (with reason "WP08 lands the metadata cutover") on
  the post-WP03 tree.
- After WP08 removes the `xfail`, the tests pass.

## Definition of Done

- [ ] All 3 subtasks complete with checkboxes ticked above (`mark-status` updates the per-WP checkboxes here as the WP advances).
- [ ] `tests/architectural/test_shared_package_boundary.py` exists and passes
  on the post-WP02 tree (T014, T015 rules live).
- [ ] Injection tests prove the rules catch real regressions.
- [ ] `tests/architectural/test_pyproject_shape.py` exists with `xfail`-marked
  tests for WP08 to activate.
- [ ] Total runtime of new architectural tests ≤ 30 seconds (NFR-006).

## Risks

- **Pytestarch lazy-import detection misses some patterns.** Mitigation:
  ADR 2026-03-27-1 documents AST-based detection; the injection test in T014
  proves the detection is real.
- **The vendored-events rule scope comment goes stale once WP05 lands.**
  Mitigation: WP05's reviewer guidance includes "delete the scope-comment
  caveat in `test_shared_package_boundary.py`."

## Reviewer guidance

- Verify the rules pass on the current tree.
- Verify the injection test plants a real import and the rule catches it.
- Verify NFR-006 (≤30s runtime).
- Verify `pyproject_shape` tests are `xfail`-marked appropriately.
- Verify the test module docstrings name the spec FR / constraint each rule
  enforces (so future readers know why the rule exists).

## Implementation command

```bash
spec-kitty agent action implement WP03 --agent <name> --mission shared-package-boundary-cutover-01KQ22DS
```

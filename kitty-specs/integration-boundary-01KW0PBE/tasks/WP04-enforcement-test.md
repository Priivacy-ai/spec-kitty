---
work_package_id: WP04
title: test_integration_boundary.py enforcement test
dependencies:
- WP03
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- C-008
- NFR-001
- NFR-002
tracker_refs: []
planning_base_branch: feat/integration-boundary
merge_target_branch: feat/integration-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/integration-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/integration-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
phase: Phase 4 - enforcement test
assignee: ''
agent: ''
shell_pid: '2341815'
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_integration_boundary.py
execution_mode: code_change
owned_files:
- tests/architectural/**
tags: []
---

# Work Package Prompt: WP04 – test_integration_boundary.py enforcement test

## Objective

Add `tests/architectural/test_integration_boundary.py` — an AST-based enforcement
test that permanently prevents any module in the CORE set from importing any module
in the INTEGRATION set, including lazy function-body imports and `if TYPE_CHECKING:`
block imports.

**This WP MUST be introduced only after WP01–WP03 have fixed all three leaks**, so
the test passes green from its first commit. Introducing it before that would leave
the CI permanently red.

---

## Prerequisites

WP03 must be merged first: all three leaks (Leak #1, #2 addressed, #3) must be
fully inverted. The only remaining CORE→INTEGRATION edge is the single allowlisted
Leak #2 (`readiness/coordinator.py → saas.rollout`), which this test explicitly
permits.

---

## Reference

Model the test on `tests/architectural/test_status_sync_boundary.py` — the approved
AST-scan idiom for this codebase (spec assumption 5). Read that file before
implementing.

---

## Subtasks

### T016 — Implement `_collect_imports` AST walker + main enforcement test

Create `tests/architectural/test_integration_boundary.py` with:

1. **Module-level constants**:
   ```python
   SRC = Path(__file__).parent.parent.parent / "src"

   CORE_PACKAGES = [
       SRC / "specify_cli" / "core",
       SRC / "specify_cli" / "status",
       SRC / "specify_cli" / "readiness",
       SRC / "specify_cli" / "invocation",
   ]

   INTEGRATION_PREFIXES = [
       "specify_cli.orchestrator_api",
       "specify_cli.sync",
       "specify_cli.tracker",
       "specify_cli.saas",
       "specify_cli.saas_client",
   ]
   ```

2. **`_collect_imports(source: str) -> list[str]`** helper that parses `source` with
   `ast.parse` and walks the AST, collecting the module string for every import node
   including:
   - `ast.Import` nodes (collect each alias's `name`)
   - `ast.ImportFrom` nodes (collect `node.module` where present)
   - All of the above whether they appear at module level, inside `if TYPE_CHECKING:`
     blocks, or inside function/method bodies (walk the full tree — do not restrict to
     module-level only).

3. **`test_no_core_imports_integration`** test function:
   - For every `.py` file found by `Path.rglob("*.py")` across all `CORE_PACKAGES`:
     - Parse the file with `_collect_imports`.
     - For each collected import, check if it starts with any prefix in
       `INTEGRATION_PREFIXES`.
     - If it does, check the allowlist (see T018). If not allowlisted, record a
       violation.
   - After scanning all files, assert no violations. On failure, produce a message
     that includes **at minimum three diagnostic fields** for each violation (NFR-002):
     - Violating source file (relative path from repo root)
     - Offending import path
     - Corrective action (e.g., "Route through the adapter/observer registry in
       status/adapters.py or invocation/adapters.py instead of importing directly.")

### T017 — Path-existence sub-test (C-008)

Add a test function `test_core_package_dirs_exist` that asserts every entry in
`CORE_PACKAGES` exists as a directory:

```python
@pytest.mark.architectural
def test_core_package_dirs_exist() -> None:
    missing = [p for p in CORE_PACKAGES if not p.is_dir()]
    assert not missing, (
        f"CORE_PACKAGES directories missing: {missing}. "
        "If a package was renamed, update CORE_PACKAGES in this test."
    )
```

This ensures the main enforcement test cannot pass vacuously if a CORE-set directory
is renamed (C-008).

### T018 — Allowlist with single Leak #2 entry + sanity sub-test (FR-003, FR-007)

1. **Allowlist constant** — a set of `(source_file_relative, import_prefix)` tuples,
   with exactly one entry:
   ```python
   ALLOWLIST: frozenset[tuple[str, str]] = frozenset({
       (
           "src/specify_cli/readiness/coordinator.py",
           "specify_cli.saas.rollout",
           # Rationale: saas/rollout.py acts as a shared-config module (shared-config v1).
           # is_saas_sync_enabled is a pure feature-flag read with no side effects; not a
           # structural SaaS dependency. Will be relocated to a core/kernel config module
           # in a follow-up mission. Exempted until that relocation lands.
       ),
   })
   ```
   (Represent as a 2-tuple in the frozenset; include the rationale as a comment.)

2. **`test_allowlist_cannot_be_bypassed`** sanity sub-test: invoke `_collect_imports`
   on a synthetic source string that contains a non-allowlisted INTEGRATION import
   (e.g., `"from specify_cli.sync.events import emit_mission_created"`), and assert
   the enforcement logic would catch it (i.e., it appears in the collected imports and
   is NOT in the allowlist). This proves the scanner is not silently skipping imports.
   No on-disk file needed — pass the string directly to `_collect_imports`.

### T019 — pytest.mark, timing budget, violation message format (NFR-001, NFR-002, C-008)

1. Decorate all test functions in the file with `@pytest.mark.architectural` (follow
   the marker registration in `pyproject.toml` / `conftest.py` for the
   `tests/architectural/` suite).

2. The full file must complete within the existing `tests/architectural/` 30 s budget
   (NFR-001). Use `Path.rglob` (not `os.walk`) for consistency with the reference
   test. Parse each file once and cache results if needed.

3. Every violation message MUST include:
   - `file`: the violating source file path (relative to repo root)
   - `import`: the offending import module string
   - `action`: the corrective action string
   Format example:
   ```
   CORE→INTEGRATION boundary violation:
     file:   src/specify_cli/core/mission_creation.py
     import: specify_cli.sync.events
     action: Route through the adapter/observer registry (status/adapters.py or
             invocation/adapters.py) instead of importing INTEGRATION modules directly.
   ```

---

## Acceptance Criteria

1. `pytest tests/architectural/test_integration_boundary.py` is green.
2. The test catches a synthetic violation created by injecting a non-allowlisted
   import string into `_collect_imports` (sanity sub-test passes).
3. All four CORE-set directories exist (path-existence sub-test passes).
4. Allowlist contains exactly one entry (`readiness/coordinator.py → saas.rollout`)
   with written rationale.
5. All test functions carry `@pytest.mark.architectural`.
6. `pytest tests/architectural/` completes within 30 s (NFR-001).
7. Violation messages contain ≥ 3 diagnostic fields (NFR-002).
8. `ruff check tests/architectural/test_integration_boundary.py` and `mypy`
   report zero new issues.

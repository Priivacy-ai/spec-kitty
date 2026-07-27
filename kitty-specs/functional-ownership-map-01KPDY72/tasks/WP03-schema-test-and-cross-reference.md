---
work_package_id: WP03
title: Schema Validation Test + Cross-reference
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-011
- NFR-002
- NFR-004
planning_base_branch: feature/module_ownership
merge_target_branch: feature/module_ownership
branch_strategy: Planning artifacts for this feature were generated on feature/module_ownership. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/module_ownership unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
shell_pid: "1022467"
history:
- at: '2026-04-18T04:31:57Z'
  event: created
  actor: claude
authoritative_surface: tests/architecture/
execution_mode: code_change
owned_files:
- tests/architecture/test_ownership_manifest_schema.py
- tests/architecture/__init__.py
- architecture/2.x/04_implementation_mapping/README.md
tags: []
agent: "claude"
---

# WP03 — Schema Validation Test + Cross-reference

## Objective

Close the remaining FR/NFR gaps:

1. Write `tests/architecture/test_ownership_manifest_schema.py` — a pytest module with all 9 data-model assertions that validates the YAML manifest is parseable, complete, and structurally correct (FR-011, NFR-002).
2. Edit `architecture/2.x/04_implementation_mapping/README.md` — add a prominent cross-link paragraph directing readers to the ownership map for slice-level questions (FR-007, acceptance scenario 7).

Both tasks are independent and can be done in parallel.

**Depends on WP02**: the schema test's assertion 7 checks that `charter_governance.shims == []`. If WP02 hasn't landed yet, the shim directory still exists, and this WP produces incorrect test state. Always start WP03 from the merged state of WP02.

## Context

- The 9 assertions are enumerated in `kitty-specs/functional-ownership-map-01KPDY72/data-model.md §4`.
- The manifest is at `architecture/2.x/05_ownership_manifest.yaml` (created by WP01).
- `architecture/2.x/04_implementation_mapping/README.md` already exists and has a `## Purpose` section near the top — the cross-link goes early in the document so readers see it immediately (FR-007: "links prominently to the ownership map").
- Use **PyYAML** (`import yaml`) in the test, not `ruamel.yaml`. PyYAML is already a project dependency; `ruamel.yaml` is for authoring. `yaml.safe_load()` is sufficient for reading and validation.
- `tests/architecture/` may not exist yet. Create it with an `__init__.py` if absent.

---

## Subtask T013 — Write the schema validation test (9 assertions)

**Purpose**: Implement `tests/architecture/test_ownership_manifest_schema.py` with exactly the 9 assertions from data-model §4. The test must run green after WP01+WP02 have landed and must complete in ≤1 s (NFR-002).

**Steps**:

1. Ensure `tests/architecture/` exists:
   ```bash
   mkdir -p tests/architecture
   touch tests/architecture/__init__.py
   ```

2. Create `tests/architecture/test_ownership_manifest_schema.py` with this structure:

   ```python
   """Schema validation for architecture/2.x/05_ownership_manifest.yaml.

   Asserts structural completeness per data-model.md §4.
   Runs in <1 s (NFR-002).
   """
   import time
   from pathlib import Path

   import pytest
   import yaml

   MANIFEST_PATH = Path(__file__).parents[2] / "architecture" / "2.x" / "05_ownership_manifest.yaml"

   REQUIRED_SLICE_KEYS = {
       "cli_shell",
       "charter_governance",
       "doctrine",
       "runtime_mission_execution",
       "glossary",
       "lifecycle_status",
       "orchestrator_sync_tracker_saas",
       "migration_versioning",
   }

   REQUIRED_ENTRY_FIELDS = {
       "canonical_package",
       "current_state",
       "adapter_responsibilities",
       "shims",
       "seams",
       "extraction_sequencing_notes",
   }

   SHIM_REQUIRED_FIELDS = {"path", "canonical_import", "removal_release"}


   @pytest.fixture(scope="module")
   def manifest() -> dict:
       """Load the manifest once for all tests in this module."""
       start = time.monotonic()
       data = yaml.safe_load(MANIFEST_PATH.read_text())
       elapsed = time.monotonic() - start
       if elapsed > 1.0:
           import warnings
           warnings.warn(f"Manifest load took {elapsed:.2f}s (NFR-002 target: ≤1 s)", UserWarning, stacklevel=2)
       return data
   ```

3. Write the 9 individual test functions (each corresponds to one assertion from data-model §4):

   **Assertion 1** — manifest file exists and parses:
   ```python
   def test_manifest_exists_and_parses(manifest):
       assert isinstance(manifest, dict), "Manifest must be a YAML mapping at top level"
   ```

   **Assertion 2** — exactly the 8 canonical slice keys, no extras, no missing:
   ```python
   def test_manifest_has_exactly_eight_canonical_keys(manifest):
       assert set(manifest.keys()) == REQUIRED_SLICE_KEYS
   ```

   **Assertion 3** — each slice entry has all required fields with correct types:
   ```python
   def test_each_slice_entry_has_required_fields(manifest):
       for key, entry in manifest.items():
           for field in REQUIRED_ENTRY_FIELDS:
               assert field in entry, f"Slice '{key}' missing required field '{field}'"
           assert isinstance(entry["canonical_package"], str) and entry["canonical_package"], \
               f"Slice '{key}': canonical_package must be a non-empty string"
           assert isinstance(entry["current_state"], list) and len(entry["current_state"]) > 0, \
               f"Slice '{key}': current_state must be a non-empty list"
           assert isinstance(entry["adapter_responsibilities"], list), \
               f"Slice '{key}': adapter_responsibilities must be a list"
           assert isinstance(entry["shims"], list), \
               f"Slice '{key}': shims must be a list"
           assert isinstance(entry["seams"], list), \
               f"Slice '{key}': seams must be a list"
           assert isinstance(entry["extraction_sequencing_notes"], str) and entry["extraction_sequencing_notes"], \
               f"Slice '{key}': extraction_sequencing_notes must be a non-empty string"
   ```

   **Assertion 4** — runtime slice has `dependency_rules` with both required sub-keys as lists:
   ```python
   def test_runtime_slice_has_dependency_rules(manifest):
       runtime = manifest["runtime_mission_execution"]
       assert "dependency_rules" in runtime, "runtime_mission_execution must have dependency_rules"
       dr = runtime["dependency_rules"]
       assert isinstance(dr, dict), "dependency_rules must be a mapping"
       assert "may_call" in dr and isinstance(dr["may_call"], list), \
           "dependency_rules.may_call must be a list"
       assert "may_be_called_by" in dr and isinstance(dr["may_be_called_by"], list), \
           "dependency_rules.may_be_called_by must be a list"
   ```

   **Assertion 5 + 6** — `dependency_rules` on runtime only; no other slice has it:
   ```python
   def test_only_runtime_slice_has_dependency_rules(manifest):
       for key, entry in manifest.items():
           if key == "runtime_mission_execution":
               continue
           assert "dependency_rules" not in entry, \
               f"Slice '{key}' must not have dependency_rules (runtime-only field)"
   ```

   **Assertion 7** — `charter_governance.shims` is an empty list:
   ```python
   def test_charter_governance_shims_is_empty(manifest):
       charter = manifest["charter_governance"]
       assert charter["shims"] == [], \
           "charter_governance.shims must be [] (shim deleted by Mission functional-ownership-map-01KPDY72)"
   ```

   **Assertion 8** — every value in `may_call` and `may_be_called_by` is a recognised slice key:
   ```python
   def test_dependency_rules_reference_known_slice_keys(manifest):
       dr = manifest["runtime_mission_execution"]["dependency_rules"]
       for direction in ("may_call", "may_be_called_by"):
           for ref in dr[direction]:
               assert ref in REQUIRED_SLICE_KEYS, \
                   f"dependency_rules.{direction} contains unknown slice key '{ref}'"
   ```

   **Assertion 6** — every `shims[].path` that is non-empty points to a directory/file that exists on disk (charter's list is empty, so this check trivially passes for it):
   ```python
   def test_shim_paths_exist_if_listed(manifest):
       """Every shim path listed in the manifest must exist on disk (data-model §4 assertion 6)."""
       repo_root = Path(__file__).parents[2]
       for key, entry in manifest.items():
           for shim in entry.get("shims", []):
               path_str = shim.get("path", "")
               if path_str:
                   assert (repo_root / path_str).exists(), (
                       f"Slice '{key}' shim path '{path_str}' does not exist in repo. "
                       "Either the shim was deleted without updating the manifest, "
                       "or the manifest lists a path that was never created."
                   )
   ```

   **Assertion 9** — test completes within 1 s (soft):
   ```python
   def test_validation_completes_within_one_second():
       """Soft timing check — emits a warning but does not fail if >1 s (NFR-002)."""
       start = time.monotonic()
       data = yaml.safe_load(MANIFEST_PATH.read_text())
       # Re-run all structural checks to measure full validation time
       assert set(data.keys()) == REQUIRED_SLICE_KEYS
       elapsed = time.monotonic() - start
       if elapsed > 1.0:
           import warnings
           warnings.warn(
               f"Manifest validation took {elapsed:.2f}s; NFR-002 target is ≤1 s on a baseline dev machine.",
               UserWarning,
               stacklevel=2,
           )
       # Soft: warn but never fail — hardware variation is outside our control
   ```

4. Verify the test file is importable:
   ```bash
   python -c "import tests.architecture.test_ownership_manifest_schema; print('Import OK')"
   ```

**Files**:
- `tests/architecture/__init__.py` (new, empty)
- `tests/architecture/test_ownership_manifest_schema.py` (new, ~130 lines)

**Validation**: File syntax-checks cleanly; `python -m py_compile tests/architecture/test_ownership_manifest_schema.py` exits 0.

---

## Subtask T014 — Edit `04_implementation_mapping/README.md` — add cross-link (FR-007)

**Purpose**: Ensure that readers navigating the architecture documentation are directed to the ownership map when they have slice-level questions (acceptance scenario 7).

**Steps**:

1. Open `architecture/2.x/04_implementation_mapping/README.md` and read its current structure. The document begins with a title + metadata table, then a `## Purpose` section.

2. Immediately after the `## Purpose` section heading (or after the first paragraph of Purpose), add a prominent cross-reference paragraph. Insert it before the first code/table content so that readers see it at the top of the meaningful document body:

   ```markdown
   > **Slice-level ownership** — For the authoritative record of which package owns each
   > functional slice, where it lives today, what adapter responsibilities remain in
   > `src/specify_cli/`, and how each slice sequences for extraction, see
   > **[05_ownership_map.md](../05_ownership_map.md)**.
   ```

   This should be a blockquote callout, not a plain paragraph, so it stands out visually.

3. Confirm the cross-link resolves correctly relative to `architecture/2.x/04_implementation_mapping/README.md`. The relative path `../05_ownership_map.md` resolves to `architecture/2.x/05_ownership_map.md`, which was created by WP01. ✓

**Files**: `architecture/2.x/04_implementation_mapping/README.md` (edited — one blockquote added).

**Validation**: The blockquote is present and the relative link path is correct. Open `04_implementation_mapping/README.md` and confirm the callout appears before the first implementation table.

---

## Subtask T015 — Run mypy + schema test; confirm all 9 assertions pass in ≤1 s (NFR-002)

**Purpose**: Verify the test module is type-correct (charter requires `mypy --strict`) and works end-to-end against the actual manifest created by WP01.

**Steps**:

1. Run `mypy --strict` on the new test file (charter requirement — U4):
   ```bash
   mypy --strict tests/architecture/test_ownership_manifest_schema.py 2>&1
   ```
   Expected: `Success: no issues found in 1 source file`. If type errors appear, fix them in T013's code (the test uses `yaml.safe_load()` which returns `Any`; add a `cast(dict, ...)` or type-ignore comment where necessary).

2. Run the schema test in verbose mode:
   ```bash
   python -m pytest tests/architecture/test_ownership_manifest_schema.py -v 2>&1
   ```

3. Expected output: **9 tests collected, 9 passed**, 0 failed:
   ```
   tests/architecture/test_ownership_manifest_schema.py::test_manifest_exists_and_parses PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_manifest_has_exactly_eight_canonical_keys PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_each_slice_entry_has_required_fields PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_runtime_slice_has_dependency_rules PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_only_runtime_slice_has_dependency_rules PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_shim_paths_exist_if_listed PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_charter_governance_shims_is_empty PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_dependency_rules_reference_known_slice_keys PASSED
   tests/architecture/test_ownership_manifest_schema.py::test_validation_completes_within_one_second PASSED
   =========== 9 passed in 0.12s ===========
   ```

4. If any test fails:
   - **`test_charter_governance_shims_is_empty` fails**: WP02 may not be merged yet, or the manifest was not updated with `shims: []`. Fix the manifest or confirm WP02 is landed.
   - **`test_shim_paths_exist_if_listed` fails**: A shim `path` listed in the manifest doesn't exist on disk — either the manifest references a planned (not-yet-created) shim path, or the path string has a typo. Fix the manifest entry.
   - **`test_manifest_has_exactly_eight_canonical_keys` fails**: A typo in the manifest's top-level keys.
   - **`test_dependency_rules_reference_known_slice_keys` fails**: A `may_call` or `may_be_called_by` value is not one of the 8 slice keys. Check for `kernel` or other non-slice entries — see WP01-T004 caution note.

5. Check that the test run time is ≤1 s (the test itself will warn if not, but NFR-002 is a soft requirement here).

**Validation**: `mypy --strict` clean; `pytest tests/architecture/ -v` exits 0 with **9 tests** passing.

---

## Subtask T016 — Verify `import specify_cli.charter` raises `ModuleNotFoundError` (NFR-004)

**Purpose**: Final end-to-end acceptance check confirming NFR-004 from the spec.

**Steps**:

1. Run:
   ```bash
   python -c "import specify_cli.charter" 2>&1
   ```
   Expected: `ModuleNotFoundError: No module named 'specify_cli.charter'`

2. Run:
   ```bash
   python -c "
   try:
       import specify_cli.charter
       print('FAIL: import should have raised ModuleNotFoundError')
   except ModuleNotFoundError as e:
       print(f'PASS: {e}')
   except Exception as e:
       print(f'UNEXPECTED: {type(e).__name__}: {e}')
   "
   ```
   Expected: `PASS: No module named 'specify_cli.charter'`

3. Also confirm the canonical import is unaffected:
   ```bash
   python -c "from charter import build_charter_context; print('Canonical import OK')"
   ```
   Expected: `Canonical import OK`

**Validation**: Both checks pass as expected.

---

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `spec-kitty agent action implement WP03 --agent <name>` via `lanes.json`.
- **Ordering requirement**: WP02 must be merged before WP03 starts (schema test asserts the charter shim is absent from disk and `charter_governance.shims == []`).

---

## Definition of Done

- [ ] `tests/architecture/__init__.py` exists (directory created).
- [ ] `tests/architecture/__init__.py` exists (directory initialized).
- [ ] `tests/architecture/test_ownership_manifest_schema.py` exists with all 9 test functions covering data-model §4 assertions 1–9 (including `test_shim_paths_exist_if_listed`).
- [ ] `mypy --strict tests/architecture/test_ownership_manifest_schema.py` exits 0.
- [ ] `pytest tests/architecture/test_ownership_manifest_schema.py -v` exits 0 with **9 tests** passing.
- [ ] Test run completes in ≤1 s (or emits a soft warning if marginally over on a slow machine).
- [ ] `architecture/2.x/04_implementation_mapping/README.md` contains the ownership-map cross-reference blockquote, positioned prominently before the first implementation table.
- [ ] `python -c "import specify_cli.charter"` raises `ModuleNotFoundError` (NFR-004 confirmed).
- [ ] `python -c "from charter import build_charter_context"` exits without error (canonical import intact).

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `tests/architecture/` directory doesn't exist | High (it's new) | Create `tests/architecture/__init__.py` at the start of T013 |
| PyYAML not importable | Very low | PyYAML is a project dependency; `import yaml` in the test matches existing test patterns |
| WP02 not yet merged when WP03 runs | Medium | Hard pre-condition: confirm `src/specify_cli/charter/` is gone before running T015 |
| Relative path `../05_ownership_map.md` resolves to wrong location | Low | Verify: `architecture/2.x/04_implementation_mapping/../05_ownership_map.md` = `architecture/2.x/05_ownership_map.md` ✓ |
| Assertion count mismatch (data-model lists 9 but test has fewer functions) | Low | Assertions 5+6 may be combined into one function; document explains this |

---

## Reviewer Guidance

- Confirm `tests/architecture/test_ownership_manifest_schema.py` exists and has ≥8 test functions covering the assertions in data-model §4.
- Run `pytest tests/architecture/ -v` and confirm it exits 0.
- Open `architecture/2.x/04_implementation_mapping/README.md` and confirm the ownership-map cross-reference blockquote is near the top (before any tables).
- Verify the T016 acceptance check output is documented (or run it manually).
- Confirm no other files are modified by this WP.

## Activity Log

- 2026-04-18T06:55:09Z – claude – shell_pid=1022467 – Started implementation via action command
- 2026-04-18T07:00:22Z – claude – shell_pid=1022467 – Ready for review: 9-assertion schema test passes in 0.72s, mypy --strict clean, README cross-link added before first table, NFR-004 confirmed in worktree context

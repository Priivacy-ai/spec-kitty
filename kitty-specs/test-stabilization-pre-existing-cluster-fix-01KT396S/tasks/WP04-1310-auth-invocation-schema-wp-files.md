---
work_package_id: WP04
title: '#1310 Residual: Auth, Invocation, Schema Version, WP Files'
dependencies: []
requirement_refs:
- FR-009
- FR-010
- FR-011
- FR-012
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
- T022
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: debugger-debbie
authoritative_surface: tests/auth/
execution_mode: code_change
owned_files:
- tests/auth/integration/test_refresh_through_transport.py
- tests/auth/conftest.py
- tests/specify_cli/invocation/**/*.py
- tests/specify_cli/migration/test_schema_version.py
- tests/specify_cli/status/test_wp_metadata.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load debugger-debbie
```

---

## Objective

Fix four independent sub-failures from the #1310 residual cluster:

1. **Auth transport exit code 2** — `test_refresh_through_transport` fails because the `sync status --check` CliRunner invocation exits with code 2 (Typer usage error) before reaching auth logic.
2. **Invocation JSON noise** — `test_do`, `test_profiles`, `test_record` fail because `logged_out_on_connected_teamspace` noise leaks into captured JSON output from a prior test.
3. **Schema-version wording drift** — `test_schema_version` fails because the error message assertion no longer matches the production string.
4. **WP file Pydantic validation** — `test_all_kitty_specs_wp_files_validate` fails because 6 WP JSON files in `kitty-specs/` don't conform to the current `WorkPackage` Pydantic model.

---

## Context

All four failures are test-isolation or content-drift issues, not production logic bugs. The fixes are:
- Add missing test fixture config (auth)
- Add a conftest teardown to reset global state (invocation)
- Update a string assertion or restore a message (schema version)
- Update 6 WP JSON files to the current schema (WP file validation)

**No new `SPEC_KITTY_TEST_MODE` bypasses** may be introduced. Fix the test fixtures — not production code.

---

## Subtasks

### T016 — Diagnose auth test exit code 2

**Steps**:

1. Run the failing test with full output:
   ```bash
   pytest tests/auth/integration/test_refresh_through_transport.py -v -s 2>&1 | head -80
   ```

2. Exit code 2 in Typer/Click means a usage error — the CLI command received invalid arguments or is missing a required config before the command body runs. The test invokes `sync status --check` via CliRunner.

3. Read `tests/auth/integration/test_refresh_through_transport.py` and `tests/auth/conftest.py` to understand what config/session state the test provides.

4. Look for:
   - Missing required CLI option (e.g., `--teamspace-id`, `--config-path`)
   - Missing required environment variable
   - Missing session file that `sync status` tries to read
   - CliRunner `mix_stderr=False` issues

5. Find the `sync status --check` command definition in `src/specify_cli/` to identify what it requires:
   ```bash
   grep -rn "sync.*status\|status.*check" src/specify_cli/ --include="*.py" | head -20
   ```

**Output**: Exact config item missing from the test fixture.

---

### T017 — Fix auth test fixture

**Steps**:

1. Based on T016, add the missing fixture setup in `tests/auth/integration/test_refresh_through_transport.py` or `tests/auth/conftest.py`.

2. Common fixes:
   - **Missing config file**: Create a minimal `config.yaml` in `tmp_path` and point the CliRunner env to it via `env={"SPEC_KITTY_CONFIG": str(config_path)}`.
   - **Missing session file**: The test already creates a `StoredSession` — check that the file is being written to the path the auth module reads from, and that the path is correctly injected.
   - **Missing teamspace context**: Add a minimal teamspace stub to the CliRunner `env`.

3. The fix must be in the test fixture only — do not change production code to skip validation.

4. Verify the test now reaches the auth refresh logic (the CliRunner should exit 0 or 1, not 2).

**Files**:
- `tests/auth/integration/test_refresh_through_transport.py`
- `tests/auth/conftest.py`

**Validation**: `pytest tests/auth/integration/test_refresh_through_transport.py -v` exits without code 2.

---

### T018 — Add autouse conftest teardown for invocation test noise

**Steps**:

1. Run the failing invocation tests to see the exact JSON parse failure:
   ```bash
   pytest tests/specify_cli/invocation/ -v -s 2>&1 | head -80
   ```

2. Find what `logged_out_on_connected_teamspace` is — likely a module-level or class-level boolean/function in the auth or teamspace module that gets set by a prior test.

3. Locate the setter:
   ```bash
   grep -rn "logged_out_on_connected_teamspace" src/ tests/ --include="*.py" | head -20
   ```

4. In `tests/specify_cli/invocation/conftest.py` (create if missing), add an `autouse` fixture that resets this condition after each test:
   ```python
   import pytest

   @pytest.fixture(autouse=True)
   def reset_teamspace_auth_state():
       yield
       # Reset the condition so it doesn't leak into the next test
       from specify_cli.<module> import set_logged_out_on_connected_teamspace
       set_logged_out_on_connected_teamspace(False)  # or None, depending on type
   ```

5. If there is no setter function, use `monkeypatch` in the fixture or patch the module attribute directly.

6. Do not add `SPEC_KITTY_TEST_MODE` bypasses.

**Files**:
- `tests/specify_cli/invocation/conftest.py` (create or update)

**Validation**: `pytest tests/specify_cli/invocation/ -v` passes with clean JSON output.

---

### T019 — Fix schema-version error message assertion

**Steps**:

1. Run the failing test:
   ```bash
   pytest tests/specify_cli/migration/test_schema_version.py -v -s 2>&1
   ```

2. The output will show the actual message vs. the expected message.

3. Find the production code that generates the message:
   ```bash
   grep -rn "schema.version\|schema_version" src/specify_cli/ --include="*.py" | grep -i "error\|invalid\|mismatch\|unsupported" | head -20
   ```

4. Determine intent:
   - If the message was changed **intentionally** as part of another mission's work: update the test assertion to match the new wording.
   - If the message was changed **accidentally**: restore the original wording in the production code.
   - Use `git log --oneline src/specify_cli/<file> | head -10` to check recent commits and determine intent.

5. Apply the minimum fix (one or the other, not both).

**Files**:
- `tests/specify_cli/migration/test_schema_version.py` (if test assertion needs updating)
- OR the production file containing the error message (if message needs restoring)

**Validation**: `pytest tests/specify_cli/migration/test_schema_version.py -v` passes.

---

### T020 — Enumerate the 6 failing WP files

**Steps**:

1. Run the WP validation test:
   ```bash
   pytest tests/specify_cli/status/test_wp_metadata.py::test_all_kitty_specs_wp_files_validate -v -s 2>&1
   ```

2. The test output will list:
   - The path to each failing WP file
   - The Pydantic validation error (missing field, wrong type, etc.)

3. Record all 6 files and their specific errors.

4. Read the current `WorkPackage` Pydantic model to understand the expected schema:
   ```bash
   grep -rn "class WorkPackage\|WorkPackageModel" src/specify_cli/ --include="*.py" | head -10
   ```

**Output**: List of 6 WP files with their specific validation errors.

---

### T021 — Update the 6 WP JSON files

**Steps**:

For each of the 6 WP files identified in T020:

1. Open the WP file (JSON or Markdown with YAML frontmatter).

2. Apply the minimum fix for each validation error:
   - **Missing required field**: Add the field with an appropriate default value (e.g., `"dependencies": []` for a field that was added after the file was created).
   - **Wrong type**: Convert the value to the expected type (e.g., string `"WP01"` → list `["WP01"]`).
   - **Extra field not in model**: If Pydantic is in strict mode, remove the unrecognized field.

3. After updating each file, verify it validates:
   ```bash
   python3 -c "
   import json
   from specify_cli.<model_module> import WorkPackage
   with open('<path/to/wp/file>') as f:
       data = json.load(f)
   wp = WorkPackage(**data)
   print('valid:', wp)
   "
   ```

4. Do not change the semantics of any WP — only add/correct structural fields.

**Files**: The 6 WP files identified in T020 (paths from `kitty-specs/`).

**Validation**: Each file validates individually before running the full test.

---

### T022 — Verify all WP04 target tests green

**Steps**:

```bash
pytest tests/auth/integration/test_refresh_through_transport.py \
       tests/specify_cli/invocation/ \
       tests/specify_cli/migration/test_schema_version.py \
       tests/specify_cli/status/test_wp_metadata.py::test_all_kitty_specs_wp_files_validate \
       -v 2>&1
```

Expected: all previously-failing tests pass. Zero new failures.

Then run a broader sweep to catch regressions:
```bash
pytest tests/auth/ tests/specify_cli/invocation/ tests/specify_cli/migration/ tests/specify_cli/status/ -q
```

---

## Branch Strategy

**Planning base branch**: `main`
**Merge target**: `main`
**Execution**: Lane C worktree. Run `spec-kitty agent action implement WP04 --agent claude`.

---

## Definition of Done

- [ ] `test_refresh_through_transport` exits with code 0 or 1 (not 2)
- [ ] Invocation tests (`test_do`, `test_profiles`, `test_record`) pass with clean JSON
- [ ] `test_schema_version` passes
- [ ] `test_all_kitty_specs_wp_files_validate` passes (all 6 WP files valid)
- [ ] `mypy --strict` passes on any modified Python files
- [ ] No production code changes introduce new `SPEC_KITTY_TEST_MODE` bypasses
- [ ] No previously-passing test regresses

## Risks

- **Auth fixture complexity**: `sync status --check` may have multiple layers of required config. Trace patiently — exit code 2 means it never reached the command body.
- **WP file cascade**: The 6 failing WP files may each have a different error. Enumerate before bulk-editing.

## Reviewer Guidance

1. Confirm auth fix is in the test fixture — not production code.
2. Confirm the conftest teardown correctly resets the `logged_out_on_connected_teamspace` state.
3. Confirm WP JSON file changes are structural only (no semantic changes to existing fields).
4. Run `pytest tests/auth/ tests/specify_cli/ -q` independently.

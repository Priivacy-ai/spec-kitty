---
work_package_id: WP02
title: Migration and Compatibility Gate
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-011
- NFR-004
- NFR-005
tracker_refs: []
planning_base_branch: feat/tool-surface-contract
merge_target_branch: feat/tool-surface-contract
branch_strategy: Planning artifacts for this mission were generated on feat/tool-surface-contract. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/tool-surface-contract unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
agent: claude
history:
- date: '2026-06-14'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/tool_surface/integration/
create_intent:
- tests/specify_cli/tool_surface/integration/__init__.py
- tests/specify_cli/tool_surface/integration/test_migration_compat.py
- tests/specify_cli/tool_surface/integration/test_agent_config_compat.py
- tests/specify_cli/tool_surface/integration/fixtures/__init__.py
- tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json
execution_mode: code_change
owned_files:
- tests/specify_cli/tool_surface/integration/__init__.py
- tests/specify_cli/tool_surface/integration/test_migration_compat.py
- tests/specify_cli/tool_surface/integration/test_agent_config_compat.py
- tests/specify_cli/tool_surface/integration/fixtures/__init__.py
- tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, run:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Establish integration test fixtures that act as a **compatibility gate** for the entire epic. After this WP merges:

- `doctor skills --json` output schema is captured as a baseline snapshot
- `spec-kitty agent config list/status/sync` interface is captured as a baseline snapshot
- Any subsequent WP (WP03-WP09) that would break these baselines is caught immediately when its PR tests run

**This WP's tests must pass for every subsequent WP.** If WP03 breaks `test_migration_compat.py`, WP03 cannot merge.

**Child issue**: #1944
**Parent epic**: #1945

## Context

The existing `doctor skills --json` command and `spec-kitty agent config list/status/sync` commands are used by external tooling and documented consumers. Their output schemas are backward-compatibility guarantees that must not change when the ToolSurfaceContract registry is introduced.

## Branch Strategy

- Planning base branch: `feat/tool-surface-contract`
- Merge target: `feat/tool-surface-contract`
- Command: `spec-kitty agent action implement WP02 --agent claude`

## Subtask Details

### T008 -- Write `test_migration_compat.py`

**Purpose**: Assert that `spec-kitty doctor skills --json` output schema is unchanged before and after the ToolSurfaceContract registry is introduced.

**Approach**:
1. Run `spec-kitty doctor skills --json` using subprocess against the current installed version.
2. Capture the output structure: top-level keys, finding code format, per-finding field names.
3. Write a baseline snapshot to `tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json`.
4. The test asserts: running `doctor skills --json` returns output that conforms to the baseline schema (required top-level keys present, finding objects have `code`, `detail`, etc.).

**Key assertions**:
```python
def test_doctor_skills_json_schema_stable():
    """Assert doctor skills --json output schema has not changed."""
    result = subprocess.run(
        ["spec-kitty", "doctor", "skills", "--json"],
        capture_output=True, text=True, cwd=project_root
    )
    output = json.loads(result.stdout)
    # Top-level keys must be present
    assert "findings" in output or "result" in output  # adjust to actual schema
    # Each finding must have required fields
    for finding in output.get("findings", []):
        assert "code" in finding
        assert "detail" in finding
```

Consult the actual current `doctor skills --json` output to determine the exact schema. Do not assume -- run it and capture it.

**Files**:
- `tests/specify_cli/tool_surface/integration/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/integration/test_migration_compat.py` (new, ~80 lines)
- `tests/specify_cli/tool_surface/integration/fixtures/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json` (new, captured from real run)

**Validation**:
- [ ] Test passes against the current (pre-registry) codebase
- [ ] Test is deterministic (does not depend on whether skills are installed or not)

---

### T009 -- Write `test_agent_config_compat.py`

**Purpose**: Assert that `spec-kitty agent config list/status/sync` external interface is unchanged.

**Approach**:
1. Run `spec-kitty agent config list --json` and `spec-kitty agent config status --json` (if available).
2. Capture the output structure: keys, format, error codes.
3. Write assertions that the interface conforms to the baseline.

**Key assertions**:
```python
def test_agent_config_list_json_schema_stable():
    """Assert agent config list --json output schema has not changed."""
    result = subprocess.run(
        ["spec-kitty", "agent", "config", "list", "--json"],
        capture_output=True, text=True, cwd=project_root
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    # Assert expected top-level keys
    assert isinstance(output, dict)
    # Add specific field assertions based on actual output
```

**Files**:
- `tests/specify_cli/tool_surface/integration/test_agent_config_compat.py` (new, ~80 lines)

**Validation**:
- [ ] Test passes against the current codebase
- [ ] `spec-kitty agent config sync` test (if applicable) verifies no state changes in a dry-run scenario

---

### T010 -- Add compat fixture helpers and baseline snapshots

**Purpose**: Provide shared helpers for running CLI commands in tests and comparing against baseline snapshots.

**Helpers to create**:
```python
# tests/specify_cli/tool_surface/integration/conftest.py or fixtures module

def run_spec_kitty(*args: str, cwd: Path) -> dict:
    """Run spec-kitty CLI and return parsed JSON output."""
    result = subprocess.run(
        ["spec-kitty", *args],
        capture_output=True, text=True, cwd=str(cwd)
    )
    return json.loads(result.stdout)

def project_root() -> Path:
    """Return the repository root for subprocess calls."""
    ...
```

Also capture the actual baseline JSON snapshots by running the commands against the current code:
```bash
spec-kitty doctor skills --json > tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json
spec-kitty agent config list --json > tests/specify_cli/tool_surface/integration/fixtures/agent_config_list_baseline.json
```

**Files**:
- `tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json` (captured)
- `tests/specify_cli/tool_surface/integration/fixtures/agent_config_list_baseline.json` (captured)

**Validation**:
- [ ] Both baseline files are valid JSON
- [ ] Baseline files are committed (not gitignored)

---

### T011 -- Write compatibility contract doc

**Purpose**: Record the migration compatibility policy in a contract file so future implementers understand the constraints.

**File**: `kitty-specs/tool-surface-contract-01KV2K2P/contracts/migration-compatibility.md`

**Content**:
- What `doctor skills --json` schema fields are frozen (must not change)
- What `agent config` interface fields are frozen
- What constitutes a breaking change vs. an additive change
- How to update the baseline if an intentional additive change is made

Example:
```markdown
# Migration Compatibility Contract

## Frozen interfaces

### `doctor skills --json`
The following fields in the output are frozen and must not change:
- Top-level `findings` array
- Each finding's `code` field (string, stable identifier)
- Each finding's `detail` field (string, human-readable)
[Document actual fields from baseline]

### `spec-kitty agent config list --json`
[Document actual fields from baseline]

## Additive changes (allowed)
- New top-level keys may be added
- New finding codes may be introduced
- New fields may be added to finding objects

## How to update baselines
If an intentional additive change causes baseline drift:
1. Regenerate baselines: run `spec-kitty doctor skills --json` and save
2. Update `doctor_skills_baseline.json`
3. Document the change in CHANGELOG.md
4. PR must include Codex sign-off that the change is additive, not breaking
```

**Validation**:
- [ ] Contract doc exists and is committed
- [ ] Contract references the actual baseline field names (not placeholders)

## Definition of Done

- [ ] `pytest tests/specify_cli/tool_surface/integration/test_migration_compat.py` passes
- [ ] `pytest tests/specify_cli/tool_surface/integration/test_agent_config_compat.py` passes
- [ ] Both baseline JSON files are committed
- [ ] `kitty-specs/tool-surface-contract-01KV2K2P/contracts/migration-compatibility.md` exists
- [ ] No changes to any existing source files (this WP is test-and-contract only)

## Risks

- **Baseline instability**: If `doctor skills --json` output varies between runs (e.g., depends on what tools are configured), the test must be designed to pass regardless of which tools are installed. Focus on schema shape, not content.
- **subprocess in tests**: Some CI environments may not have `spec-kitty` on PATH. Use the installed editable package path or `python -m specify_cli` as a fallback.

## Reviewer Guidance (Codex)

- Verify that the compat tests would catch a schema-breaking change in `doctor skills --json`
- Verify baseline snapshots are real (not fabricated)
- Verify the migration contract correctly identifies frozen vs. additive fields
- These tests must remain GREEN for every subsequent WP PR

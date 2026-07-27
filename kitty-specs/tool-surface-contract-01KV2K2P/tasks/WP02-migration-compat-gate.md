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
base_branch: kitty/mission-tool-surface-contract-01KV2K2P
base_commit: 512f149be63c094c8b0c079781688b47464992b8
created_at: '2026-06-14T10:05:21.770674+00:00'
subtasks:
- T008
- T009
- T010
- T011
agent: claude
shell_pid: '12914'
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
- src/specify_cli/tool_surface/contracts/migration-compatibility.md
execution_mode: code_change
owned_files:
- tests/specify_cli/tool_surface/integration/__init__.py
- tests/specify_cli/tool_surface/integration/test_migration_compat.py
- tests/specify_cli/tool_surface/integration/test_agent_config_compat.py
- tests/specify_cli/tool_surface/integration/fixtures/__init__.py
- tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_baseline.json
- src/specify_cli/tool_surface/contracts/migration-compatibility.md
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

**Approach -- use checkout-local entrypoint, not system `spec-kitty`**:

The test MUST NOT shell out to `["spec-kitty", ...]` because that invokes the globally-installed version, not the checkout under test. Use one of these checkout-local approaches:

```python
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[5]  # adjust depth to repo root

def _run_spec_kitty(*args: str, cwd: Path | None = None) -> dict:
    """Run spec-kitty from the checkout's venv or via python -m."""
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli"] + list(args),
        capture_output=True, text=True,
        cwd=str(cwd or PROJECT_ROOT),
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
```

**Use controlled fixtures, not ambient machine state**:

The test must create a temporary `.kittify/config.yaml` with a fixed minimal agent list so that doctor output is deterministic regardless of what the developer has configured. Example:

```python
import tempfile, json, yaml

def test_doctor_skills_json_schema_stable(tmp_path):
    # Write minimal controlled .kittify config
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        yaml.dump({"agents": {"available": ["codex"]}})
    )
    # Write minimal command-skills manifest so doctor doesn't error
    (kittify / "command-skills-manifest.json").write_text(
        json.dumps({"schema_version": 1, "entries": {}})
    )

    result = _run_spec_kitty("doctor", "skills", "--json", cwd=tmp_path)
    assert result["returncode"] == 0, result["stderr"]
    output = json.loads(result["stdout"])

    # Assert schema shape (not content)
    assert "result" in output or "findings" in output, "Top-level schema changed"
    for finding in output.get("findings", []):
        assert "code" in finding, "Finding missing 'code' field"
        assert "detail" in finding or "message" in finding, "Finding missing detail"
```

**Key assertions**:
- Output is valid JSON
- Top-level schema keys present (at minimum `result` or `findings`)
- Each finding has `code` and a human-readable message field
- Test is deterministic: does NOT depend on what tools the developer has configured

**Files**:
- `tests/specify_cli/tool_surface/integration/__init__.py` (new, empty)
- `tests/specify_cli/tool_surface/integration/test_migration_compat.py` (new, ~120 lines)
- `tests/specify_cli/tool_surface/integration/fixtures/__init__.py` (new, empty)

**Validation**:
- [ ] Test passes without any globally-installed `spec-kitty`
- [ ] Test is deterministic (fixed config in tmp_path, not ambient state)
- [ ] `subprocess.run(["spec-kitty", ...])` does NOT appear in this file

---

### T009 -- Write `test_agent_config_compat.py`

**Purpose**: Assert that `spec-kitty agent config list/status/sync` external interface is unchanged.

**Approach**:
1. Run `spec-kitty agent config list --json` and `spec-kitty agent config status --json` (if available).
2. Capture the output structure: keys, format, error codes.
3. Write assertions that the interface conforms to the baseline.

**Key assertions**:
```python
def test_agent_config_list_json_schema_stable(tmp_path):
    """Assert agent config list --json output schema has not changed."""
    # Use checkout-local entrypoint (sys.executable + -m specify_cli), not ["spec-kitty", ...]
    result = _run_spec_kitty("agent", "config", "list", "--json", cwd=tmp_path)
    assert result["returncode"] == 0
    output = json.loads(result["stdout"])
    # Assert expected top-level keys
    assert isinstance(output, dict)
    # Add specific field assertions based on actual output
```

Use controlled fixtures in `tmp_path` (same approach as T008) so results are deterministic.

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
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[5]  # adjust depth to repo root

def _run_spec_kitty(*args: str, cwd: Path | None = None) -> dict:
    """Run spec-kitty from the checkout's venv or via python -m.

    IMPORTANT: Do NOT use ["spec-kitty", ...] -- that invokes the globally-installed
    version, not the checkout under test.
    """
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli"] + list(args),
        capture_output=True, text=True,
        cwd=str(cwd or PROJECT_ROOT),
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
```

Generate schema shape fixtures programmatically using the checkout-local approach above (not by piping from the global `spec-kitty` CLI). Store only the JSON key structure (not content) so fixtures are machine-independent.

**Files**:
- `tests/specify_cli/tool_surface/integration/fixtures/doctor_skills_schema.json` (schema shape only, generated programmatically)
- `tests/specify_cli/tool_surface/integration/fixtures/agent_config_list_schema.json` (schema shape only, generated programmatically)

**Validation**:
- [ ] Both fixture files are valid JSON
- [ ] Fixture files do NOT contain machine-specific paths or ambient tool config
- [ ] Fixtures are committed (not gitignored)

---

### T011 -- Write compatibility contract doc

**Purpose**: Record the migration compatibility policy in a contract file so future implementers understand the constraints.

**File**: `src/specify_cli/tool_surface/contracts/migration-compatibility.md`

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
- [ ] `src/specify_cli/tool_surface/contracts/migration-compatibility.md` exists and references the actual baseline field names
- [ ] No changes to any existing source files (this WP is test-and-contract only)

## Risks

- **Baseline instability**: If `doctor skills --json` output varies between runs (e.g., depends on what tools are configured), the test must be designed to pass regardless of which tools are installed. Focus on schema shape, not content.
- **subprocess in tests**: Some CI environments may not have `spec-kitty` on PATH. Use the installed editable package path or `python -m specify_cli` as a fallback.

## Reviewer Guidance (Codex)

- Verify that the compat tests would catch a schema-breaking change in `doctor skills --json`
- Verify baseline snapshots are real (not fabricated)
- Verify the migration contract correctly identifies frozen vs. additive fields
- These tests must remain GREEN for every subsequent WP PR

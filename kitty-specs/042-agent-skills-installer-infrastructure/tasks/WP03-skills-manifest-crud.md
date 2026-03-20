---
work_package_id: WP03
title: Skills Manifest CRUD
lane: "for_review"
dependencies:
- WP01
base_branch: 042-agent-skills-installer-infrastructure-WP01
base_commit: 06eb8070106b6ece8424249f8a245949d4c4169b
created_at: '2026-03-20T16:58:24.895146+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
phase: Phase 1 - Foundation
assignee: ''
agent: coordinator
shell_pid: '92922'
review_status: has_feedback
reviewed_by: Robert Douglass
review_feedback: feedback://042-agent-skills-installer-infrastructure/WP03/20260320T170736Z-2a549533.md
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-013
- FR-023
---

# Work Package Prompt: WP03 – Skills Manifest CRUD

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP03
```

No dependencies — can run in parallel with WP01.

---

## Objectives & Success Criteria

1. `SkillsManifest` and `ManagedFile` dataclasses match the data model.
2. `write_manifest()` serializes to human-readable YAML at `.kittify/agent-surfaces/skills-manifest.yaml`.
3. `load_manifest()` deserializes from YAML, returns `None` for missing/corrupt files.
4. `compute_file_hash()` produces correct SHA-256 hex digests.
5. Round-trip test: write → load produces identical data.
6. Passes `mypy --strict` and `ruff check`.

## Context & Constraints

- **Spec**: FR-013, FR-023
- **Data model**: `kitty-specs/042-agent-skills-installer-infrastructure/data-model.md` (ManagedFile, SkillsManifest, YAML schema)
- **Existing pattern**: See `src/specify_cli/core/agent_config.py` for YAML read/write pattern using `ruamel.yaml`
- **Manifest path**: `.kittify/agent-surfaces/skills-manifest.yaml`
- Use `ruamel.yaml` (already a project dependency) for YAML I/O, not `pyyaml`.

## Subtasks & Detailed Guidance

### Subtask T013 – ManagedFile and SkillsManifest dataclasses

**Purpose**: Type-safe data structures for manifest content.

**Steps**:
1. Create `src/specify_cli/skills/manifest.py`
2. Define:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field
   from pathlib import Path

   MANIFEST_PATH = ".kittify/agent-surfaces/skills-manifest.yaml"

   @dataclass
   class ManagedFile:
       path: str        # relative to project root
       sha256: str      # hex digest
       file_type: str   # "wrapper" | "skill_root_marker"

   @dataclass
   class SkillsManifest:
       spec_kitty_version: str
       created_at: str
       updated_at: str
       skills_mode: str
       selected_agents: list[str] = field(default_factory=list)
       installed_skill_roots: list[str] = field(default_factory=list)
       managed_files: list[ManagedFile] = field(default_factory=list)
   ```

**Files**: `src/specify_cli/skills/manifest.py` (new, ~120 lines)

### Subtask T014 – write_manifest() YAML serialization

**Purpose**: Persist manifest to disk in human-readable YAML.

**Steps**:
1. Add function:
   ```python
   def write_manifest(project_root: Path, manifest: SkillsManifest) -> None:
       """Write manifest to .kittify/agent-surfaces/skills-manifest.yaml."""
   ```
2. Create parent directory if missing: `manifest_path.parent.mkdir(parents=True, exist_ok=True)`
3. Serialize to dict, then write with `ruamel.yaml`:
   - Convert `ManagedFile` list to list of dicts
   - Use `YAML(typ="safe")` for writing or `ruamel.yaml.YAML()` round-trip mode
   - Match the YAML schema from the data model document
4. Handle encoding: write as UTF-8

**Files**: `src/specify_cli/skills/manifest.py`

### Subtask T015 – load_manifest() YAML deserialization

**Purpose**: Read manifest from disk with graceful error handling.

**Steps**:
1. Add function:
   ```python
   def load_manifest(project_root: Path) -> SkillsManifest | None:
       """Load manifest from YAML. Returns None if file missing or invalid."""
   ```
2. Check if file exists; return `None` if missing
3. Read YAML content
4. Validate required fields are present; return `None` if corrupt
5. Reconstruct `ManagedFile` objects from dict entries
6. Return `SkillsManifest` instance

**Edge cases**:
- File exists but is empty → return `None`
- File exists but has invalid YAML → return `None` (log warning if rich console available)
- File exists but missing required fields → return `None`

**Files**: `src/specify_cli/skills/manifest.py`

### Subtask T016 – compute_file_hash() SHA-256 helper

**Purpose**: Content hashing for drift detection.

**Steps**:
1. Add function:
   ```python
   import hashlib

   def compute_file_hash(file_path: Path) -> str:
       """Return SHA-256 hex digest of file contents."""
       h = hashlib.sha256()
       with file_path.open("rb") as f:
           for chunk in iter(lambda: f.read(8192), b""):
               h.update(chunk)
       return h.hexdigest()
   ```
2. Read in binary mode to ensure cross-platform consistency.
3. Use chunked reading for large files (though wrappers are small, this is good practice).

**Files**: `src/specify_cli/skills/manifest.py`

### Subtask T017 – Unit tests

**Purpose**: Verify manifest CRUD, round-trip, and error handling.

**Steps**:
1. Create `tests/specify_cli/test_skills/test_manifest.py`
2. Tests (all use `tmp_path` fixture for filesystem):

```python
# Round-trip: write then load produces identical data
def test_manifest_round_trip(tmp_path):
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0",
        created_at="2026-03-20T16:00:00Z",
        updated_at="2026-03-20T16:00:00Z",
        skills_mode="auto",
        selected_agents=["claude", "codex"],
        installed_skill_roots=[".agents/skills/", ".claude/skills/"],
        managed_files=[
            ManagedFile(path=".agents/skills/.gitkeep", sha256="e3b0...", file_type="skill_root_marker"),
        ],
    )
    write_manifest(tmp_path, manifest)
    loaded = load_manifest(tmp_path)
    assert loaded is not None
    assert loaded.spec_kitty_version == manifest.spec_kitty_version
    assert loaded.selected_agents == manifest.selected_agents
    assert len(loaded.managed_files) == 1
    assert loaded.managed_files[0].path == ".agents/skills/.gitkeep"

# Load from missing file returns None
def test_load_missing_returns_none(tmp_path):
    assert load_manifest(tmp_path) is None

# Load from corrupt YAML returns None
def test_load_corrupt_returns_none(tmp_path):
    manifest_path = tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{{invalid yaml", encoding="utf-8")
    assert load_manifest(tmp_path) is None

# Load from empty file returns None
def test_load_empty_returns_none(tmp_path):
    manifest_path = tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("", encoding="utf-8")
    assert load_manifest(tmp_path) is None

# compute_file_hash produces correct SHA-256
def test_compute_file_hash(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert compute_file_hash(test_file) == expected

# compute_file_hash for empty file
def test_compute_file_hash_empty(tmp_path):
    test_file = tmp_path / "empty.txt"
    test_file.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert compute_file_hash(test_file) == expected

# Parent directory creation on write
def test_write_creates_parent_dir(tmp_path):
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0", created_at="", updated_at="",
        skills_mode="auto",
    )
    write_manifest(tmp_path, manifest)
    assert (tmp_path / ".kittify" / "agent-surfaces" / "skills-manifest.yaml").exists()
```

**Files**: `tests/specify_cli/test_skills/test_manifest.py` (new, ~80 lines)

## Test Strategy

- All tests use `tmp_path` for isolated filesystem
- Round-trip test is the primary correctness check
- Error handling tests verify graceful degradation
- Run: `pytest tests/specify_cli/test_skills/test_manifest.py -v`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| YAML serialization order changes between writes | Use `ruamel.yaml` round-trip mode which preserves order, or accept dict ordering |
| ruamel.yaml version differences | Project already pins this dependency; no risk |

## Review Guidance

1. Verify YAML output matches the schema in `data-model.md`.
2. Verify `load_manifest` never raises — it returns `None` on any error.
3. Verify file hash uses binary mode for cross-platform consistency.
4. Check that `MANIFEST_PATH` constant is used consistently (not hardcoded elsewhere).

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
- 2026-03-20T16:58:25Z – coordinator – shell_pid=68611 – lane=doing – Assigned agent via workflow command
- 2026-03-20T17:02:06Z – coordinator – shell_pid=68611 – lane=for_review – Ready for review: SkillsManifest/ManagedFile dataclasses, write_manifest(), load_manifest(), compute_file_hash(), 17 passing tests
- 2026-03-20T17:02:58Z – codex – shell_pid=77270 – lane=doing – Started review via workflow command
- 2026-03-20T17:07:36Z – codex – shell_pid=77270 – lane=planned – Moved to planned
- 2026-03-20T17:09:07Z – coordinator – shell_pid=92922 – lane=doing – Started implementation via workflow command
- 2026-03-20T17:10:52Z – coordinator – shell_pid=92922 – lane=for_review – Fixed: load_manifest now catches UnicodeDecodeError and requires list fields

---
work_package_id: WP03
title: ManagedSkillManifest Dataclass & Persistence
lane: planned
dependencies: []
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 0 - Foundation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-21T07:39:56Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-004
- FR-005
- C-005
---

# Work Package Prompt: WP03 – ManagedSkillManifest Dataclass & Persistence

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `ManagedFileEntry` and `ManagedSkillManifest` dataclasses
- Implement JSON persistence (save/load/clear) to `.kittify/skills-manifest.json`
- Implement helper methods for querying and mutating the manifest
- Implement content hash computation utility
- Unit tests with 90%+ coverage

**Success**: A manifest can be created, populated with entries, saved to JSON, loaded back, and queried — with perfect round-trip fidelity.

## Context & Constraints

- **PRD reference**: Section 9.3 (Manifest and Drift)
- **Constraint C-005**: Separate from dossier manifest (`src/specify_cli/dossier/manifest.py`)
- **Existing pattern**: Use `specify_cli.core.atomic.atomic_write` for safe file writes
- **Data model**: See `kitty-specs/055-agent-skills-pack/data-model.md`

**Implementation command**: `spec-kitty implement WP03`

## Subtasks & Detailed Guidance

### Subtask T009 – Create dataclasses

- **Purpose**: Define the core data structures for managed file tracking.
- **Steps**:
  1. Create `src/specify_cli/skills/manifest.py`
  2. Define `ManagedFileEntry`:
     ```python
     @dataclass
     class ManagedFileEntry:
         skill_name: str           # e.g., "spec-kitty-setup-doctor"
         source_file: str          # Relative within skill dir, e.g., "SKILL.md"
         installed_path: str       # Relative from project root, e.g., ".claude/skills/spec-kitty-setup-doctor/SKILL.md"
         installation_class: str   # "shared-root-capable", "native-root-required", "wrapper-only"
         agent_key: str            # "claude", "codex", etc.
         content_hash: str         # "sha256:<hex>"
         installed_at: str         # ISO 8601 UTC
     ```
  3. Define `ManagedSkillManifest`:
     ```python
     @dataclass
     class ManagedSkillManifest:
         version: int = 1
         created_at: str = ""
         updated_at: str = ""
         spec_kitty_version: str = ""
         entries: list[ManagedFileEntry] = field(default_factory=list)
     ```
- **Files**: `src/specify_cli/skills/manifest.py` (new)
- **Notes**: Use `from __future__ import annotations` for forward refs. All fields must have type annotations.

### Subtask T010 – Implement JSON persistence

- **Purpose**: Save and load the manifest to/from `.kittify/skills-manifest.json`.
- **Steps**:
  1. Implement `save_manifest(manifest: ManagedSkillManifest, project_path: Path) -> None`:
     - Serialize to JSON using `dataclasses.asdict()`
     - Write to `project_path / ".kittify" / "skills-manifest.json"`
     - Use `atomic_write` from `specify_cli.core.atomic`
     - Update `updated_at` timestamp before saving
  2. Implement `load_manifest(project_path: Path) -> ManagedSkillManifest | None`:
     - Read from `project_path / ".kittify" / "skills-manifest.json"`
     - Return `None` if file doesn't exist
     - Deserialize entries into `ManagedFileEntry` objects
     - Handle malformed JSON gracefully (log warning, return None)
  3. Implement `clear_manifest(project_path: Path) -> None`:
     - Delete the manifest file if it exists
  4. Define `MANIFEST_FILENAME = "skills-manifest.json"` as module constant
- **Files**: `src/specify_cli/skills/manifest.py` (modify)
- **Notes**: Use `json.dumps(indent=2)` for human-readable output. Ensure `.kittify/` directory exists before writing.

### Subtask T011 – Implement helper methods

- **Purpose**: Provide convenient query and mutation methods for the manifest.
- **Steps**:
  1. Add methods to `ManagedSkillManifest`:
     ```python
     def add_entry(self, entry: ManagedFileEntry) -> None:
         """Add a new entry, replacing any existing entry with the same installed_path."""

     def remove_entries_for_agent(self, agent_key: str) -> list[ManagedFileEntry]:
         """Remove and return all entries for a specific agent."""

     def find_by_skill(self, skill_name: str) -> list[ManagedFileEntry]:
         """Find all entries for a specific skill."""

     def find_by_installed_path(self, installed_path: str) -> ManagedFileEntry | None:
         """Find entry by installed path."""
     ```
  2. `add_entry` should replace if `installed_path` already exists (idempotent)
- **Files**: `src/specify_cli/skills/manifest.py` (modify)

### Subtask T012 – Content hash computation utility

- **Purpose**: Compute SHA-256 hashes for drift detection.
- **Steps**:
  1. Implement `compute_content_hash(file_path: Path) -> str`:
     ```python
     def compute_content_hash(file_path: Path) -> str:
         """Compute sha256 hash of file content."""
         import hashlib
         content = file_path.read_bytes()
         digest = hashlib.sha256(content).hexdigest()
         return f"sha256:{digest}"
     ```
  2. Place in `src/specify_cli/skills/manifest.py` as a module-level function
- **Files**: `src/specify_cli/skills/manifest.py` (modify)
- **Notes**: Read as bytes to avoid encoding issues. Hash is deterministic across platforms.

### Subtask T013 – Unit tests for manifest

- **Purpose**: Verify manifest CRUD operations and JSON round-trip.
- **Steps**:
  1. Create `tests/specify_cli/skills/test_manifest.py`
  2. Test cases:
     - `test_create_manifest_with_defaults` — verify default values
     - `test_add_entry` — add entry, verify it's in entries list
     - `test_add_entry_replaces_duplicate_path` — same installed_path replaces
     - `test_remove_entries_for_agent` — removes correct entries, returns them
     - `test_find_by_skill` — finds matching entries
     - `test_find_by_installed_path` — finds or returns None
     - `test_save_and_load_round_trip` — save then load, verify equality
     - `test_load_missing_file_returns_none` — no file → None
     - `test_load_malformed_json_returns_none` — bad JSON → None
     - `test_clear_manifest_removes_file` — file deleted
     - `test_compute_content_hash` — verify sha256 output format
     - `test_compute_content_hash_deterministic` — same content → same hash
  3. Use `tmp_path` fixture for all file operations
- **Files**: `tests/specify_cli/skills/test_manifest.py` (new, ~150 lines)
- **Parallel?**: Yes

## Risks & Mitigations

- **Concurrent writes**: Multiple agents writing manifest → `atomic_write` prevents corruption
- **Schema evolution**: `version` field enables future migration
- **Large manifests**: 12 agents × 8 skills × ~5 files each = ~480 entries → well within 50KB limit

## Review Guidance

- Verify round-trip fidelity (save → load produces identical data)
- Verify `atomic_write` is used (not raw `open()`)
- Verify content hash format is `sha256:<hex>`
- Verify all methods have type annotations

## Activity Log

- 2026-03-21T07:39:56Z – system – lane=planned – Prompt created.

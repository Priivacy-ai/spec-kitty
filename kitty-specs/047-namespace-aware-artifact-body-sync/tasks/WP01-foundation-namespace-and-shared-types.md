---
work_package_id: WP01
title: Foundation - NamespaceRef & Shared Types
dependencies: []
requirement_refs: [FR-002, FR-005, FR-011, FR-012]
base_branch: 2.x
base_commit: 25ddd221bc402b8ddfbbd57e5046708bbc953a37
created_at: '2026-03-09T07:19:44.028991+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Foundation
history:
- timestamp: '2026-03-09T07:09:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: ''
execution_mode: code_change
mission_id: 01KN2371WTANS0Z2M6JEHAJS3F
owned_files:
- kitty-specs/047-namespace-aware-artifact-body-sync/plan.md
- kitty-specs/047-namespace-aware-artifact-body-sync/spec.md
- src/specify_cli/dossier/manifest.py
- src/specify_cli/sync/namespace.py
- src/specify_cli/sync/project_identity.py
- tests/specify_cli/sync/test_namespace.py
wp_code: WP01
---

# Work Package Prompt: WP01 – Foundation - NamespaceRef & Shared Types

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Create `NamespaceRef` dataclass representing the 5-field canonical namespace tuple used by all body upload operations
- Create `SupportedInlineFormat` enum for v1 supported file extensions
- Create `UploadOutcome` dataclass for per-artifact upload result classification
- All types pass `mypy --strict`
- `pytest tests/specify_cli/sync/test_namespace.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: `kitty-specs/047-namespace-aware-artifact-body-sync/spec.md` — FR-002 (namespace tuple), FR-005 (supported formats), FR-012 (outcome classification)
- **Plan**: `kitty-specs/047-namespace-aware-artifact-body-sync/plan.md` — Module Responsibilities section for `namespace.py`
- **Existing code**: `src/specify_cli/sync/project_identity.py` — `ProjectIdentity` dataclass (source of `project_uuid`, `project_slug`, `node_id`)
- **Existing code**: `src/specify_cli/dossier/manifest.py` — `ExpectedArtifactManifest` (source of `manifest_version`)
- **Constraint**: All new code targets Python 3.11+ with `mypy --strict`
- **Constraint**: No new dependencies — use stdlib `dataclasses`, `enum`, `pathlib`

**Implementation command**: `spec-kitty implement WP01`

## Subtasks & Detailed Guidance

### Subtask T001 – Create NamespaceRef Dataclass

- **Purpose**: Define the canonical sender-side representation of the five-field namespace tuple that every body upload request must include (FR-002). This is the identity envelope for all artifact body operations.

- **Steps**:
  1. Create `src/specify_cli/sync/namespace.py`
  2. Define a frozen `@dataclass` named `NamespaceRef` with these fields:
     - `project_uuid: str` — UUID4 string from `ProjectIdentity.project_uuid`
     - `feature_slug: str` — e.g., `"047-namespace-aware-artifact-body-sync"`
     - `target_branch: str` — e.g., `"2.x"`, `"main"`
     - `mission_key: str` — e.g., `"software-dev"`
     - `manifest_version: str` — e.g., `"1"` from `ExpectedArtifactManifest.manifest_version`
  3. Add a `__post_init__` validator that raises `ValueError` if any field is empty or whitespace-only
  4. Add a `to_dict() -> dict[str, str]` method returning all 5 fields as a flat dict (used in request body construction)
  5. Add a `dedupe_key(artifact_path: str, content_hash: str) -> str` method that returns a deterministic string for the 7-field unique constraint used by the body queue: `f"{project_uuid}|{feature_slug}|{target_branch}|{mission_key}|{manifest_version}|{artifact_path}|{content_hash}"`

- **Files**: `src/specify_cli/sync/namespace.py` (new, ~60 lines)
- **Parallel?**: No — T002 builds on this.

### Subtask T002 – Add NamespaceRef.from_project_identity() Factory

- **Purpose**: Provide a construction helper that assembles a `NamespaceRef` from the existing `ProjectIdentity`, feature metadata, and manifest version. This prevents callers from manually threading 5 fields through the call stack.

- **Steps**:
  1. Add a `@classmethod` factory method to `NamespaceRef`:
     ```python
     @classmethod
     def from_context(
         cls,
         identity: ProjectIdentity,
         feature_slug: str,
         target_branch: str,
         mission_key: str,
         manifest_version: str,
     ) -> NamespaceRef:
     ```
  2. Extract `project_uuid` from `identity.project_uuid` — convert `UUID` to `str` if needed
  3. Validate that `identity.project_uuid` is not `None`; raise `ValueError("ProjectIdentity.project_uuid is required for body sync")` if missing
  4. Return constructed `NamespaceRef`
  5. Add a second helper `resolve_manifest_version(mission_type: str) -> str` as a module-level function:
     - Import `ManifestRegistry` from `specify_cli.dossier.manifest`
     - Call `ManifestRegistry.load_manifest(mission_type)`
     - Return `manifest.manifest_version` if manifest exists, else `"1"` (default)

- **Files**: `src/specify_cli/sync/namespace.py` (extend, ~30 additional lines)
- **Parallel?**: No — depends on T001 dataclass.
- **Notes**: Import `ProjectIdentity` with `TYPE_CHECKING` guard to avoid circular imports (follow pattern in `emitter.py`).

### Subtask T003 – Create SupportedInlineFormat Enum

- **Purpose**: Enumerate file extensions eligible for inline body upload in v1 (FR-005). Provides a single source of truth for format filtering in WP03.

- **Steps**:
  1. In `src/specify_cli/sync/namespace.py`, add:
     ```python
     class SupportedInlineFormat(str, Enum):
         MARKDOWN = ".md"
         JSON = ".json"
         YAML = ".yaml"
         YML = ".yml"
         CSV = ".csv"
     ```
  2. Add a module-level helper:
     ```python
     SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(f.value for f in SupportedInlineFormat)

     def is_supported_format(path: str | Path) -> bool:
         """Check if file extension is supported for inline body upload."""
         return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS
     ```
  3. Ensure the enum is a `str` mixin so `.value` returns the string directly

- **Files**: `src/specify_cli/sync/namespace.py` (extend, ~20 additional lines)
- **Parallel?**: Yes — independent of T001/T002.

### Subtask T004 – Create UploadOutcome Dataclass

- **Purpose**: Classify the final result of one attempted upload per FR-012. Used by body_upload.py (preparation), body_transport.py (HTTP response), and logging (diagnostics).

- **Steps**:
  1. In `src/specify_cli/sync/namespace.py`, add:
     ```python
     class UploadStatus(str, Enum):
         UPLOADED = "uploaded"           # 201 stored
         ALREADY_EXISTS = "already_exists"  # 200 content hash match
         QUEUED = "queued"               # Enqueued for later delivery
         SKIPPED = "skipped"             # Filtered out (format, size, binary, hash mismatch)
         FAILED = "failed"              # Non-retryable error (400, namespace_not_found)

     @dataclass(frozen=True)
     class UploadOutcome:
         artifact_path: str              # Feature-relative path
         status: UploadStatus
         reason: str                     # Human-readable explanation
         content_hash: str | None = None # SHA-256 if available
         retryable: bool = False         # Whether the failure is retryable
     ```
  2. Add a `__str__` method for human-readable logging: `f"{artifact_path}: {status.value} ({reason})"`

- **Files**: `src/specify_cli/sync/namespace.py` (extend, ~30 additional lines)
- **Parallel?**: Yes — independent of T001/T002.

### Subtask T005 – Write test_namespace.py

- **Purpose**: Verify all foundational types work correctly. These types are consumed by every other WP, so correctness here is critical.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_namespace.py`
  2. Test `NamespaceRef` construction:
     - Valid construction with all 5 fields
     - `ValueError` on empty `project_uuid`
     - `ValueError` on whitespace-only `feature_slug`
     - `ValueError` on empty `target_branch`, `mission_key`, `manifest_version`
     - `to_dict()` returns correct flat dict
     - `dedupe_key()` returns deterministic string
     - Frozen: assignment raises `FrozenInstanceError`
  3. Test `NamespaceRef.from_context()`:
     - Valid construction from `ProjectIdentity` mock
     - `ValueError` when `identity.project_uuid` is `None`
  4. Test `resolve_manifest_version()`:
     - Returns manifest version when manifest exists
     - Returns `"1"` when manifest is `None`
  5. Test `SupportedInlineFormat`:
     - `is_supported_format("spec.md")` → True
     - `is_supported_format("data.json")` → True
     - `is_supported_format("image.png")` → False
     - `is_supported_format("binary.exe")` → False
     - Case insensitive: `is_supported_format("README.MD")` → True
  6. Test `UploadOutcome`:
     - Construction with all status codes
     - `__str__` formatting
     - Frozen: assignment raises error

- **Files**: `tests/specify_cli/sync/test_namespace.py` (new, ~120 lines)
- **Parallel?**: No — needs all types from T001-T004.
- **Notes**: Mock `ProjectIdentity` with `MagicMock` or create a minimal instance. Mock `ManifestRegistry.load_manifest` for `resolve_manifest_version` tests.

## Risks & Mitigations

- **Risk**: Circular import between `namespace.py` and `project_identity.py`. **Mitigation**: Use `TYPE_CHECKING` guard for `ProjectIdentity` import, follow pattern in `emitter.py`.
- **Risk**: `manifest_version` type mismatch (int vs str). **Mitigation**: Always store as `str` in `NamespaceRef`; convert in factory.

## Review Guidance

- Verify all 5 namespace fields are present and validated
- Verify `dedupe_key()` includes all 7 fields (5 namespace + artifact_path + content_hash)
- Verify `SupportedInlineFormat` exactly matches FR-005 extensions
- Verify `UploadStatus` exactly matches the 5 states in FR-012
- Check `mypy --strict` passes: `mypy --strict src/specify_cli/sync/namespace.py`

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T07:19:44Z – claude – shell_pid=44411 – lane=doing – Assigned agent via workflow command
- 2026-03-09T07:23:06Z – claude – shell_pid=44411 – lane=for_review – Ready for review: NamespaceRef, SupportedInlineFormat, UploadOutcome types with 44 tests, 100% coverage, mypy clean
- 2026-03-09T07:25:37Z – claude-opus – shell_pid=45749 – lane=doing – Started review via workflow command
- 2026-03-09T07:30:17Z – claude-opus – shell_pid=45749 – lane=done – Review passed: All 5 subtasks (T001-T005) verified. 44/44 tests pass, mypy clean, FR-002/FR-005/FR-011/FR-012 compliant. | Done override: Review approved pre-merge. Branch 047-namespace-aware-artifact-body-sync-WP01 ready for merge to 2.x.

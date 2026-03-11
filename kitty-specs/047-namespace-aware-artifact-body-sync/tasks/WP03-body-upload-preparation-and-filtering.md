---
work_package_id: WP03
title: Body Upload Preparation & Filtering
lane: done
dependencies: [WP01, WP02]
base_branch: 047-namespace-aware-artifact-body-sync-WP03-merge-base
base_commit: ab125a790b2bbd1290f8fa047688ae68978a2c92
created_at: '2026-03-09T08:38:19.768273+00:00'
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 2 - Core Logic
assignee: ''
agent: claude-opus
shell_pid: '52547'
review_status: approved
reviewed_by: Robert Douglass
history:
- timestamp: '2026-03-09T07:09:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-003, FR-004, FR-005, FR-006, FR-014]
---

# Work Package Prompt: WP03 – Body Upload Preparation & Filtering

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Implement `prepare_body_uploads()` in `body_upload.py` — the function that transforms `ArtifactRef` list from the indexer into queued body upload tasks
- Filter by supported surfaces (FR-004), supported formats (FR-005), size limits, and binary detection (FR-006)
- Re-hash guard detects file changes between index scan and body read
- Every skipped artifact has an explicit `UploadOutcome` with reason (FR-006, FR-012)
- `pytest tests/specify_cli/sync/test_body_upload.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: FR-004 (supported surfaces), FR-005 (supported formats), FR-006 (binary/unsupported skip), FR-012 (per-artifact diagnostics), FR-014 (path form agreement)
- **Plan**: Module Responsibilities → `body_upload.py`, Key Design Decisions #2 (indexer output as sole input), #3 (re-hash guard)
- **Input**: `List[ArtifactRef]` from `Indexer.index_feature()` — provides `relative_path`, `content_hash_sha256`, `size_bytes`, `is_present`
- **Output**: List of `UploadOutcome` (for diagnostics) + side effect: tasks enqueued in `OfflineBodyUploadQueue`
- **WP01 types**: `NamespaceRef`, `SupportedInlineFormat`, `is_supported_format()`, `UploadOutcome`, `UploadStatus`
- **WP02 queue**: `OfflineBodyUploadQueue.enqueue()`
- **Constraint**: Body sync never touches filesystem for discovery — only reads content for artifacts that pass filtering (Design Decision #2)

**Implementation command**: `spec-kitty implement WP03 --base WP02`

## Subtasks & Detailed Guidance

### Subtask T013 – Implement Surface Filtering (FR-004)

- **Purpose**: Determine which artifact paths are eligible for body upload based on their feature-relative location. Only artifacts from supported surfaces are uploaded.

- **Steps**:
  1. In `src/specify_cli/sync/body_upload.py`, define the supported surfaces:
     ```python
     # FR-004: Supported feature-scoped surfaces
     _TOP_LEVEL_ARTIFACTS: frozenset[str] = frozenset({
         "spec.md", "plan.md", "tasks.md", "research.md",
         "quickstart.md", "data-model.md",
     })

     _DIRECTORY_PREFIXES: tuple[str, ...] = (
         "research/", "contracts/", "checklists/",
     )

     _WP_PATTERN = re.compile(r"^tasks/WP\d+.*\.md$")
     ```
  2. Implement filter function:
     ```python
     def _is_supported_surface(relative_path: str) -> bool:
         """Check if artifact path matches FR-004 supported surfaces."""
         if relative_path in _TOP_LEVEL_ARTIFACTS:
             return True
         if any(relative_path.startswith(prefix) for prefix in _DIRECTORY_PREFIXES):
             return True
         if _WP_PATTERN.match(relative_path):
             return True
         return False
     ```
  3. Use `ArtifactRef.relative_path` directly — it's already feature-relative per the indexer convention (FR-014)

- **Files**: `src/specify_cli/sync/body_upload.py` (new, ~30 lines)
- **Parallel?**: Yes — independent filter function.
- **Notes**: `tasks/WP*.md` uses regex because the naming pattern includes variable slugs (e.g., `tasks/WP01-setup.md`). Directory prefixes use `startswith()` for recursive inclusion of all files under those dirs.

### Subtask T014 – Implement Format Filtering (FR-005)

- **Purpose**: Only upload files with supported inline text formats. Binary and unsupported formats are explicitly skipped.

- **Steps**:
  1. Reuse `is_supported_format()` from WP01 (`namespace.py`)
  2. In `body_upload.py`, add a wrapper that returns an `UploadOutcome` for unsupported formats:
     ```python
     def _check_format(relative_path: str) -> UploadOutcome | None:
         """Return UploadOutcome(skipped) if format unsupported, else None."""
         if not is_supported_format(relative_path):
             ext = Path(relative_path).suffix or "(no extension)"
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason=f"unsupported_format: {ext}",
             )
         return None
     ```

- **Files**: `src/specify_cli/sync/body_upload.py` (extend, ~15 lines)
- **Parallel?**: Yes — independent filter function.

### Subtask T015 – Implement Size Limit + Binary Detection (FR-006)

- **Purpose**: Enforce the 512 KiB inline upload size limit and detect binary files that shouldn't be uploaded.

- **Steps**:
  1. Define constant:
     ```python
     MAX_INLINE_SIZE_BYTES = 512 * 1024  # 512 KiB
     ```
  2. Implement size check:
     ```python
     def _check_size_limit(relative_path: str, size_bytes: int) -> UploadOutcome | None:
         """Return UploadOutcome(skipped) if oversized, else None."""
         if size_bytes > MAX_INLINE_SIZE_BYTES:
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason=f"oversized: {size_bytes} bytes > {MAX_INLINE_SIZE_BYTES} limit",
             )
         return None
     ```
  3. Binary detection is handled implicitly: FR-005 format filtering excludes binary extensions, and the UTF-8 read in T016 catches binary content that slipped through

- **Files**: `src/specify_cli/sync/body_upload.py` (extend, ~15 lines)
- **Parallel?**: Yes — independent filter function.

### Subtask T016 – Implement Content Read + Re-Hash Guard

- **Purpose**: Read the actual file content and verify it matches the hash from the indexer scan. This guards against TOCTOU races where the file changes between indexing and body reading (Design Decision #3).

- **Steps**:
  1. Implement:
     ```python
     import hashlib

     def _read_and_rehash(
         feature_dir: Path,
         relative_path: str,
         expected_hash: str,
     ) -> tuple[str, str] | UploadOutcome:
         """Read file content and verify hash.

         Returns (content, actual_hash) on success, or UploadOutcome on failure.
         """
         file_path = feature_dir / relative_path
         try:
             content = file_path.read_text(encoding="utf-8")
         except FileNotFoundError:
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason="deleted_after_scan",
             )
         except UnicodeDecodeError:
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason="not_valid_utf8",
             )
         except OSError as e:
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason=f"read_error: {e}",
             )

         actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
         if actual_hash != expected_hash:
             return UploadOutcome(
                 artifact_path=relative_path,
                 status=UploadStatus.SKIPPED,
                 reason="content_hash_mismatch",
                 content_hash=actual_hash,
             )

         return content, actual_hash
     ```
  2. The hash comparison uses SHA-256 on the UTF-8 encoded content, matching the dossier `hasher.py` convention

- **Files**: `src/specify_cli/sync/body_upload.py` (extend, ~40 lines)
- **Parallel?**: No — core logic.
- **Notes**: `read_text(encoding="utf-8")` raises `UnicodeDecodeError` for binary files that got past format filtering — this is the safety net for FR-006. The hash must be computed on `content.encode("utf-8")` to match the indexer's convention (check `dossier/hasher.py` for exact algorithm).

### Subtask T017 – Implement prepare_body_uploads() Orchestration

- **Purpose**: The main entry point that WP05 (`dossier_pipeline.py`) calls. Processes a list of `ArtifactRef` objects through all filters, reads valid content, and enqueues upload tasks.

- **Steps**:
  1. Implement:
     ```python
     def prepare_body_uploads(
         artifacts: list[ArtifactRef],
         namespace_ref: NamespaceRef,
         body_queue: OfflineBodyUploadQueue,
         feature_dir: Path,
     ) -> list[UploadOutcome]:
         """Filter artifacts, read content, enqueue body uploads.

         Returns a list of UploadOutcome for every artifact processed
         (including skipped ones for diagnostics per FR-012).
         """
         outcomes: list[UploadOutcome] = []

         for artifact in artifacts:
             # Skip non-present artifacts
             if not artifact.is_present:
                 outcomes.append(UploadOutcome(
                     artifact_path=artifact.relative_path,
                     status=UploadStatus.SKIPPED,
                     reason=f"not_present: {artifact.error_reason or 'unknown'}",
                 ))
                 continue

             # Filter 1: Supported surface (FR-004)
             if not _is_supported_surface(artifact.relative_path):
                 outcomes.append(UploadOutcome(
                     artifact_path=artifact.relative_path,
                     status=UploadStatus.SKIPPED,
                     reason="unsupported_surface",
                 ))
                 continue

             # Filter 2: Supported format (FR-005/FR-006)
             format_skip = _check_format(artifact.relative_path)
             if format_skip is not None:
                 outcomes.append(format_skip)
                 continue

             # Filter 3: Size limit
             size_skip = _check_size_limit(artifact.relative_path, artifact.size_bytes)
             if size_skip is not None:
                 outcomes.append(size_skip)
                 continue

             # Read content + re-hash guard
             result = _read_and_rehash(
                 feature_dir, artifact.relative_path, artifact.content_hash_sha256,
             )
             if isinstance(result, UploadOutcome):
                 outcomes.append(result)
                 continue

             content, actual_hash = result

             # Enqueue
             enqueued = body_queue.enqueue(
                 namespace=namespace_ref,
                 artifact_path=artifact.relative_path,
                 content_hash=actual_hash,
                 content_body=content,
                 size_bytes=len(content.encode("utf-8")),
             )

             outcomes.append(UploadOutcome(
                 artifact_path=artifact.relative_path,
                 status=UploadStatus.QUEUED if enqueued else UploadStatus.ALREADY_EXISTS,
                 reason="enqueued" if enqueued else "already_in_queue",
                 content_hash=actual_hash,
             ))

         return outcomes
     ```
  2. The function produces a diagnostic outcome for EVERY artifact — no silent drops

- **Files**: `src/specify_cli/sync/body_upload.py` (extend, ~60 lines)
- **Parallel?**: No — depends on all filter functions.
- **Notes**: The `ALREADY_EXISTS` status from `enqueue()` (duplicate in queue, not server-side) is distinguished from the server-side `already_exists` that comes from `body_transport.py`. Both are non-error conditions.

### Subtask T018 – Write test_body_upload.py

- **Purpose**: Comprehensive tests for filter logic, re-hash guard, and the orchestration function.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_body_upload.py`
  2. Create test fixtures:
     - Mock `ArtifactRef` objects with various paths, hashes, sizes
     - Temp directory with real files for re-hash tests
     - Mock `OfflineBodyUploadQueue` (or use real one with `tmp_path`)
     - Mock `NamespaceRef` from WP01
  3. Test categories:
     - **Surface filtering**: `spec.md` accepted, `unknown.txt` rejected, `tasks/WP01-foo.md` accepted, `research/deep/analysis.md` accepted, `contracts/api.yaml` accepted, `checklists/req.md` accepted, `meta.json` rejected
     - **Format filtering**: `.md` accepted, `.json` accepted, `.yaml`/`.yml` accepted, `.csv` accepted, `.png` rejected, `.pdf` rejected, no extension rejected
     - **Size limit**: Under limit accepted, at limit accepted, over limit skipped with reason
     - **Re-hash guard**: Matching hash → success; mismatched hash → skipped; deleted file → skipped; binary file → skipped (UnicodeDecodeError); permission error → skipped
     - **prepare_body_uploads()**: Full pipeline with mixed artifacts; verify outcome count matches artifact count; verify enqueue called for valid artifacts; verify all skip reasons are explicit
     - **Non-present artifacts**: `is_present=False` → skipped with `not_present` reason

- **Files**: `tests/specify_cli/sync/test_body_upload.py` (new, ~180 lines)
- **Parallel?**: No — needs all functions from T013-T017.
- **Notes**: For re-hash tests, write real files to `tmp_path` and modify them between "index" and "read" to simulate TOCTOU race.

## Risks & Mitigations

- **Risk**: Hash algorithm mismatch with dossier indexer. **Mitigation**: Check `dossier/hasher.py` for exact SHA-256 input convention (raw bytes vs UTF-8 encoded text). Must match exactly.
- **Risk**: `tasks/WP*.md` regex too narrow or too broad. **Mitigation**: Test with real WP naming patterns from existing features (e.g., `WP01-setup-and-environment.md`).
- **Risk**: Large files cause memory issues when reading content. **Mitigation**: 512 KiB size filter runs BEFORE content read.

## Review Guidance

- Verify surface list matches FR-004 exactly (compare against spec.md)
- Verify format list matches FR-005 exactly
- Verify re-hash uses the SAME algorithm as `dossier/hasher.py`
- Verify every artifact produces an `UploadOutcome` — no silent drops
- Verify `_is_supported_surface()` handles edge cases: trailing slashes, case sensitivity, nested paths
- Run `mypy --strict src/specify_cli/sync/body_upload.py`

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T08:38:20Z – claude-opus – shell_pid=51530 – lane=doing – Assigned agent via workflow command
- 2026-03-09T08:41:58Z – claude-opus – shell_pid=51530 – lane=for_review – Ready for review: prepare_body_uploads() with surface/format/size filters, re-hash guard (raw-bytes matching hasher.py), and full pipeline to OfflineBodyUploadQueue. 41 tests, ruff clean.
- 2026-03-09T08:42:21Z – claude-opus – shell_pid=52547 – lane=doing – Started review via workflow command
- 2026-03-09T08:43:56Z – claude-opus – shell_pid=52547 – lane=done – Review passed: 41/41 tests, 100% coverage, correct raw-bytes hash matching hasher.py, clean filter pipeline, ruff clean | Done override: Review approved: 41/41 tests pass, 100% coverage, correct raw-bytes hash convention, clean ruff. Branch merge pending as part of feature merge workflow.

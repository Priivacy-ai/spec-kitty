---
work_package_id: WP05
title: Dossier Pipeline Orchestration
dependencies:
- WP03
- WP01
requirement_refs: [FR-001, FR-013, FR-014]
base_branch: 047-namespace-aware-artifact-body-sync-WP05-merge-base
base_commit: 86b3def9f0555822d369d0e1a66edf4fc1f9b49f
created_at: '2026-03-09T08:59:44.340051+00:00'
subtasks:
- T024
- T025
- T026
- T027
phase: Phase 3 - Integration
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
- src/specify_cli/dossier/events.py
- src/specify_cli/dossier/indexer.py
- src/specify_cli/sync/dossier_pipeline.py
- tests/specify_cli/sync/test_dossier_pipeline.py
wp_code: WP05
---

# Work Package Prompt: WP05 – Dossier Pipeline Orchestration

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Create `sync_feature_dossier()` entrypoint in `dossier_pipeline.py` that wires indexer → event emission → body upload preparation
- Body uploads are triggered by normal sync, not a manual command (FR-013)
- Partial failures are non-fatal: event emission can succeed while body enqueue fails
- `pytest tests/specify_cli/sync/test_dossier_pipeline.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: FR-001 (body upload as phase of normal sync), FR-013 (subordinate to normal sync), FR-014 (path form agreement)
- **Plan**: Architecture → Data Flow diagram, Module Responsibilities → `dossier_pipeline.py`, Key Design Decision #2 (indexer output as sole input)
- **Existing code**: `src/specify_cli/dossier/indexer.py` — `Indexer.index_feature(feature_dir, mission_type, step_id)` returns `MissionDossier`
- **Existing code**: `src/specify_cli/dossier/events.py` — `emit_mission_dossier_artifact_indexed()` and related emission functions
- **WP01**: `NamespaceRef`, `resolve_manifest_version()`
- **WP02**: `OfflineBodyUploadQueue`
- **WP03**: `prepare_body_uploads()` returns `list[UploadOutcome]`
- **Constraint**: Invoked ONLY by feature-aware sync commands, NOT by `BackgroundSyncService` (plan Architecture section)

**Implementation command**: `spec-kitty implement WP05 --base WP03`

## Subtasks & Detailed Guidance

### Subtask T024 – Create sync_feature_dossier() Entrypoint

- **Purpose**: The central orchestration function that runs the entire dossier sync pipeline for one feature: index artifacts, emit dossier events, and prepare body uploads. This is the ONLY place body uploads are enqueued.

- **Steps**:
  1. Create `src/specify_cli/sync/dossier_pipeline.py`
  2. Define the function signature:
     ```python
     from __future__ import annotations
     import logging
     from pathlib import Path
     from typing import TYPE_CHECKING

     if TYPE_CHECKING:
         from ..dossier.models import MissionDossier
         from .body_queue import OfflineBodyUploadQueue
         from .namespace import NamespaceRef, UploadOutcome

     logger = logging.getLogger(__name__)

     @dataclass
     class DossierSyncResult:
         """Result of a full dossier sync pipeline run."""
         dossier: MissionDossier | None
         events_emitted: int
         body_outcomes: list[UploadOutcome]
         errors: list[str]

         @property
         def success(self) -> bool:
             return self.dossier is not None and not self.errors

     def sync_feature_dossier(
         feature_dir: Path,
         namespace_ref: NamespaceRef,
         body_queue: OfflineBodyUploadQueue,
         mission_type: str = "software-dev",
         step_id: str | None = None,
     ) -> DossierSyncResult:
         """Run full dossier sync: index → emit events → prepare body uploads.

         This is the ONLY entrypoint for body upload preparation.
         BackgroundSyncService only drains already-enqueued work.
         """
     ```
  3. The function coordinates three sequential steps (see T025)
  4. Returns a `DossierSyncResult` for caller diagnostics

- **Files**: `src/specify_cli/sync/dossier_pipeline.py` (new, ~40 lines initially)
- **Parallel?**: No — entry point for the module.

### Subtask T025 – Wire Indexer → Event Emission → Body Upload

- **Purpose**: Implement the three-step pipeline inside `sync_feature_dossier()`.

- **Steps**:
  1. **Step 1 — Index**:
     ```python
     from ..dossier.indexer import Indexer

     indexer = Indexer()
     try:
         dossier = indexer.index_feature(feature_dir, mission_type, step_id)
     except Exception as e:
         logger.error("Indexer failed for %s: %s", feature_dir, e)
         return DossierSyncResult(
             dossier=None, events_emitted=0, body_outcomes=[], errors=[str(e)],
         )
     ```

  2. **Step 2 — Emit dossier events** (existing behavior, unchanged):
     ```python
     from ..dossier.events import emit_mission_dossier_artifact_indexed

     events_emitted = 0
     for artifact in dossier.artifacts:
         try:
             emit_mission_dossier_artifact_indexed(
                 feature_slug=namespace_ref.feature_slug,
                 artifact_key=artifact.artifact_key,
                 artifact_class=artifact.artifact_class,
                 relative_path=artifact.relative_path,
                 content_hash=artifact.content_hash_sha256,
                 size_bytes=artifact.size_bytes,
                 is_present=artifact.is_present,
                 # ... other fields as needed by the existing emission function
             )
             events_emitted += 1
         except Exception as e:
             logger.warning("Event emission failed for %s: %s", artifact.relative_path, e)
     ```
     Note: Check the actual signature of `emit_mission_dossier_artifact_indexed()` in `dossier/events.py` — it may differ from the above. Adapt accordingly.

  3. **Step 3 — Prepare body uploads** (new, from WP03):
     ```python
     from .body_upload import prepare_body_uploads

     body_outcomes = prepare_body_uploads(
         artifacts=dossier.artifacts,
         namespace_ref=namespace_ref,
         body_queue=body_queue,
         feature_dir=feature_dir,
     )
     ```

  4. Return `DossierSyncResult(dossier=dossier, events_emitted=events_emitted, body_outcomes=body_outcomes, errors=[])`

- **Files**: `src/specify_cli/sync/dossier_pipeline.py` (extend, ~50 lines)
- **Parallel?**: No — sequential pipeline steps.
- **Notes**: Check `dossier/events.py` for exact function signatures before implementing. The event emission functions may take additional parameters like `wp_id`, `step_id`, or require an `EventEmitter` instance. Adapt the call accordingly.

### Subtask T026 – Handle Partial Failures

- **Purpose**: Ensure body upload preparation failure does not abort dossier event emission, and vice versa. Each step is independent.

- **Steps**:
  1. Wrap body upload preparation in try/except:
     ```python
     try:
         body_outcomes = prepare_body_uploads(
             artifacts=dossier.artifacts,
             namespace_ref=namespace_ref,
             body_queue=body_queue,
             feature_dir=feature_dir,
         )
     except Exception as e:
         logger.error("Body upload preparation failed for %s: %s", feature_dir, e)
         body_outcomes = []
         errors.append(f"body_upload_preparation_failed: {e}")
     ```
  2. Event emission errors are already logged per-artifact in T025 — they don't abort the pipeline
  3. The pipeline returns a `DossierSyncResult` even on partial failure, so callers can inspect what succeeded
  4. Log a summary at the end:
     ```python
     queued = sum(1 for o in body_outcomes if o.status == UploadStatus.QUEUED)
     skipped = sum(1 for o in body_outcomes if o.status == UploadStatus.SKIPPED)
     logger.info(
         "Dossier sync for %s: %d events emitted, %d bodies queued, %d skipped",
         namespace_ref.feature_slug, events_emitted, queued, skipped,
     )
     ```

- **Files**: `src/specify_cli/sync/dossier_pipeline.py` (extend, ~20 lines)
- **Parallel?**: No — error handling for the pipeline.
- **Notes**: This ensures the spec requirement that "body upload is subordinate to normal sync" (FR-013) — sync never fails because of body upload issues.

### Subtask T027 – Write test_dossier_pipeline.py

- **Purpose**: Integration tests for the orchestration pipeline.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_dossier_pipeline.py`
  2. Create fixtures:
     - Mock `Indexer` returning a `MissionDossier` with sample `ArtifactRef` list
     - Mock event emission functions
     - Real `OfflineBodyUploadQueue` with `tmp_path` DB
     - Real filesystem with sample feature files in `tmp_path`
     - `NamespaceRef` from WP01
  3. Test categories:
     - **Happy path**: Index returns artifacts → events emitted → bodies enqueued → result.success is True
     - **Indexer failure**: Indexer raises exception → result.dossier is None, result.errors non-empty, no events or bodies
     - **Event emission failure**: One event fails → rest still emitted, bodies still enqueued
     - **Body preparation failure**: prepare_body_uploads raises → events still emitted, result.errors includes body failure
     - **Empty dossier**: No artifacts → 0 events, 0 bodies, result.success True
     - **Mixed artifacts**: Some supported, some unsupported → only supported enqueued
     - **Result diagnostics**: Verify `events_emitted` count, `body_outcomes` list, `errors` list

- **Files**: `tests/specify_cli/sync/test_dossier_pipeline.py` (new, ~150 lines)
- **Parallel?**: No — needs all functions from T024-T026.
- **Notes**: Mock the `Indexer` at the import boundary (`patch("specify_cli.sync.dossier_pipeline.Indexer")`). Use real files for body content read tests.

## Risks & Mitigations

- **Risk**: Existing dossier event emission API differs from expected signature. **Mitigation**: Read `dossier/events.py` before implementing; adapt call sites.
- **Risk**: Circular import between `sync/dossier_pipeline.py` and `dossier/indexer.py`. **Mitigation**: Use `TYPE_CHECKING` guards for dossier imports.
- **Risk**: Feature-aware sync commands may not exist yet or have a different integration point. **Mitigation**: This WP creates the entrypoint function; WP06 wires it into the runtime. The actual call site integration depends on existing sync command structure.

## Review Guidance

- Verify `sync_feature_dossier()` is the ONLY place `prepare_body_uploads()` is called
- Verify partial failure handling: body failure does NOT abort events, and vice versa
- Verify `DossierSyncResult` contains enough diagnostic info for callers
- Verify indexer is called with the correct parameters (match `dossier/indexer.py` signature)
- Check that no new event types are introduced — existing dossier events are reused
- Run `mypy --strict src/specify_cli/sync/dossier_pipeline.py`

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T08:59:44Z – claude-opus – shell_pid=57622 – lane=doing – Assigned agent via workflow command
- 2026-03-09T09:03:06Z – claude-opus – shell_pid=57622 – lane=for_review – Ready for review: sync_feature_dossier() orchestrates indexer → event emission → body upload with partial failure isolation. 14 tests, ruff clean.
- 2026-03-09T09:56:58Z – claude-opus – shell_pid=11265 – lane=doing – Started review via workflow command
- 2026-03-09T09:58:50Z – claude-opus – shell_pid=11265 – lane=done – Review passed: 14/14 tests, 100% coverage, ruff clean, all 9 API signatures verified matching. sync_feature_dossier() is sole caller of prepare_body_uploads(). Partial failure isolation confirmed in both directions. | Done override: Review approved pre-merge; branch ready to merge to 2.x

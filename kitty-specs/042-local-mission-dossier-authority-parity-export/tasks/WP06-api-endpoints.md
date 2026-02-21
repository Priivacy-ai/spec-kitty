---
work_package_id: WP06
title: Dashboard API Endpoints
lane: "for_review"
dependencies:
- WP04
- WP05
base_branch: 042-local-mission-dossier-authority-parity-export-WP06-merge-base
base_commit: 1bf5196379830703d153f67da65abff9469ed59d
created_at: '2026-02-21T15:59:41.476706+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
feature_slug: 042-local-mission-dossier-authority-parity-export
shell_pid: "98799"
agent: "coordinator"
---

# WP06: Dashboard API Endpoints

**Objective**: Expose 4 REST endpoints for dossier access in local dashboard. Endpoints provide overview, artifact listing (with filtering), detail views, and snapshot export for SaaS import. Implement adapter pattern for future FastAPI migration.

**Priority**: P1 (Enables dashboard UI)

**Scope**:
- 4 dossier endpoints (overview, list, detail, export)
- Filtering by class, wp_id, step_id
- Stable ordering (lexicographic by artifact_key)
- Truncation for large artifacts (>5MB)
- Handler integration with existing dashboard
- Adapter interface for future migration

**Test Criteria**:
- All endpoints return valid JSON
- Filtering works (class=output returns only output)
- Detail endpoint truncates large files
- Export returns snapshot JSON (SaaS-compatible)

---

## Context

Phase 2 brings dossier system online: API endpoints expose indexing/snapshot results to local dashboard UI (WP07) and SaaS backend (via export). The 4 endpoints follow REST conventions and integrate with existing dashboard handler pattern.

**Key Requirements**:
- **FR-007**: System MUST expose dashboard API endpoints (4 types)
- **FR-008**: System MUST support filtering by class, wp_id, step_id
- **SC-001**: API responses <500ms for full catalog

**Dashboard Context**:
- Existing dashboard: `src/specify_cli/dashboard/`
- Handler pattern: HTTPServer + handler methods + router dispatch
- Future migration: Defer to post-042 (Decision 1 in plan.md)

---

## Detailed Guidance

### T028: Implement GET /api/dossier/overview Endpoint

**What**: Return high-level dossier summary (completeness, counts, hashes).

**How**:
1. Create DossierOverviewResponse model:
   ```python
   class DossierOverviewResponse(BaseModel):
       feature_slug: str
       completeness_status: str  # "complete" | "incomplete" | "unknown"
       parity_hash_sha256: str
       artifact_counts: dict  # {total, required, required_present, required_missing, optional, optional_present}
       missing_required_count: int
       last_scanned_at: Optional[datetime]
   ```
2. Implement handler method in DossierHandler:
   ```python
   def handle_dossier_overview(self, feature_slug: str) -> DossierOverviewResponse:
       """GET /api/dossier/overview?feature={feature_slug}"""
       # Load latest snapshot
       snapshot = load_snapshot(self.repo_root / "kitty-specs" / feature_slug, feature_slug)
       if not snapshot:
           return error_response("Dossier not found", 404)

       return DossierOverviewResponse(
           feature_slug=feature_slug,
           completeness_status=snapshot.completeness_status,
           parity_hash_sha256=snapshot.parity_hash_sha256,
           artifact_counts={
               "total": snapshot.total_artifacts,
               "required": snapshot.required_artifacts,
               "required_present": snapshot.required_present,
               "required_missing": snapshot.required_missing,
               "optional": snapshot.optional_artifacts,
               "optional_present": snapshot.optional_present,
           },
           missing_required_count=snapshot.required_missing,
           last_scanned_at=snapshot.computed_at,
       )
   ```
3. Route: GET /api/dossier/overview
4. Query params: feature={feature_slug}
5. Response: 200 with JSON, or 404 if not found

**Test Requirements**:
- Returns valid JSON with all fields
- Correct artifact counts
- Correct completeness status
- 404 if feature not found

---

### T029: Implement GET /api/dossier/artifacts Endpoint

**What**: List all artifacts with filtering and stable ordering.

**How**:
1. Create ArtifactListResponse model:
   ```python
   class ArtifactListItem(BaseModel):
       artifact_key: str
       artifact_class: str
       relative_path: str
       size_bytes: int
       wp_id: Optional[str]
       step_id: Optional[str]
       is_present: bool
       error_reason: Optional[str]

   class ArtifactListResponse(BaseModel):
       total_count: int
       filtered_count: int
       artifacts: List[ArtifactListItem]
       filters_applied: dict  # {class, wp_id, step_id, required_only}
   ```
2. Implement handler:
   ```python
   def handle_dossier_artifacts(self, feature_slug: str, **filters) -> ArtifactListResponse:
       """GET /api/dossier/artifacts?feature={feature_slug}&class=output&wp_id=WP01&step_id=plan&required_only=true"""
       # Load snapshot + artifacts
       snapshot = load_snapshot(...)
       dossier = load_dossier(...)  # Need full dossier for filtering

       # Apply filters
       filtered = dossier.artifacts
       if filters.get('class'):
           filtered = [a for a in filtered if a.artifact_class == filters['class']]
       if filters.get('wp_id'):
           filtered = [a for a in filtered if a.wp_id == filters['wp_id']]
       if filters.get('step_id'):
           filtered = [a for a in filtered if a.step_id == filters['step_id']]
       if filters.get('required_only') == 'true':
           filtered = [a for a in filtered if a.required_status == 'required']

       # Sort by artifact_key (stable ordering)
       filtered = sorted(filtered, key=lambda a: a.artifact_key)

       # Build response
       return ArtifactListResponse(
           total_count=len(dossier.artifacts),
           filtered_count=len(filtered),
           artifacts=[
               ArtifactListItem(
                   artifact_key=a.artifact_key,
                   artifact_class=a.artifact_class,
                   relative_path=a.relative_path,
                   size_bytes=a.size_bytes,
                   wp_id=a.wp_id,
                   step_id=a.step_id,
                   is_present=a.is_present,
                   error_reason=a.error_reason,
               )
               for a in filtered
           ],
           filters_applied=filters,
       )
   ```
3. Route: GET /api/dossier/artifacts
4. Query params: feature, class (optional), wp_id (optional), step_id (optional), required_only (optional)
5. Response: 200 with JSON list

**Filtering Rules**:
- class: One of {input, workflow, output, evidence, policy, runtime}
- wp_id: Exact match (e.g., "WP01")
- step_id: Exact match (e.g., "plan")
- required_only: Boolean (true/false)
- Multiple filters AND together

**Test Requirements**:
- Returns all artifacts if no filters
- Filters work independently and combined
- Stable ordering (by artifact_key)
- Correct counts (total vs filtered)

---

### T030: Implement GET /api/dossier/artifacts/{artifact_key} Endpoint

**What**: Return artifact detail with full-text content (or truncation notice).

**How**:
1. Create ArtifactDetailResponse model:
   ```python
   class ArtifactDetailResponse(BaseModel):
       artifact_key: str
       artifact_class: str
       relative_path: str
       content_hash_sha256: Optional[str]
       size_bytes: int
       wp_id: Optional[str]
       step_id: Optional[str]
       required_status: str
       is_present: bool
       error_reason: Optional[str]

       # Full content (or truncation notice)
       content: Optional[str]  # Full text if <5MB
       content_truncated: bool
       truncation_notice: Optional[str]
       media_type_hint: str  # "markdown" | "json" | "yaml" | "text"

       indexed_at: datetime
   ```
2. Implement handler:
   ```python
   def handle_dossier_artifact_detail(self, feature_slug: str, artifact_key: str) -> ArtifactDetailResponse:
       """GET /api/dossier/artifacts/{artifact_key}"""
       # Load artifact from dossier
       dossier = load_dossier(feature_slug)
       artifact = None
       for a in dossier.artifacts:
           if a.artifact_key == artifact_key:
               artifact = a
               break

       if not artifact:
           return error_response(f"Artifact {artifact_key} not found", 404)

       # Load full content if present and <5MB
       content = None
       content_truncated = False
       truncation_notice = None
       if artifact.is_present:
           file_path = dossier.feature_dir / artifact.relative_path
           if artifact.size_bytes < 5242880:  # 5MB
               try:
                   content = file_path.read_text(encoding='utf-8')
               except Exception as e:
                   truncation_notice = f"Could not read: {e}"
           else:
               content_truncated = True
               truncation_notice = f"File {artifact.size_bytes / 1024 / 1024:.1f}MB, content not included"

       # Media type hint
       media_type_hint = infer_media_type(artifact.relative_path)

       return ArtifactDetailResponse(
           artifact_key=artifact.artifact_key,
           artifact_class=artifact.artifact_class,
           relative_path=artifact.relative_path,
           content_hash_sha256=artifact.content_hash_sha256,
           size_bytes=artifact.size_bytes,
           wp_id=artifact.wp_id,
           step_id=artifact.step_id,
           required_status=artifact.required_status,
           is_present=artifact.is_present,
           error_reason=artifact.error_reason,
           content=content,
           content_truncated=content_truncated,
           truncation_notice=truncation_notice,
           media_type_hint=media_type_hint,
           indexed_at=artifact.indexed_at,
       )

   def infer_media_type(file_path: str) -> str:
       """Infer media type from extension."""
       ext = Path(file_path).suffix.lower()
       if ext in ['.md']:
           return 'markdown'
       if ext in ['.json']:
           return 'json'
       if ext in ['.yaml', '.yml']:
           return 'yaml'
       return 'text'
   ```
3. Route: GET /api/dossier/artifacts/{artifact_key}
4. Response: 200 with JSON, or 404 if artifact not found

**Test Requirements**:
- Returns artifact detail
- Content included if <5MB
- Truncation notice if >5MB
- Media type hint correct
- 404 if artifact not found

---

### T031: Implement GET /api/dossier/snapshots/export Endpoint

**What**: Export snapshot JSON for SaaS import.

**How**:
1. Implement handler:
   ```python
   def handle_dossier_snapshot_export(self, feature_slug: str) -> dict:
       """GET /api/dossier/snapshots/export?feature={feature_slug}"""
       snapshot = load_snapshot(feature_slug)
       if not snapshot:
           return error_response("Snapshot not found", 404)

       # Return snapshot as JSON (serializable)
       return {
           "feature_slug": snapshot.feature_slug,
           "snapshot_id": snapshot.snapshot_id,
           "total_artifacts": snapshot.total_artifacts,
           "required_artifacts": snapshot.required_artifacts,
           "required_present": snapshot.required_present,
           "required_missing": snapshot.required_missing,
           "optional_artifacts": snapshot.optional_artifacts,
           "optional_present": snapshot.optional_present,
           "completeness_status": snapshot.completeness_status,
           "parity_hash_sha256": snapshot.parity_hash_sha256,
           "artifact_summaries": snapshot.artifact_summaries,
           "computed_at": snapshot.computed_at.isoformat(),
       }
   ```
2. Route: GET /api/dossier/snapshots/export
3. Query params: feature={feature_slug}
4. Response: 200 with JSON snapshot (SaaS import-compatible)

**Export Format**:
- JSON representation of MissionDossierSnapshot
- All fields included (for SaaS audit trail)
- Timestamps in ISO format

**Test Requirements**:
- Returns valid JSON
- All fields present
- Timestamps ISO format
- 404 if snapshot not found

---

### T032: Router Dispatch Rules

**What**: Integrate dossier handlers into dashboard request dispatcher.

**How**:
1. Modify dashboard handler router (src/specify_cli/dashboard/handlers/router.py):
   ```python
   def do_GET(self):
       """Route incoming GET request."""
       if self.path.startswith('/api/dossier/'):
           self.handle_dossier_route()
       else:
           # Existing routes...

   def handle_dossier_route(self):
       """Dispatch dossier API requests."""
       # Extract feature_slug, artifact_key from path
       if '/artifacts/' in self.path:
           artifact_key = self.path.split('/artifacts/')[-1].split('?')[0]
           response = self.dossier_handler.handle_dossier_artifact_detail(artifact_key)
       elif '/artifacts' in self.path:
           filters = parse_query_params(self.path)
           response = self.dossier_handler.handle_dossier_artifacts(**filters)
       elif '/snapshots/export' in self.path:
           filters = parse_query_params(self.path)
           response = self.dossier_handler.handle_dossier_snapshot_export(**filters)
       elif '/overview' in self.path:
           filters = parse_query_params(self.path)
           response = self.dossier_handler.handle_dossier_overview(**filters)
       else:
           self.send_error(404, "Dossier endpoint not found")
           return

       # Return response
       self.send_response(200)
       self.send_header('Content-Type', 'application/json')
       self.end_headers()
       self.wfile.write(json.dumps(response.dict() if hasattr(response, 'dict') else response).encode())
   ```
2. Create DossierHandler mixin:
   ```python
   class DossierHandler:
       def __init__(self, repo_root: Path):
           self.repo_root = repo_root

       def handle_dossier_overview(self, feature_slug: str):
           # Implementation from T028

       def handle_dossier_artifacts(self, **filters):
           # Implementation from T029

       def handle_dossier_artifact_detail(self, artifact_key: str):
           # Implementation from T030

       def handle_dossier_snapshot_export(self, feature_slug: str):
           # Implementation from T031
   ```
3. Mix into dashboard handler class
4. Test route dispatch

**Route Table**:
| Method | Path | Handler |
|--------|------|---------|
| GET | /api/dossier/overview | handle_dossier_overview |
| GET | /api/dossier/artifacts | handle_dossier_artifacts |
| GET | /api/dossier/artifacts/{key} | handle_dossier_artifact_detail |
| GET | /api/dossier/snapshots/export | handle_dossier_snapshot_export |

**Test Requirements**:
- All routes dispatched correctly
- Query params parsed
- Error responses for invalid paths

---

### T033: Define Adapter Interface for FastAPI Migration

**What**: Define interface/protocol for handler methods (enables future FastAPI port).

**How**:
1. Create adapter protocol in src/specify_cli/dashboard/handlers/adapter.py:
   ```python
   from typing import Protocol, Any

   class DossierHandlerAdapter(Protocol):
       """Interface for dossier handlers (agnostic to HTTPServer/FastAPI)."""

       def handle_dossier_overview(self, feature_slug: str) -> Any:
           """GET /api/dossier/overview"""
           ...

       def handle_dossier_artifacts(self, feature_slug: str, **filters) -> Any:
           """GET /api/dossier/artifacts"""
           ...

       def handle_dossier_artifact_detail(self, feature_slug: str, artifact_key: str) -> Any:
           """GET /api/dossier/artifacts/{artifact_key}"""
           ...

       def handle_dossier_snapshot_export(self, feature_slug: str) -> Any:
           """GET /api/dossier/snapshots/export"""
           ...
   ```
2. Document interface semantics:
   - All methods return pydantic models (serializable to JSON)
   - Error handling: Return error_response or raise (depends on framework)
   - Framework-agnostic: No HTTPServer/FastAPI specifics
3. Add migration roadmap to plan.md (deferred feature 044)

**Adapter Benefits**:
- Future FastAPI migration: Implement FastAPI routes that wrap these methods
- No modification to dossier logic (pure functions)
- Testable in isolation (mock HTTP framework)

**Test Requirements**:
- Adapter protocol well-defined
- All handler methods comply with protocol
- Testable without HTTP framework

---

## Definition of Done

- [ ] 4 endpoint handlers implemented (overview, list, detail, export)
- [ ] Filtering works (class, wp_id, step_id)
- [ ] Stable ordering implemented (by artifact_key)
- [ ] Large artifacts truncated (>5MB)
- [ ] Router dispatch integrated into dashboard
- [ ] Adapter interface defined (for future migration)
- [ ] All endpoints return valid JSON
- [ ] 404 errors for missing resources
- [ ] SC-001 performance criteria validated (<500ms)
- [ ] FR-007, FR-008 requirements satisfied

---

## Risks & Mitigations

**Risk 1**: Adapter interface doesn't fully decouple HTTPServer/FastAPI
- **Mitigation**: Keep handlers pure (no HTTP context), return models

**Risk 2**: Large artifacts cause memory issues
- **Mitigation**: Stream large artifacts, don't load full content

**Risk 3**: Query param parsing fragile
- **Mitigation**: Use urllib.parse.parse_qs, validate params

**Risk 4**: Router dispatch too complex
- **Mitigation**: Keep dispatch simple, push logic to handlers

---

## Reviewer Guidance

When reviewing WP06:
1. Verify 4 endpoints implemented (overview, list, detail, export)
2. Check filtering logic (class, wp_id, step_id, required_only)
3. Confirm stable ordering (by artifact_key)
4. Verify truncation for >5MB artifacts
5. Check router dispatch correctly routes to handlers
6. Verify adapter interface protocol well-defined
7. Test all endpoints return valid JSON
8. Validate SC-001 (<500ms response times)
9. Check error handling (404s)
10. Confirm FR-007, FR-008 satisfied

---

## Implementation Notes

- **Storage**: api.py (handlers, models, adapter)
- **Dependencies**: WP04 (event payload contracts), WP05 (snapshot), pydantic
- **Estimated Lines**: ~400 (api.py + adapter + tests)
- **Integration Point**: WP07 (UI) fetches from these endpoints; WP10 integration tests
- **Deferred**: FastAPI migration (feature 044)

## Activity Log

- 2026-02-21T15:59:41Z – coordinator – shell_pid=98799 – lane=doing – Assigned agent via workflow command
- 2026-02-21T16:02:26Z – coordinator – shell_pid=98799 – lane=for_review – Ready for review: Dashboard API endpoints (overview, artifacts list, artifact detail, snapshot export) with adapter pattern for FastAPI migration. All 33 tests passing.

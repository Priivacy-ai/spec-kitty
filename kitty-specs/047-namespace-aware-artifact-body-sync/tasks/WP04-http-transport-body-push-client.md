---
work_package_id: WP04
title: HTTP Transport - Body Push Client
lane: "done"
dependencies: [WP01]
base_branch: 047-namespace-aware-artifact-body-sync-WP01
base_commit: 221cac1a3567575e5241d4768086572e970e2e6d
created_at: '2026-03-09T08:45:52.174291+00:00'
subtasks:
- T019
- T020
- T021
- T022
- T023
phase: Phase 2 - Core Logic
assignee: ''
agent: claude-opus
shell_pid: '56289'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-09T07:09:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-002, FR-003, FR-008, FR-010]
---

# Work Package Prompt: WP04 – HTTP Transport - Body Push Client

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting
Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Implement `push_content()` HTTP POST to `/api/dossier/push-content/` in `body_transport.py`
- Classify all response codes into `UploadOutcome` (201, 200, 400, 401, 404, 429, 5xx)
- 404 sub-code dispatch: `index_entry_not_found` (retryable) vs `namespace_not_found` (fatal)
- Request body includes full namespace tuple + artifact payload (FR-002, FR-003)
- `pytest tests/specify_cli/sync/test_body_transport.py` passes with 90%+ coverage

## Context & Constraints

- **Spec**: FR-002 (namespace tuple in requests), FR-003 (artifact payload fields), FR-008 (404 index_entry_not_found retryable)
- **Plan**: Module Responsibilities → `body_transport.py`, Architecture → response classification table
- **Contract**: `kitty-specs/047-namespace-aware-artifact-body-sync/contracts/push-content-api.md`
- **Existing code**: `src/specify_cli/sync/auth.py` — `AuthClient.get_access_token()` for Bearer token
- **Existing code**: `src/specify_cli/sync/batch.py` — Pattern reference for HTTP error categorization
- **Constraint**: Uses `requests` library (already a dependency), not `httpx`
- **Constraint**: No new auth flow — reuse existing `AuthClient` (C-002)

**Implementation command**: `spec-kitty implement WP04 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T019 – Implement push_content() HTTP POST

- **Purpose**: The HTTP client function that sends a single body upload task to the SaaS `/api/dossier/push-content/` endpoint. This is called by `BackgroundSyncService` during body queue drain (WP06).

- **Steps**:
  1. Create `src/specify_cli/sync/body_transport.py`
  2. Implement:
     ```python
     from __future__ import annotations
     import logging
     from typing import TYPE_CHECKING

     import requests

     if TYPE_CHECKING:
         from .body_queue import BodyUploadTask
         from .namespace import UploadOutcome

     logger = logging.getLogger(__name__)

     DEFAULT_TIMEOUT_SECONDS = 30

     def push_content(
         task: BodyUploadTask,
         auth_token: str,
         server_url: str,
         timeout: float = DEFAULT_TIMEOUT_SECONDS,
     ) -> UploadOutcome:
         """POST artifact body to SaaS push_content endpoint.

         Returns UploadOutcome classifying the server response.
         """
         url = f"{server_url.rstrip('/')}/api/dossier/push-content/"
         headers = {
             "Authorization": f"Bearer {auth_token}",
             "Content-Type": "application/json",
         }
         payload = _build_request_body(task)

         try:
             response = requests.post(
                 url, json=payload, headers=headers, timeout=timeout,
             )
         except requests.ConnectionError as e:
             return _connection_error_outcome(task, e)
         except requests.Timeout as e:
             return _timeout_outcome(task, e)

         return _classify_response(task, response)
     ```
  3. Handle `requests.ConnectionError` and `requests.Timeout` as retryable failures

- **Files**: `src/specify_cli/sync/body_transport.py` (new, ~40 lines)
- **Parallel?**: No — core function.

### Subtask T020 – Implement Response Classification

- **Purpose**: Map HTTP response codes to `UploadOutcome` with correct retryable/non-retryable semantics. This classification drives the queue lifecycle in WP06.

- **Steps**:
  1. Implement `_classify_response()`:
     ```python
     def _classify_response(
         task: BodyUploadTask, response: requests.Response,
     ) -> UploadOutcome:
         status = response.status_code

         if status == 201:
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.UPLOADED,
                 reason="stored",
                 content_hash=task.content_hash,
             )

         if status == 200:
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.ALREADY_EXISTS,
                 reason="already_exists",
                 content_hash=task.content_hash,
             )

         if status == 400:
             body = _safe_json(response)
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason=f"bad_request: {body.get('detail', 'unknown')}",
                 content_hash=task.content_hash,
                 retryable=False,
             )

         if status == 401:
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason="unauthorized",
                 content_hash=task.content_hash,
                 retryable=True,  # Auth refresh will fix this
             )

         if status == 404:
             return _dispatch_404(task, response)

         if status == 429:
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason="rate_limited",
                 content_hash=task.content_hash,
                 retryable=True,
             )

         if 500 <= status < 600:
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason=f"server_error: {status}",
                 content_hash=task.content_hash,
                 retryable=True,
             )

         # Unexpected status
         return UploadOutcome(
             artifact_path=task.artifact_path,
             status=UploadStatus.FAILED,
             reason=f"unexpected_status: {status}",
             content_hash=task.content_hash,
             retryable=False,
         )
     ```
  2. Add helper:
     ```python
     def _safe_json(response: requests.Response) -> dict:
         try:
             return response.json()
         except (ValueError, requests.JSONDecodeError):
             return {}
     ```

- **Files**: `src/specify_cli/sync/body_transport.py` (extend, ~70 lines)
- **Parallel?**: No — sequential after T019.

### Subtask T021 – Implement 404 Sub-Code Dispatch

- **Purpose**: Distinguish between `index_entry_not_found` (retryable per FR-008, dossier index not materialized yet) and `namespace_not_found` (non-retryable, namespace doesn't exist on SaaS). This is critical for correctness — treating all 404s the same would either lose retries or create infinite retry loops.

- **Steps**:
  1. Implement:
     ```python
     def _dispatch_404(
         task: BodyUploadTask, response: requests.Response,
     ) -> UploadOutcome:
         """Dispatch 404 based on error_code in response body.

         - index_entry_not_found: Retryable (FR-008). Dossier index not yet materialized.
         - namespace_not_found: Non-retryable. Namespace doesn't exist on SaaS.
         - Unknown/missing error_code: Non-retryable (conservative).
         """
         body = _safe_json(response)
         error_code = body.get("error_code", "")

         if error_code == "index_entry_not_found":
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason="index_entry_not_found (retryable: dossier index not materialized)",
                 content_hash=task.content_hash,
                 retryable=True,
             )

         if error_code == "namespace_not_found":
             return UploadOutcome(
                 artifact_path=task.artifact_path,
                 status=UploadStatus.FAILED,
                 reason="namespace_not_found (non-retryable: namespace does not exist)",
                 content_hash=task.content_hash,
                 retryable=False,
             )

         # Unknown 404 error code — treat as non-retryable
         detail = body.get("detail", "unknown")
         return UploadOutcome(
             artifact_path=task.artifact_path,
             status=UploadStatus.FAILED,
             reason=f"not_found: {detail} (error_code={error_code or 'missing'})",
             content_hash=task.content_hash,
             retryable=False,
         )
     ```

- **Files**: `src/specify_cli/sync/body_transport.py` (extend, ~30 lines)
- **Parallel?**: No — part of response classification.
- **Notes**: The `error_code` field in the 404 response body is the discriminator. If the field is missing or unknown, we default to non-retryable (conservative — prevents infinite retry).

### Subtask T022 – Build Request Body with Namespace Tuple

- **Purpose**: Construct the JSON request payload for the `push_content` endpoint, including all 5 namespace fields plus artifact payload (FR-002, FR-003).

- **Steps**:
  1. Implement:
     ```python
     def _build_request_body(task: BodyUploadTask) -> dict:
         """Build JSON request body from BodyUploadTask.

         Includes:
         - 5 namespace fields (FR-002): project_uuid, feature_slug, target_branch,
           mission_key, manifest_version
         - 4 artifact fields (FR-003): artifact_path, content_hash, hash_algorithm,
           content_body
         """
         return {
             # Namespace identity (FR-002)
             "project_uuid": task.project_uuid,
             "feature_slug": task.feature_slug,
             "target_branch": task.target_branch,
             "mission_key": task.mission_key,
             "manifest_version": task.manifest_version,
             # Artifact payload (FR-003)
             "artifact_path": task.artifact_path,
             "content_hash": task.content_hash,
             "hash_algorithm": task.hash_algorithm,
             "content_body": task.content_body,
         }
     ```
  2. The request body is a flat JSON object — no nesting. This matches the contract in `contracts/push-content-api.md`.

- **Files**: `src/specify_cli/sync/body_transport.py` (extend, ~20 lines)
- **Parallel?**: No — used by T019.

### Subtask T023 – Write test_body_transport.py

- **Purpose**: Test HTTP transport with mocked responses for every response code and 404 sub-code.

- **Steps**:
  1. Create `tests/specify_cli/sync/test_body_transport.py`
  2. Create a `BodyUploadTask` fixture with sample data
  3. Use `unittest.mock.patch("requests.post")` or `responses` library to mock HTTP calls
  4. Test categories:
     - **201 stored**: Returns `UploadOutcome(UPLOADED, "stored")`
     - **200 already_exists**: Returns `UploadOutcome(ALREADY_EXISTS, "already_exists")`
     - **400 bad_request**: Returns `UploadOutcome(FAILED, retryable=False)` with detail
     - **401 unauthorized**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **404 index_entry_not_found**: Returns `UploadOutcome(FAILED, retryable=True)` — FR-008
     - **404 namespace_not_found**: Returns `UploadOutcome(FAILED, retryable=False)` — poison row
     - **404 unknown error_code**: Returns `UploadOutcome(FAILED, retryable=False)` — conservative
     - **404 no JSON body**: Returns `UploadOutcome(FAILED, retryable=False)` — safe fallback
     - **429 rate_limited**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **500 server_error**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **502 bad_gateway**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **Connection error**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **Timeout**: Returns `UploadOutcome(FAILED, retryable=True)`
     - **Request body verification**: Assert `_build_request_body()` includes all 9 fields
     - **Auth header**: Assert `Authorization: Bearer <token>` header sent

- **Files**: `tests/specify_cli/sync/test_body_transport.py` (new, ~200 lines)
- **Parallel?**: No — needs all functions from T019-T022.
- **Notes**: The `responses` library (if available) provides cleaner HTTP mocking than `patch("requests.post")`. Check if it's already in dev dependencies. Otherwise, `unittest.mock` is fine.

## Risks & Mitigations

- **Risk**: SaaS endpoint not yet deployed. **Mitigation**: All tests use HTTP mocks. Contract in `contracts/push-content-api.md` defines expected shapes.
- **Risk**: Response body format doesn't match expected `error_code` field. **Mitigation**: `_safe_json()` + fallback to non-retryable prevents crashes.
- **Risk**: Auth token expires mid-batch. **Mitigation**: `BackgroundSyncService` (WP06) should handle 401 by refreshing auth before retrying. Transport layer just reports `retryable=True`.

## Review Guidance

- Verify request body includes ALL 9 fields (5 namespace + 4 artifact) per FR-002/FR-003
- Verify 404 dispatch logic handles all three cases: `index_entry_not_found`, `namespace_not_found`, unknown
- Verify `retryable` flag is correct for every response code
- Verify connection/timeout errors are retryable
- Verify no `Any` types in function signatures — `mypy --strict`
- Cross-reference with `contracts/push-content-api.md` for response format

## Activity Log

- 2026-03-09T07:09:45Z – system – lane=planned – Prompt created.
- 2026-03-09T08:45:52Z – claude-opus – shell_pid=53573 – lane=doing – Assigned agent via workflow command
- 2026-03-09T08:49:32Z – claude-opus – shell_pid=53573 – lane=for_review – Ready for review: push_content() with full response classification per contract. 404 sub-code dispatch follows contract (unknown 404 = retryable, deviates from WP prompt). 26 tests, 98% coverage, ruff clean.
- 2026-03-09T08:49:57Z – claude-opus – shell_pid=56289 – lane=doing – Started review via workflow command
- 2026-03-09T08:51:50Z – claude-opus – shell_pid=56289 – lane=done – Review passed: push_content() HTTP transport correctly implements contract. All 9 request fields, 404 sub-code dispatch (error field per contract), retryable semantics correct. 26 tests, ruff clean. | Done override: Review approved: merge pending. Code correct per contract, 26 tests passing, ruff clean.

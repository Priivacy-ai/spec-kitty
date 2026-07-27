# API Contract: push_content

**Feature**: 047-namespace-aware-artifact-body-sync
**Date**: 2026-03-09
**Direction**: Client (spec-kitty CLI) → Server (SaaS receiver)
**Status**: Draft (C-003: sender development may proceed against this contract)

## Endpoint

```
POST /api/dossier/push-content/
```

The route is owned by the SaaS receiver. The sender targets this canonical route only; no client-side route configuration or fallback aliases.

## Authentication

```
Authorization: Bearer <access_token>
```

Uses existing `AuthClient` / `CredentialStore` (C-002). No new auth flow.

## Request

### Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <access_token>` |

### Body

```json
{
  "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "feature_slug": "047-namespace-aware-artifact-body-sync",
  "target_branch": "2.x",
  "mission_key": "software-dev",
  "manifest_version": "1.0.0",
  "artifact_path": "spec.md",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "hash_algorithm": "sha256",
  "content_body": "# Feature Specification: ...\n\nFull markdown content here..."
}
```

### Field Definitions

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `project_uuid` | string (UUID4) | yes | Valid UUID4 | Project identity |
| `feature_slug` | string | yes | `\d{3}-[a-z0-9-]+` | Feature identifier |
| `target_branch` | string | yes | Non-empty | Target branch name |
| `mission_key` | string | yes | Non-empty | Mission type key |
| `manifest_version` | string | yes | Non-empty | Artifact manifest data version |
| `artifact_path` | string | yes | Feature-relative path, no `..` | Path matching indexer convention |
| `content_hash` | string | yes | 64 hex chars | SHA-256 of content_body |
| `hash_algorithm` | string | yes | `sha256` | Hash algorithm identifier |
| `content_body` | string | yes | ≤512 KiB UTF-8 | Renderable text content |

### Validation Rules

- All namespace fields (`project_uuid`, `feature_slug`, `target_branch`, `mission_key`, `manifest_version`) must be non-empty.
- `content_hash` must be the SHA-256 hex digest of `content_body` encoded as UTF-8. Server may verify.
- `artifact_path` must not contain `..` path traversal.
- `content_body` must not exceed 524,288 bytes (512 KiB) when UTF-8 encoded.

## Responses

### 201 Created — Stored

```json
{
  "status": "stored",
  "artifact_path": "spec.md",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### 200 OK — Already Exists

```json
{
  "status": "already_exists",
  "artifact_path": "spec.md",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### 400 Bad Request — Validation Error

```json
{
  "error": "validation_error",
  "detail": "content_hash does not match content_body"
}
```

Client action: Log as `failed`, remove from queue (not retryable).

### 401 Unauthorized — Auth Expired

```json
{
  "error": "authentication_required"
}
```

Client action: Keep in queue, wait for auth refresh.

### 404 Not Found — Index Entry Not Found (retryable)

```json
{
  "error": "index_entry_not_found",
  "detail": "No indexed artifact for feature_slug=047-namespace-aware-artifact-body-sync artifact_path=spec.md"
}
```

Client action: Treat as **retryable** (FR-008). The dossier index event may not be materialized yet on the server. Increment retry count and set next_attempt_at with backoff.

### 404 Not Found — Namespace Not Found (non-retryable)

```json
{
  "error": "namespace_not_found",
  "detail": "No namespace for project_uuid=... feature_slug=047-namespace-aware-artifact-body-sync target_branch=2.x"
}
```

Client action: Treat as **non-retryable**. The namespace tuple is malformed or the project/feature has never been registered with SaaS. Log as `failed`, remove from queue. A malformed namespace will never self-heal on retry and must be surfaced as a local diagnostic.

### 429 Too Many Requests

```json
{
  "error": "rate_limited",
  "retry_after": 30
}
```

Client action: Retryable. Use `retry_after` value if provided, otherwise use standard backoff.

### 5xx Server Error

Client action: Retryable with exponential backoff.

## Client Behavior Summary

| Response | UploadOutcome | Queue Action | Retryable |
|----------|---------------|--------------|-----------|
| 201 `stored` | `uploaded` | Remove from queue | N/A |
| 200 `already_exists` | `already_exists` | Remove from queue | N/A |
| 400 | `failed` | Remove from queue | No |
| 401 | N/A | Keep in queue | Yes (after auth refresh) |
| 404 `index_entry_not_found` | N/A | Keep, increment retry | Yes |
| 404 `namespace_not_found` | `failed` | Remove from queue | No |
| 429 | N/A | Keep, increment retry | Yes |
| 5xx | N/A | Keep, increment retry | Yes |
| Connection error | N/A | Keep, increment retry | Yes |

**Critical 404 dispatch rule**: The client MUST inspect the response body `error` field to distinguish `index_entry_not_found` (retryable) from `namespace_not_found` (non-retryable). A bare 404 without a parseable `error` field is treated as retryable (conservative default).

## Backoff Schedule

Per-task exponential backoff:

| Retry | Delay |
|-------|-------|
| 1 | 1 second |
| 2 | 2 seconds |
| 3 | 4 seconds |
| 4 | 8 seconds |
| 5 | 16 seconds |
| 6 | 32 seconds |
| 7 | 64 seconds |
| 8 | 128 seconds |
| 9+ | 300 seconds (5 min cap) |

Formula: `min(2^retry_count, 300)` seconds.

`next_attempt_at` = current time + delay.

## Idempotency

The client always submits the upload request. It does not maintain a local cache of presumed remote content state (FR-010). The receiver is responsible for returning `already_exists` when the content hash for the given namespace + artifact_path already matches. The client classifies `already_exists` as a successful no-op.

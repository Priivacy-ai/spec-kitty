# Feature Specification: Namespace-Aware Artifact Body Sync

**Feature Branch**: `047-namespace-aware-artifact-body-sync`
**Created**: 2026-03-09
**Status**: Draft
**Priority**: P1
**Target Branch**: `2.x`
**Mission**: `software-dev`
**Delivery Mode**: CLI sync sender only

## Summary

Extend spec-kitty so normal sync uploads renderable artifact bodies to SaaS using the same namespace identity already present in local dossier events. The local dashboard remains file-authoritative, but SaaS must receive the same text artifacts so it can render the same feature surfaces without relying on a separate manual content push workflow.

This feature covers the sender side only:

- Discover supported artifact files in `kitty-specs/<feature>/...`
- Upload bodies with the canonical namespace tuple
- Queue and retry uploads durably via the existing offline queue
- Preserve namespace isolation across features and branches

This feature does not cover SaaS UI, SaaS storage design, or project-scoped artifacts (see Out of Scope).

## User Scenarios & Testing

### User Story 1 - Online Sync Uploads Artifact Bodies (Priority: P1)

A developer runs normal sync from a feature worktree and expects SaaS to receive the same text artifacts the local dashboard can display.

**Why this priority**: Without body upload, SaaS can know an artifact exists (via dossier index events) but cannot render `spec.md`, `plan.md`, `tasks.md`, or supporting docs. This is the core value proposition.

**Independent Test**: Run sync for a feature containing `spec.md`, `plan.md`, `tasks.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, `checklists/`, and `tasks/WP*.md`. Verify SaaS receives body uploads for all supported text artifacts with the correct namespace tuple.

**Acceptance Scenarios**:

1. **Given** a feature namespace with `spec.md`, `plan.md`, and `tasks.md`, **When** online sync runs, **Then** body uploads are sent for those files with `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, and `manifest_version`.
2. **Given** a feature with `research/`, `contracts/`, and `checklists/` text artifacts, **When** sync runs, **Then** each supported file is uploaded with its feature-relative path (matching the dossier indexer convention) and content hash.
3. **Given** a feature with work package prompts under `tasks/WP*.md`, **When** sync runs, **Then** those prompt files are uploaded as renderable markdown artifacts.

---

### User Story 2 - Offline/Eventually-Online Delivery (Priority: P1)

A developer syncs while SaaS is unreachable or partially available and expects uploads to complete later without losing artifact identity.

**Why this priority**: Sync already supports offline replay for dossier events. Artifact body delivery must match that resilience model so developers never need to remember a manual re-push.

**Independent Test**: Disconnect SaaS, run sync, restart the CLI, reconnect SaaS, replay queued uploads, and confirm all supported bodies arrive exactly once from the user's perspective.

**Acceptance Scenarios**:

1. **Given** SaaS is offline, **When** sync runs, **Then** artifact body uploads are persisted to the durable local queue instead of being dropped.
2. **Given** the dossier events reach SaaS before the body uploads, **When** queued uploads replay, **Then** the uploads succeed without manual intervention.
3. **Given** SaaS returns a retryable failure, **When** replay runs later, **Then** the upload is retried with backoff and preserved across CLI restarts.

---

### User Story 3 - Namespace Isolation Across Features and Branches (Priority: P1)

A developer works on multiple features or branches in the same project and expects artifact bodies to land in the correct remote namespace every time.

**Why this priority**: The whole point of the sender-side change is to preserve the local namespace semantics instead of collapsing everything into mission-level buckets.

**Independent Test**: Sync two features with the same mission type but different `feature_slug` or `target_branch`. Confirm uploads remain isolated and no artifact body is associated with the wrong namespace.

**Acceptance Scenarios**:

1. **Given** two namespaces share the same `mission_key` but have different `feature_slug` values, **When** both sync, **Then** each upload carries the correct namespace tuple and cannot overwrite the other.
2. **Given** the same feature exists on `main` and `2.x`, **When** both branches sync, **Then** uploads remain isolated by `target_branch`.
3. **Given** repeated uploads of the same file content in the same namespace, **When** sync runs again, **Then** the operation is idempotent and does not create duplicate logical artifacts.

---

### User Story 4 - Unsupported or Unreadable Files Fail Explicitly (Priority: P2)

A developer has non-UTF-8, binary, or oversized files in the artifact tree and expects sync to handle them safely without crashing or silently lying about what SaaS can render.

**Why this priority**: Sync must not abort mid-run because of one bad file. Explicit skip diagnostics are essential for operator trust but are not the core upload path.

**Independent Test**: Include a non-UTF-8 file, a binary file, and an oversized file in supported directories. Confirm sync records an explicit skip reason for each and continues uploading the remaining valid artifacts.

**Acceptance Scenarios**:

1. **Given** an artifact file is not valid UTF-8 text, **When** body upload is attempted, **Then** the upload is skipped with an explicit diagnostic reason.
2. **Given** an artifact file is binary or otherwise unsupported for inline rendering, **When** sync runs, **Then** no body upload is attempted and the skip is recorded.
3. **Given** an artifact exceeds the configured inline upload size limit, **When** sync runs, **Then** the body is skipped according to policy and the outcome is explicit.

### Edge Cases

- **File deleted after index**: A file is indexed but deleted before body upload runs. The upload is recorded as skipped with a concrete reason; it is never silently ignored.
- **Remote index not materialized**: SaaS returns `404 index_entry_not_found` because dossier event materialization has not completed yet. The client treats this as retryable, not fatal.
- **Auth expiry during replay**: Auth expires between event sync and body upload replay. The queued upload remains pending until auth is refreshed; it is not discarded.
- **Same content hash across namespaces**: The same content hash appears in two different namespaces. Deduplication is allowed at the receiver storage layer, but sender requests must still carry the full namespace tuple.
- **Non-renderable research artifacts**: Research artifacts may include non-renderable formats. Only supported inline text formats are uploaded in v1.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Normal `spec-kitty` sync MUST include an artifact body upload phase for supported dossier artifacts. Body upload runs after dossier event emission, within the same sync invocation. | Draft |
| FR-002 | Every body upload request MUST include the canonical namespace tuple: `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, and `manifest_version`. | Draft |
| FR-003 | Every body upload request MUST include `artifact_path`, `content_hash` (SHA-256), `hash_algorithm` (`sha256`), and `content_body` (UTF-8 text). The `artifact_path` MUST be the feature-relative path (e.g., `spec.md`, `tasks/WP01.md`, `research/analysis.md`) consistent with the path emitted by the dossier indexer in `ArtifactIndexed` events, not the repository-absolute path. | Draft |
| FR-004 | The client MUST upload supported text artifacts from these feature-scoped surfaces when present: `spec.md`, `plan.md`, `tasks.md`, `research.md`, `quickstart.md`, `data-model.md`, `research/**`, `contracts/**`, `checklists/**`, and `tasks/WP*.md`. Top-level files are matched by exact name; directory globs recursively include all supported-format files within the directory. | Draft |
| FR-005 | V1 MUST support inline upload for UTF-8 text formats needed by the dashboard renderer: Markdown (`.md`), JSON (`.json`), YAML (`.yaml`, `.yml`), and CSV (`.csv`). | Draft |
| FR-006 | The client MUST NOT attempt inline body upload for binary or unsupported formats in v1; these cases MUST be explicitly logged as skipped with a reason code. | Draft |
| FR-007 | Artifact body uploads MUST be durably queued for replay when SaaS is unavailable or returns a retryable HTTP status (5xx, 429, or 404 `index_entry_not_found`). | Draft |
| FR-008 | `404 index_entry_not_found` from the SaaS upload endpoint MUST be treated as retryable because the remote dossier index may not be materialized yet. | Draft |
| FR-009 | Body upload replay MUST survive CLI restarts. Queued upload tasks are persisted to the existing SQLite offline queue. | Draft |
| FR-010 | Upload behavior MUST be idempotent for repeated sync runs of unchanged artifact bodies. The client MUST always submit the upload request (including `content_hash`). The receiver returns `already_exists` when the content hash matches; the client classifies this as a successful no-op. The client MUST NOT maintain a local cache of presumed remote content state to pre-skip uploads, because such a cache cannot account for receiver-side data loss, scope changes, or prior upload failures. | Draft |
| FR-011 | The client MUST preserve namespace isolation; no upload may omit or substitute any namespace identity field. | Draft |
| FR-012 | The client MUST surface upload results in logs or diagnostics with enough detail to distinguish `uploaded`, `already_exists`, `queued`, `skipped`, and `failed` states per artifact. | Draft |
| FR-013 | Artifact body upload MUST remain subordinate to normal dossier event sync; no separate manual command is required to keep SaaS artifact pages current. | Draft |
| FR-014 | The `artifact_path` in body upload requests MUST use the same path form as the dossier indexer's `ArtifactIndexed` events (feature-relative). Body sync MUST NOT invent a different path convention. If the canonical contract requires repository-relative paths, a normalization step MUST be added to both the indexer and the body uploader so they agree. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Body upload phase completes within a bounded time for a typical feature namespace. | All supported artifacts uploaded within 10 seconds for a feature with up to 30 artifacts on a standard connection. | Draft |
| NFR-002 | Offline queue growth is bounded to prevent unbounded disk usage. | Queue capacity defaults to 100,000 upload tasks and reuses the shared sync queue sizing policy/configuration. | Draft |
| NFR-003 | Retry backoff prevents thundering-herd or tight-loop retry against SaaS. | Exponential backoff starting at 1 second, capped at 5 minutes between retries, tracked per upload task (not globally). The existing queue schema tracks retry count globally per event row; the plan phase MUST address whether the schema needs a per-task backoff timestamp or next-eligible-at column. | Draft |
| NFR-004 | New code maintains existing test coverage standards. | 90%+ line coverage for new modules; mypy --strict passes. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Body sync reuses the existing `OfflineQueue` (SQLite) and `BatchSync` infrastructure. No new persistence backend is introduced. | Draft |
| C-002 | Body sync reuses the existing `AuthClient` and `CredentialStore` for SaaS authentication. No new auth flow is introduced. | Draft |
| C-003 | The SaaS receiver exposes a namespace-aware `push_content` API before this feature ships. Sender development may proceed against a contract/mock. | Draft |
| C-004 | `manifest_version` is the `ExpectedArtifactManifest.manifest_version` value for the active mission type, sourced from `expected-artifacts.yaml`. It versions the artifact-definition set used for completeness/parity, not the CLI binary and not the upload batch. | Draft |
| C-005 | Artifact body sync is scoped to feature directories (`kitty-specs/<feature>/...`) only. Project-scoped artifacts (e.g., `constitution.md` in `.kittify/constitution/`) are out of scope. | Draft |

### Key Entities

- **NamespaceRef**: Canonical sender-side representation of the five-field namespace tuple: `project_uuid`, `feature_slug`, `target_branch`, `mission_key`, and `manifest_version`. Matches the `LocalNamespaceTuple` already used in dossier events.
- **ArtifactBodyUploadTask**: Durable queued unit containing a `NamespaceRef`, `artifact_path` (feature-relative, matching dossier indexer convention), `content_hash` (SHA-256), `content_body` (UTF-8 text), retry count, last error, and queue timestamp.
- **UploadOutcome**: Final classified result for one attempted upload: `uploaded`, `already_exists`, `queued`, `skipped`, or `failed`. Includes a human-readable reason string.
- **SupportedInlineFormat**: Enumeration of file extensions eligible for inline body upload in v1: `.md`, `.json`, `.yaml`, `.yml`, `.csv`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After a successful online sync, SaaS receives renderable bodies for all supported text artifacts in a namespace within 10 seconds.
- **SC-002**: Namespace isolation is preserved: zero cross-namespace upload collisions in tests across features sharing the same mission type.
- **SC-003**: Offline replay persists queued uploads across process restarts with zero lost upload tasks in integration tests.
- **SC-004**: Repeated sync of unchanged artifacts is idempotent: no duplicate logical body delivery in integration tests.
- **SC-005**: `404 index_entry_not_found` is recovered automatically by retry logic in integration tests.
- **SC-006**: Non-UTF-8, binary, and oversized files do not crash sync and are surfaced explicitly as skipped or unsupported.

### Acceptance Criteria

- Body uploads are triggered by normal sync, not a manual sidecar workflow
- All uploads include the canonical namespace tuple (all five fields)
- Durable replay covers temporary SaaS outages and remote-not-ready conditions
- Supported text artifacts from top-level feature files, subdirectories, and WP prompt files are uploaded
- Unsupported artifacts fail explicitly without aborting the rest of sync
- Integration tests cover online, offline, retry, idempotency, and cross-namespace cases

## Assumptions

1. The SaaS receiver will expose a namespace-aware `push_content` API before this feature ships. Sender development may proceed against a contract/mock.
2. Existing sync auth/session handling (`AuthClient`, `CredentialStore`) can be reused for artifact body upload requests without modification.
3. The main parity goal for v1 is renderable text artifacts, not arbitrary binary files.
4. The existing `OfflineQueue` (SQLite, FIFO, retry-aware) can be extended for body upload tasks without architectural replacement.
5. Dossier index events remain the source of truth for artifact existence and metadata; body uploads add renderable content, not artifact identity.
6. The dossier `Indexer` already classifies and hashes feature artifacts; body sync can leverage its scan results rather than re-scanning.

## Out of Scope

1. SaaS namespace model changes and SaaS artifact viewer implementation (separate `spec-kitty-saas` spec)
2. Binary artifact uploads (v1 supports text formats only)
3. Full-text search indexing of uploaded bodies
4. Replacing existing dossier event emission (body uploads are additive)
5. Replacing the local dashboard's file-authoritative model
6. New user-facing CLI commands solely for artifact body upload in v1
7. Project-scoped artifact upload (e.g., `constitution.md`). If needed, this should be a separate project-scoped sync surface, not part of namespace artifact sync.

## Related Artifacts

- Local dossier/parity foundation: `kitty-specs/042-local-mission-dossier-authority-parity-export/spec.md`
- Local dashboard implementation: `src/specify_cli/dashboard/`
- Sync pipeline: `src/specify_cli/sync/`
- Dossier event payloads: `src/specify_cli/dossier/events.py`
- Dossier indexer: `src/specify_cli/dossier/indexer.py`
- Manifest registry: `src/specify_cli/dossier/manifest.py`
- Offline queue: `src/specify_cli/sync/queue.py`
- Project identity: `src/specify_cli/sync/project_identity.py`
- Complementary receiver/viewer work lives in the separate `spec-kitty-saas` spec

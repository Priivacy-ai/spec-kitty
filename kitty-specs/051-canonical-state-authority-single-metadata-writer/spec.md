# Feature Specification: Canonical State Authority & Single Metadata Writer

**Feature Branch**: `051-canonical-state-authority-single-metadata-writer`
**Created**: 2026-03-18
**Status**: Draft
**Input**: Phase 3 + Phase 4 of the 2.x state architecture cleanup plan

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acceptance Reads Canonical State (Priority: P1)

A developer or CI agent runs acceptance validation on a feature. The acceptance logic determines whether all work packages are in the `done` lane by querying the canonical status snapshot (`status.json` / `status.events.jsonl`), not by parsing Activity Log entries from WP markdown bodies. If the Activity Log section is corrupted, deleted, or out of sync, acceptance still produces the correct result.

**Why this priority**: This is the core correctness requirement. Today, acceptance reads Activity Log text to determine lane state, creating a fragile dependency on markdown body content. Fixing this is the single highest-impact change in the sprint.

**Independent Test**: Run acceptance on a feature where all WPs are `done` in the canonical event log but the Activity Log body text has been deleted from every WP file. Acceptance must succeed.

**Acceptance Scenarios**:

1. **Given** a feature with 3 WPs all in `done` lane per `status.events.jsonl`, **When** acceptance validation runs, **Then** it reports all WPs done and proceeds to acceptance metadata write.
2. **Given** a feature with 3 WPs all in `done` lane per `status.events.jsonl` but Activity Log sections deleted from all WP files, **When** acceptance validation runs, **Then** it still reports all WPs done (canonical state is authoritative).
3. **Given** a feature with WP01 in `done` and WP02 in `for_review` per `status.events.jsonl` but WP02's Activity Log falsely says "done", **When** acceptance validation runs, **Then** it correctly reports WP02 as not done (canonical state overrides stale compatibility view).

---

### User Story 2 - All meta.json Writes Go Through One API (Priority: P1)

A developer working on spec-kitty internals needs to write acceptance metadata, VCS lock state, documentation mission state, or merge history to a feature's `meta.json`. Every such write goes through `feature_metadata.py` — there is no other code path that opens and writes `meta.json` directly. The API provides atomic writes, stable formatting, and schema validation.

**Why this priority**: Equally critical to Story 1. The 11 scattered write sites currently produce inconsistent formatting, lack validation, and risk partial writes. Collapsing them is a prerequisite for trustworthy metadata.

**Independent Test**: Search the entire `src/specify_cli/` tree for direct `meta.json` writes (e.g., `json.dump` + `meta` pattern). Only `feature_metadata.py` should contain write operations.

**Acceptance Scenarios**:

1. **Given** any code path that mutates `meta.json`, **When** that code executes, **Then** it calls `feature_metadata.py` API functions — no direct file writes elsewhere.
2. **Given** two concurrent acceptance operations (standard and orchestrator), **When** both complete, **Then** both produce identical metadata structure with the same fields, formatting, and history shape.
3. **Given** a metadata write with invalid schema (e.g., missing required field), **When** the write is attempted, **Then** the API rejects it before touching the file.

---

### User Story 3 - Compatibility Views Remain Readable (Priority: P2)

After a lane transition, the WP frontmatter `lane` field, the Activity Log in the WP body, and the `tasks.md` status block are still updated as compatibility views. They remain human-readable and accurate — but no workflow logic reads them as a source of truth.

**Why this priority**: Removing compatibility views would break tooling expectations (IDE plugins, human review). Keeping them as derived views is necessary for backward compatibility.

**Independent Test**: Move a WP to `for_review` via `emit_status_transition()`. Verify that frontmatter `lane`, Activity Log, and `tasks.md` status block all reflect the transition. Then corrupt the frontmatter `lane` field to a wrong value and verify that `materialize()` still returns the correct lane from the event log.

**Acceptance Scenarios**:

1. **Given** a lane transition emitted via `emit_status_transition()`, **When** the transition completes, **Then** the WP frontmatter `lane` field, Activity Log entry, and `tasks.md` status block all reflect the new lane.
2. **Given** a WP whose frontmatter `lane` has been manually edited to a wrong value, **When** `materialize()` is called, **Then** the returned snapshot shows the correct lane from the event log, ignoring the frontmatter.

---

### User Story 4 - Atomic Metadata Writes (Priority: P2)

When `feature_metadata.py` writes `meta.json`, it uses an atomic write pattern (write to temp file, then rename). If the process is interrupted mid-write, `meta.json` is either the old version or the new version — never a partial/corrupt file.

**Why this priority**: The current non-atomic writes risk corruption on interruption, especially during acceptance where multiple fields are updated.

**Independent Test**: Simulate an interruption during metadata write (e.g., by monkeypatching `os.replace` to raise after temp file creation). Verify `meta.json` retains its previous valid content.

**Acceptance Scenarios**:

1. **Given** a valid `meta.json` and a metadata update operation, **When** the write succeeds, **Then** the file contains the new content with stable formatting (sorted keys, 2-space indent, trailing newline, UTF-8).
2. **Given** a valid `meta.json` and a metadata update that fails mid-write, **When** the failure occurs, **Then** `meta.json` retains its previous content and no temp file is left behind.

---

### User Story 5 - Bounded Acceptance History (Priority: P3)

The `acceptance_history` array in `meta.json` is managed by the metadata API with explicit bounds. When a feature is accepted multiple times (re-acceptance after changes), the history grows but is capped at a configurable maximum to prevent unbounded growth.

**Why this priority**: Not currently a production issue, but establishing the pattern now prevents future problems and demonstrates the metadata API's value.

**Independent Test**: Accept a feature 15 times. Verify `acceptance_history` contains at most the configured maximum entries (most recent retained).

**Acceptance Scenarios**:

1. **Given** a feature accepted 15 times with a history cap of 10, **When** the 15th acceptance completes, **Then** `acceptance_history` contains exactly 10 entries (the 5 oldest dropped).

---

### Edge Cases

- What happens when `status.events.jsonl` is empty or missing? Acceptance should fail with a clear error ("no canonical state found"), not silently fall back to Activity Log.
- What happens when `meta.json` doesn't exist yet and a write is attempted? The API should create it with baseline fields, not crash.
- What happens when `meta.json` has unknown fields from a newer version? The API should preserve unknown fields during read-modify-write (forward compatibility).
- What happens when acceptance runs on a legacy feature that has no event log (pre-status-model)? The migration path (`status/migrate.py`) should be invoked or an explicit error raised — not a silent fallback to Activity Log parsing.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Canonical acceptance reads | As a developer, I want acceptance validation to read `status.json`/`status.events.jsonl` so that workflow correctness doesn't depend on markdown body parsing. | High | Open |
| FR-002 | Single metadata writer module | As a developer, I want all `meta.json` mutations to go through `feature_metadata.py` so that there is one approved write path. | High | Open |
| FR-003 | Extend existing helper | As a developer, I want the new module to extend the existing `write_feature_meta()` from `upgrade/feature_meta.py` so that the formatting convention is preserved. | High | Open |
| FR-004 | Atomic meta.json writes | As a developer, I want `meta.json` writes to use temp-file-then-rename so that partial writes are impossible. | High | Open |
| FR-005 | Schema validation on write | As a developer, I want the metadata API to validate `meta.json` content before writing so that invalid state is rejected. | Medium | Open |
| FR-006 | Compatibility views preserved | As a developer, I want lane transitions to still update WP frontmatter, Activity Log, and tasks.md status block so that human readability is maintained. | High | Open |
| FR-007 | Explicit mutation functions | As a developer, I want named functions for common meta.json operations (e.g., `record_acceptance()`, `set_vcs_lock()`, `update_doc_state()`) so that callers don't do ad-hoc dict surgery. | Medium | Open |
| FR-008 | Bounded acceptance history | As a developer, I want `acceptance_history` to be capped at a configurable maximum so that unbounded growth is prevented. | Low | Open |
| FR-009 | Migrate all 11 write sites | As a developer, I want every existing `meta.json` write site migrated to the new API so that no direct writes remain. | High | Open |
| FR-010 | Unknown field preservation | As a developer, I want the metadata API to preserve unknown fields in `meta.json` during read-modify-write so that forward compatibility is maintained. | Medium | Open |
| FR-011 | Orchestrator parity | As a developer, I want orchestrator acceptance and standard acceptance to produce identical metadata structure so that downstream consumers see consistent data. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Write performance | meta.json write latency must not exceed 50ms p95 on local filesystem | Performance | Medium | Open |
| NFR-002 | Test coverage | All new public functions in `feature_metadata.py` must have unit tests; canonical-state acceptance must have integration tests | Quality | High | Open |
| NFR-003 | No new dependencies | The refactoring must not add new third-party dependencies | Maintainability | High | Open |
| NFR-004 | Minimal diff | Migration of write sites should produce the smallest defensible diff per site | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No compatibility view removal | Compatibility views (frontmatter lane, Activity Log, tasks.md status) must not be removed, only downgraded to derived state | Technical | High | Open |
| C-002 | Phase 3 + 4 scope only | No new state-contract work, .gitignore cleanup, doctor surfaces, or unrelated workflow redesign | Scope | High | Open |
| C-003 | Python 3.11+ | Existing codebase requirement | Technical | High | Open |
| C-004 | Backward compatibility | Legacy features without event logs must get an explicit error, not silent fallback | Technical | Medium | Open |
| C-005 | No new external services | No database, no network calls; filesystem-only state | Technical | High | Open |

### Key Entities

- **StatusEvent**: Immutable record of a lane transition in `status.events.jsonl`. Fields: `event_id`, `feature_slug`, `wp_id`, `from_lane`, `to_lane`, `actor`, `at`, `execution_mode`, `force`, `reason`, `evidence`, `review_ref`.
- **StatusSnapshot**: Materialized view of all WP lanes derived from replaying the event log. Stored in `status.json`. The sole authority for lane state in Phase 2.
- **FeatureMetadata**: The contents of `meta.json` — feature identity, mission config, target branch, acceptance state, VCS lock state, documentation state, merge history. Owned exclusively by `feature_metadata.py`.
- **Compatibility Views**: WP frontmatter `lane` field, WP body Activity Log section, `tasks.md` status block. Derived from canonical state after every transition. Non-authoritative.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Acceptance validation produces the correct result when Activity Log text is deleted from all WP files (canonical state is sole authority).
- **SC-002**: A codebase search for direct `meta.json` file writes outside `feature_metadata.py` returns zero results.
- **SC-003**: Orchestrator acceptance and standard acceptance produce byte-identical `meta.json` structure (excluding timestamps and commit refs).
- **SC-004**: Corrupting any compatibility view (frontmatter lane, Activity Log, tasks.md status) does not change the result of `materialize()` or acceptance validation.
- **SC-005**: All `meta.json` writes use atomic temp-file-then-rename pattern (verified by test).
- **SC-006**: Existing test suite passes without regression after migration (zero new failures attributable to this sprint).

## Assumptions

- The existing `status/emit.py` pipeline and `legacy_bridge.py` compatibility view generation are correct and do not need modification beyond wiring changes.
- The `upgrade/feature_meta.py` helper's formatting convention (2-space indent, `ensure_ascii=False`, trailing newline) is the correct target format.
- Features created before the status model exist in the wild and need an explicit error path, not migration within this sprint.
- The 11 write sites identified in the audit are exhaustive (feature creation, 2x acceptance paths, orchestrator acceptance, VCS locking, 6 doc-state writes, merge history).

## Scope Boundary

### In Scope
- Canonical workflow state cleanup (Phase 3)
- Single-writer metadata cleanup (Phase 4)
- Extend and relocate `write_feature_meta()` to `src/specify_cli/feature_metadata.py`
- Migrate all 11 meta.json write sites
- Tests proving canonical authority and metadata writer behavior

### Out of Scope
- New state-contract work
- `.gitignore` / Git boundary cleanup (Phase 2)
- New doctor surfaces
- User-home credentials/schema cleanup
- Broad atomic-write migration beyond `meta.json`
- Deprecated state-surface removal
- Unrelated workflow redesign
- The P0 requirement-mapping regression (separate fix)

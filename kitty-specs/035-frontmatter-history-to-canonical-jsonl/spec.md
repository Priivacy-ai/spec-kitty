# Feature Specification: Frontmatter History to Canonical JSONL

**Feature Branch**: `035-frontmatter-history-to-canonical-jsonl`
**Created**: 2026-02-09
**Status**: Draft
**Target Branch**: 2.x
**Input**: Comprehensive Upgrade Plan for migrating WP frontmatter history arrays into the canonical status event log (status.events.jsonl), replacing the current bootstrap-only migration with full transition reconstruction.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Full History Import via CLI (Priority: P1)

A spec-kitty user has an existing project with 30+ features and 200+ WP files. Each WP file contains a `history` array in frontmatter that records the complete lane transition timeline (planned, doing, for_review, done, etc.). Today, `spec-kitty agent status migrate` only creates a single bootstrap event per WP (planned -> current lane), losing all intermediate transitions. The user wants all historical transitions preserved in the canonical event log so that status audit trails, timeline views, and reconciliation operate on complete data.

**Why this priority**: This is the core value of the feature. Without full history reconstruction, the event log is an incomplete representation of project history, and all downstream consumers (validate, doctor, reconcile, SaaS sync) operate on incomplete data.

**Independent Test**: Run `spec-kitty agent status migrate --all` on a project with WP files containing multi-step histories. Verify that `status.events.jsonl` contains one event per adjacent transition (not just one bootstrap event per WP).

**Acceptance Scenarios**:

1. **Given** a WP file with history `[planned, doing, for_review, done]`, **When** migration runs, **Then** 3 events are created: `planned->in_progress` (alias resolved), `in_progress->for_review`, `for_review->done`.
2. **Given** a WP file with history `[planned]` and current lane `done`, **When** migration runs, **Then** a gap-fill event `planned->done` is created with force=true.
3. **Given** a WP file with empty/no history and current lane `in_progress`, **When** migration runs, **Then** a single bootstrap event `planned->in_progress` is created with force=true (fallback behavior).
4. **Given** a WP at lane `planned` with no history, **When** migration runs, **Then** zero events are created for that WP (no transition occurred).
5. **Given** history entries containing the alias `doing`, **When** migration runs, **Then** the alias is resolved to `in_progress` before event creation; `doing` never appears in events.

---

### User Story 2 - Idempotent Re-Run Safety (Priority: P1)

A user runs the migration, then runs it again (accidentally, or after an upgrade). The second run must produce zero new events and zero file changes. Additionally, if the user has a project where live events already exist (from normal workflow usage after migration), the migration must not touch that feature's event log.

**Why this priority**: Idempotency is a hard safety requirement. Users must not fear running migration or upgrade commands. Without it, duplicate events corrupt the event log and break the reducer.

**Independent Test**: Run migration twice on the same project. Diff the event files after second run. Zero changes expected.

**Acceptance Scenarios**:

1. **Given** a feature with an existing `status.events.jsonl` containing events from non-migration actors (live workflow), **When** migration runs, **Then** the feature is skipped entirely (no events added, no file modified).
2. **Given** a feature with an existing `status.events.jsonl` where ALL events have `actor` starting with `"migration"` (legacy bootstrap), **When** migration runs, **Then** the existing events are backed up and replaced with full-history reconstruction.
3. **Given** a feature where migration has already produced full-history events (marker `historical_frontmatter_to_jsonl:v1` present in event reasons), **When** migration runs again, **Then** the feature is skipped.
4. **Given** `--dry-run` mode, **When** migration runs, **Then** zero files are written but the report shows the same counts as a real run.

---

### User Story 3 - Automatic Upgrade via `spec-kitty upgrade` (Priority: P2)

A user runs `spec-kitty upgrade` after installing a new version. The upgrade framework automatically detects features with WP files that lack full event history and runs the migration as part of the standard upgrade pipeline. The user does not need to know about `status migrate` as a separate command.

**Why this priority**: Most users interact with `spec-kitty upgrade`, not manual CLI commands. Wiring the migration into the upgrade framework ensures history reconstruction happens automatically for all users.

**Independent Test**: Run `spec-kitty upgrade --dry-run` on a project with unmigrated features. Verify the upgrade migration appears in the plan and reports correct counts.

**Acceptance Scenarios**:

1. **Given** a project with unmigrated features, **When** `spec-kitty upgrade` runs, **Then** the historical status migration is detected and applied automatically.
2. **Given** a project where migration has already run (via CLI or previous upgrade), **When** `spec-kitty upgrade` runs, **Then** the migration reports "already applied" and produces no changes.
3. **Given** a project where the upgrade wrapper has recorded its migration ID in metadata.yaml, **When** upgrade runs again, **Then** the migration is short-circuited before scanning any files.

---

### User Story 4 - Done Evidence Extraction (Priority: P2)

Many WP files that reached `done` have `review_status: approved` and `reviewed_by: <name>` in their frontmatter. When the migration creates a `for_review -> done` transition, it should extract this information into proper `DoneEvidence` rather than always emitting evidence-less forced transitions. This reduces technical debt and makes the event log more honest.

**Why this priority**: Reduces the number of forced transitions without evidence. Every forced done without evidence is a debt item that `status validate` and `status doctor` will flag. Extracting available evidence at migration time eliminates this debt upfront.

**Independent Test**: Migrate a WP file with `review_status: approved` and `reviewed_by: Robert`. Verify the done event contains `DoneEvidence` with a `ReviewApproval`.

**Acceptance Scenarios**:

1. **Given** a WP with `review_status: approved` and `reviewed_by: "Robert"` in frontmatter, **When** migration creates a done transition, **Then** the event includes `DoneEvidence(review=ReviewApproval(reviewer="Robert", verdict="approved", reference="frontmatter-migration:WP01"))`.
2. **Given** a WP with `review_status: has_feedback` (not approved), **When** migration creates a done transition, **Then** the event uses `force=true` with reason explaining no approval evidence, and no `DoneEvidence`.
3. **Given** a WP at done with no review_status or reviewed_by fields, **When** migration creates a done transition, **Then** `force=true` with reason `"historical migration: no evidence in frontmatter"`.

---

### User Story 5 - Backup and Recovery (Priority: P2)

When migration replaces legacy bootstrap-only events with full-history reconstruction, the original events file is backed up. If the user discovers issues, they can restore the backup.

**Why this priority**: The replace-once path (upgrading bootstrap events to full-history events) is a destructive rewrite. Without backup, the user has no recovery path if the migration produces incorrect events.

**Independent Test**: Trigger a replace-once migration. Verify a `.bak` file is created. Verify the backup contains the original events.

**Acceptance Scenarios**:

1. **Given** a feature with migration-only bootstrap events, **When** full-history migration runs, **Then** a backup file `status.events.jsonl.bak.<ISO-timestamp>` is created in the feature directory containing the original events.
2. **Given** a backup file exists, **When** the user needs to restore, **Then** they can copy the backup over the events file and re-run materialization.

---

### User Story 6 - Materialization and Validation After Import (Priority: P3)

After migrating each feature, the system materializes `status.json` from the new event log and runs validation to confirm the migrated events are internally consistent. Failures are reported per-feature without aborting the entire migration run.

**Why this priority**: Materialization ensures status.json is immediately usable after migration. Validation catches any reconstruction errors before they propagate to downstream consumers.

**Independent Test**: Migrate a feature and verify `status.json` exists and matches the event log. Introduce a malformed WP file and verify that feature reports failure while other features still migrate successfully.

**Acceptance Scenarios**:

1. **Given** a successful feature migration, **When** events are written, **Then** `status.json` is materialized immediately from the new event log.
2. **Given** one feature with a malformed WP file and one feature with valid WPs, **When** migration runs on both, **Then** the valid feature migrates successfully and the malformed feature reports failure with a diagnostic message.
3. **Given** a migrated feature, **When** `spec-kitty agent status validate` runs, **Then** no illegal-transition findings are reported for migration-produced events.

---

### Edge Cases

- What happens when a WP file has consecutive duplicate lanes in history (e.g., `[planned, planned, doing]`)? Consecutive duplicates are collapsed before transition pairing; only the transition `planned -> in_progress` is emitted.
- What happens when a WP file's frontmatter is unreadable (malformed YAML)? That WP is skipped with an error detail; other WPs in the feature continue processing.
- What happens when a WP file has a lane value that is not a canonical lane and not a known alias? That WP is skipped with an error detail.
- What happens when the history timestamp is missing or malformed? Fall back to `datetime.now(UTC)` for that entry's timestamp.
- What happens when a feature has no `tasks/` directory? That feature reports "failed" with a diagnostic message.
- What happens if the events file is written partially (crash mid-write)? Events are accumulated in memory and written atomically per feature (all events for one feature are appended in a single operation, not one-by-one).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse WP frontmatter `history` arrays using the canonical Format A structure (keys: `timestamp`, `lane`, `agent`, `shell_pid`, `action`).
- **FR-002**: System MUST normalize history entries by resolving lane aliases (e.g., `doing` -> `in_progress`) before creating events. The alias `doing` MUST never appear in persisted events.
- **FR-003**: System MUST reconstruct transitions by pairing adjacent history entries: entry[i].lane as `from_lane` and entry[i+1].lane as `to_lane`, yielding N-1 transitions for N distinct history entries.
- **FR-004**: System MUST collapse consecutive duplicate lanes in history before pairing (e.g., `[planned, planned, doing]` becomes `[planned, doing]`).
- **FR-005**: System MUST gap-fill from the last history entry's lane to the current frontmatter lane when they differ, creating one additional transition event.
- **FR-006**: System MUST fall back to a single bootstrap event (`planned -> current_lane`) when history is empty or absent, matching current behavior.
- **FR-007**: System MUST emit zero events for WPs at lane `planned` with no meaningful history transitions.
- **FR-008**: System MUST set `force=true` and provide `reason="historical migration"` on ALL migration-generated events, because historical transitions bypassed live guard validation and many transitions (e.g., `planned -> done`) are not in `ALLOWED_TRANSITIONS`.
- **FR-009**: System MUST extract `DoneEvidence` from frontmatter fields `review_status` and `reviewed_by` when creating done transitions, constructing `ReviewApproval(reviewer=reviewed_by, verdict="approved", reference="frontmatter-migration:<wp_id>")`.
- **FR-010**: System MUST use the `agent` field from history entries as the event `actor` when available, falling back to `"migration"` when absent.
- **FR-011**: System MUST preserve the `timestamp` from history entries as the event `at` field, falling back to `datetime.now(UTC)` when absent.
- **FR-012**: System MUST skip features where `status.events.jsonl` contains any events with non-migration actors (live workflow data must not be touched).
- **FR-013**: System MUST backup and replace existing events files that contain ONLY migration-actor events (legacy bootstrap), upgrading them to full-history reconstruction.
- **FR-014**: System MUST skip features where existing events contain the idempotency marker `historical_frontmatter_to_jsonl:v1` in event reasons.
- **FR-015**: System MUST create a backup file (`status.events.jsonl.bak.<ISO-timestamp>`) before replacing any existing events file.
- **FR-016**: System MUST materialize `status.json` from the event log after migrating each feature.
- **FR-017**: System MUST process features independently; one feature's failure MUST NOT abort the entire migration run.
- **FR-018**: System MUST report structured per-feature results: migrated/skipped/failed with reason and per-WP details (events created, history format detected, aliases resolved).
- **FR-019**: System MUST provide a `--dry-run` mode that computes and reports identical results without writing any files.
- **FR-020**: System MUST be callable from both the `status migrate` CLI command and the upgrade migration framework, using the same underlying engine.
- **FR-021**: System MUST register an upgrade migration wrapper so that `spec-kitty upgrade` automatically runs history reconstruction on unmigrated features.
- **FR-022**: System MUST write events atomically per feature (all events for one feature accumulated in memory, then persisted in one operation).
- **FR-023**: System MUST set `execution_mode="direct_repo"` on all migration-generated events.

### Key Entities

- **NormalizedHistoryEntry**: A history entry normalized to a common structure (timestamp, lane, actor) regardless of input format. Intermediate representation used only during reconstruction.
- **TransitionChain**: Ordered list of (from_lane, to_lane, timestamp, actor) tuples derived from a WP's normalized history, ready for StatusEvent creation.
- **MigrationResult / FeatureMigrationResult / WPMigrationDetail**: Structured result types reporting migration outcomes at aggregate, feature, and WP levels.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All historical frontmatter lane transitions across all 200+ WP files are represented in `status.events.jsonl` files, with zero data loss compared to frontmatter history arrays.
- **SC-002**: Running migration a second time on any feature produces zero additional events and zero file changes (idempotent).
- **SC-003**: `spec-kitty agent status validate` passes on all migrated features with no illegal-transition findings.
- **SC-004**: Features with `review_status: approved` and `reviewed_by` in frontmatter produce done events with proper `DoneEvidence` (not evidence-less forced transitions).
- **SC-005**: `status.json` is materialized and valid for every migrated feature immediately after migration completes.
- **SC-006**: `spec-kitty upgrade` detects and applies the migration automatically for projects that have not yet been migrated.
- **SC-007**: Test suite includes explicit cross-branch idempotency simulation (run migration twice with same migration ID expectations, assert zero new events on second pass).

## Assumptions

- All 203 WP files in the project use Format A history structure (`timestamp`, `lane`, `agent`, `shell_pid`, `action`). Format B (`date`, `status`, `by`, `notes`) was theorized but does not exist in the actual codebase. The parser handles Format A only, but is structured to allow future format additions if needed.
- The `doing` alias is the only lane alias currently in use. The parser uses the existing `resolve_lane_alias()` function which handles any aliases defined in `LANE_ALIASES`.
- The 2.x branch is the primary development target. Backport to 0.x is a separate follow-up spec/task after 2.x is stabilized.
- Phase auto-promotion (setting `status_phase` to 1 after migration) is deferred to a follow-up. This feature focuses on the migration engine and idempotency contract.

## Scope Boundaries

### In Scope (2.x)

- History parser for Format A
- Full transition reconstruction replacing bootstrap-only logic
- Idempotency contract (3-layer: marker check, live-events check, migration-actor-only replace)
- DoneEvidence extraction from frontmatter
- Backup/restore for replace-once path
- Materialization after import
- Per-feature error isolation
- Structured reporting
- Dry-run parity
- Upgrade migration wrapper
- Test coverage for all above

### Out of Scope

- Format B history parser (does not exist in the codebase)
- 0.x backport (separate follow-up spec after 2.x stabilization)
- Phase auto-promotion (optional enhancement, not blocking)
- SaaS sync integration (migration is local/offline only)
- CLI `--rollback` flag (users can manually restore from `.bak` files)
- Per-event fingerprint hash deduplication (rejected as over-engineered)
- Generic semantic deduplication heuristics (rejected)
- Rewriting event logs that contain non-migration/live events (rejected as unsafe)

## Backport Readiness Artifacts

When 2.x implementation is complete, the following artifacts MUST be captured for the 0.x backport spec:

1. **Compatibility notes**: Document any 2.x-specific APIs, imports, or patterns used by the migration engine that differ on 0.x.
2. **Backport checklist**: Enumerate every file created/modified on 2.x with instructions for cherry-pick or manual port to 0.x.
3. **Migration ID contract**: The upgrade wrapper on both branches MUST use the same migration ID so that metadata.yaml guards prevent double-execution across branches.
4. **Cross-branch test scenario**: A test that simulates "2.x migrated first, then 0.x upgrade runs" and asserts zero additional events.

## Definition of Done

1. 2.x implementation complete: all new/modified source files committed to 2.x branch.
2. All historical frontmatter lane/history state is represented in `status.events.jsonl`.
3. `status.json` is materialized and validates for every migrated feature.
4. Running migration after initial migration results in no additional events/files changed.
5. Test suite passes with coverage for: full history import, alias normalization, duplicate collapse, gap-fill, empty history fallback, DoneEvidence extraction, 3-layer idempotency, backup creation, dry-run parity, upgrade wrapper integration.
6. Backport readiness artifacts (compatibility notes + backport checklist) are captured in the feature directory.

# Feature Specification: Feature Status State Model Remediation

**Feature Branch**: `034-feature-status-state-model-remediation`
**Created**: 2026-02-08
**Status**: Draft
**Input**: PRD: Feature Status State Model Remediation (Combined v2)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Valid Status Transitions Are Enforced (Priority: P1)

A developer or AI agent moves a work package between lanes. The system validates the transition against a strict 7-lane state machine, rejects illegal transitions, and requires force-audit fields (actor, reason) for any override.

**Why this priority**: Without transition enforcement, status can silently drift into illegal states — the root cause of every observed failure mode.

**Independent Test**: Attempt every legal and illegal lane transition via CLI and verify acceptance/rejection behavior.

**Acceptance Scenarios**:

1. **Given** a WP in `planned`, **When** an agent moves it to `claimed` with an actor identity, **Then** the transition succeeds and a canonical event is appended.
2. **Given** a WP in `planned`, **When** an agent attempts to move it directly to `for_review`, **Then** the transition is rejected with an error identifying the illegal transition.
3. **Given** a WP in `done`, **When** an agent attempts to move it to `in_progress` without `force=true`, **Then** the transition is rejected because `done` is terminal.
4. **Given** a WP in `done`, **When** an agent force-transitions to `in_progress` with actor and reason, **Then** the transition succeeds, the force flag and reason are recorded in the event.
5. **Given** a WP in any lane, **When** the input lane value is `doing`, **Then** the system accepts it as an alias for `in_progress` and persists the canonical value `in_progress`.

---

### User Story 2 - Canonical Event Log and Deterministic Materialization (Priority: P1)

Every status change produces an immutable event in `status.events.jsonl`. A deterministic reducer materializes `status.json` from the log. Running the reducer twice on the same log produces byte-identical output.

**Why this priority**: The append-only log is the architectural foundation — all other features (views, reconciliation, CI checks) derive from it.

**Independent Test**: Append events, run the materializer, verify `status.json` content. Re-run and verify identical output.

**Acceptance Scenarios**:

1. **Given** an empty feature directory, **When** a first status event is emitted, **Then** `status.events.jsonl` is created containing exactly one JSON line with all required fields (event_id, feature_slug, wp_id, from_lane, to_lane, at, actor).
2. **Given** a log with 5 events for 2 WPs, **When** `status materialize` runs, **Then** `status.json` contains current lane for each WP matching the final state after replaying all events.
3. **Given** the same event log, **When** `status materialize` runs twice, **Then** both outputs are byte-identical (determinism).
4. **Given** a log with events appended out of chronological order (simulating a merge), **When** `status materialize` runs, **Then** events are sorted by deterministic key (timestamp, then event_id) and reduced correctly.

---

### User Story 3 - Generated Human-Readable Views (Priority: P1)

After materialization, `tasks.md` status sections and WP frontmatter `lane` values are regenerated from `status.json`. These views are never manually authoritative — they are compatibility caches.

**Why this priority**: Existing workflows (agents, dashboards) read frontmatter lanes and tasks.md. Generating these from canonical state ensures they stay in sync without being authority.

**Independent Test**: Modify `status.json` by running a transition, then verify generated views match.

**Acceptance Scenarios**:

1. **Given** a materialized `status.json` showing WP01 in `for_review`, **When** views are generated, **Then** WP01's frontmatter `lane` field reads `for_review`.
2. **Given** a materialized `status.json`, **When** views are generated twice from the same snapshot, **Then** outputs are identical.
3. **Given** a user manually edits a WP frontmatter `lane` field, **When** `status validate` runs, **Then** a drift warning is emitted identifying the mismatch between frontmatter and canonical state.

---

### User Story 4 - Done-Evidence Contract (Priority: P2)

Moving a WP to `done` requires evidence: reviewer identity, approval reference, and optionally repo/branch/commit information. The system rejects `done` transitions without evidence unless force-overridden.

**Why this priority**: Evidence-backed completion prevents phantom "done" states where no actual work was verified.

**Independent Test**: Attempt `done` transition with and without evidence payloads.

**Acceptance Scenarios**:

1. **Given** a WP in `for_review`, **When** an agent moves it to `done` with reviewer identity and approval reference, **Then** the transition succeeds with evidence recorded in the event.
2. **Given** a WP in `for_review`, **When** an agent moves it to `done` without evidence, **Then** the transition is rejected with an error requiring evidence.
3. **Given** a WP in `for_review`, **When** an agent force-transitions to `done` without evidence but with actor and reason, **Then** the transition succeeds with force flag recorded.

---

### User Story 5 - Rollback-Aware Conflict Resolution (Priority: P2)

When merging branches that contain concurrent status events, explicit reviewer rollback (`for_review` -> `in_progress` with `review_ref`) takes precedence over concurrent forward progression.

**Why this priority**: Without rollback awareness, a concurrent "done" event can override a legitimate review rejection, which is the most dangerous failure mode.

**Independent Test**: Create diverging event logs with a rollback on one branch and forward progression on another, merge, and verify rollback wins.

**Acceptance Scenarios**:

1. **Given** branch A has event `for_review -> done` and branch B has event `for_review -> in_progress` with `review_ref`, **When** logs are merged, **Then** the final materialized state is `in_progress` (reviewer rollback wins).
2. **Given** two branches with non-conflicting events for different WPs, **When** logs are merged, **Then** both WPs reflect their respective final states correctly.
3. **Given** merged logs with duplicate event_ids, **When** the reducer runs, **Then** duplicates are deduplicated and the result is deterministic.

---

### User Story 6 - Validation and CI Checks (Priority: P2)

A `status validate` command checks: event schema validity, transition legality in the log, done-evidence completeness, and drift between materialized state and derived views.

**Why this priority**: Validation is the enforcement mechanism — without it, the canonical model is advisory only.

**Independent Test**: Introduce various violations and verify each is detected.

**Acceptance Scenarios**:

1. **Given** a valid event log and matching `status.json`, **When** `status validate` runs, **Then** it reports success with zero errors.
2. **Given** an event log with an illegal transition (e.g., `planned -> done`), **When** `status validate` runs, **Then** it reports the specific illegal transition with event_id and context.
3. **Given** a `status.json` that disagrees with the reducer output, **When** `status validate` runs, **Then** it reports materialization drift.
4. **Given** a `done` event missing evidence and not marked force, **When** `status validate` runs, **Then** it reports the evidence violation.

---

### User Story 7 - Cross-Repo Reconciliation (Priority: P3)

A `status reconcile` command scans target repositories for WP-linked commits, detects planning-vs-implementation drift, and emits reconciliation events. Supports `--dry-run` and `--apply` modes.

**Why this priority**: Cross-repo reconciliation is additive — it enhances the model but is not required for single-repo workflows to function.

**Independent Test**: Create a feature with WPs implemented in a separate repo, run reconcile in dry-run mode, verify suggested events.

**Acceptance Scenarios**:

1. **Given** a feature with WP01 still `in_progress` in planning but commits merged in target repo, **When** `status reconcile --dry-run` runs, **Then** it reports suggested events to advance WP01 status.
2. **Given** reconciliation suggestions, **When** `status reconcile --apply` runs, **Then** explicit reconciliation events are appended to the canonical log.
3. **Given** no drift between planning and target repos, **When** `status reconcile --dry-run` runs, **Then** it reports no drift found.

---

### User Story 8 - Status Doctor and Workspace Cleanup (Priority: P3)

A `status doctor` command detects stale claims, orphan workspace contexts, and unresolved drift. Workspace cleanup hooks automatically remove orphaned worktrees on merge completion.

**Why this priority**: Operational hygiene prevents workspace residue and stale ownership noise.

**Independent Test**: Create orphaned worktrees and stale claims, run doctor, verify detection and cleanup recommendations.

**Acceptance Scenarios**:

1. **Given** a WP in `claimed` for longer than the staleness threshold, **When** `status doctor` runs, **Then** it reports the stale claim with recommended action.
2. **Given** a worktree for a feature whose WPs are all `done`, **When** merge completes, **Then** orphaned worktrees are cleaned up automatically (or flagged for cleanup).
3. **Given** a workspace context referencing a deleted branch, **When** `status doctor` runs, **Then** it identifies the orphan and suggests resolution.

---

### User Story 9 - Migration from Legacy State (Priority: P2)

A migration command converts existing frontmatter-based lane state into canonical event log entries, bootstrapping the event history for features that predate this system.

**Why this priority**: Without migration, existing features are stranded on the old model and cannot benefit from validation or reconciliation.

**Independent Test**: Create a feature with legacy frontmatter lanes, run migration, verify event log reflects current state.

**Acceptance Scenarios**:

1. **Given** a feature with 4 WPs at various frontmatter lanes (`planned`, `doing`, `for_review`, `done`), **When** the migration command runs, **Then** `status.events.jsonl` contains one bootstrap event per WP reflecting current state, with `doing` mapped to `in_progress`.
2. **Given** a feature that already has `status.events.jsonl`, **When** migration runs, **Then** it skips that feature (idempotent).
3. **Given** migration, **When** `status materialize` runs afterward, **Then** `status.json` matches the pre-migration frontmatter state.

---

### User Story 10 - Dual-Branch Delivery (Priority: P1)

The canonical status model ships on both `2.x` and the `0.1x` line (main/release branches) with maximum parity. A parity matrix documents any unavoidable deltas.

**Why this priority**: Both branch lines must converge on the same canonical model to avoid long-term behavior divergence.

**Independent Test**: Run the same canonical event through both branch lines and verify identical materialization output.

**Acceptance Scenarios**:

1. **Given** the same `status.events.jsonl` file, **When** processed by both `2.x` and `0.1x` reducers, **Then** both produce identical `status.json` output.
2. **Given** the `0.1x` branch, **When** `status reconcile --dry-run` runs, **Then** it operates correctly (Phase 3 dry-run mode).
3. **Given** the `0.1x` branch, **When** SaaS sync is not configured, **Then** the canonical local model still operates correctly with SaaS emission as a no-op.

---

### Edge Cases

- What happens when an event log file is corrupted (invalid JSON on one line)? The reducer must report the specific line and fail rather than silently skip.
- How does the system handle concurrent appends to the same JSONL file from multiple agents? Git merge of append-only files concatenates; deduplication by event_id handles overlaps.
- What happens when a force transition is emitted without an actor? The transition is rejected at emit time — never persisted.
- What if `status.json` is manually deleted? `status materialize` regenerates it from the canonical log.
- What if `status.events.jsonl` is empty but `status.json` exists? `status validate` reports a drift error.
- What happens during the dual-write phase if the legacy frontmatter update succeeds but event append fails? The system must fail the entire operation — no partial writes.
- How are lane aliases handled in event payloads? Aliases are resolved at input boundaries only; events always contain canonical lane values.

## Requirements *(mandatory)*

### Functional Requirements

#### Event Log and Reducer

- **FR-001**: System MUST maintain an append-only event log at `kitty-specs/<feature>/status.events.jsonl` with one JSON object per line.
- **FR-002**: Each event MUST contain: `event_id` (ULID), `feature_slug`, `wp_id`, `from_lane`, `to_lane`, `at` (UTC ISO timestamp), `actor`, `force` (boolean), `reason` (required when force=true), `execution_mode` (worktree|direct_repo).
- **FR-003**: Events transitioning to `done` MUST include an `evidence` payload containing at minimum reviewer identity and approval reference.
- **FR-004**: Events representing review rollback (`for_review -> in_progress`) MUST include `review_ref`.
- **FR-005**: System MUST provide a deterministic reducer that materializes `status.json` from the canonical event log by sorting events by (timestamp, event_id) and reducing to current state per WP.
- **FR-006**: Running the reducer on the same event log MUST produce byte-identical `status.json` output (idempotency).

#### State Machine

- **FR-007**: System MUST enforce a 7-lane state machine: `planned`, `claimed`, `in_progress`, `for_review`, `done`, `blocked`, `canceled`.
- **FR-008**: System MUST enforce the transition matrix: `planned->claimed`, `claimed->in_progress`, `in_progress->for_review`, `for_review->done`, `for_review->in_progress`, `in_progress->planned`, `any->blocked`, `blocked->in_progress`, `any(except done)->canceled`. `done` is terminal unless forced.
- **FR-009**: System MUST enforce guard conditions: `planned->claimed` requires actor; `claimed->in_progress` requires workspace context; `in_progress->for_review` requires subtask evidence or force; `for_review->done` requires reviewer+approval; `for_review->in_progress` requires review feedback reference.
- **FR-010**: Any forced transition MUST require `actor` and `reason` fields.
- **FR-011**: System MUST accept `doing` as an input alias for `in_progress` and MUST persist and emit only canonical lane values.

#### Derived Views

- **FR-012**: After materialization, system MUST regenerate WP frontmatter `lane` fields and `tasks.md` status sections from `status.json`.
- **FR-013**: Generated views are compatibility caches only — the system MUST NOT read them as authoritative state after Phase 2 cutover.

#### Conflict Resolution

- **FR-014**: When merging event logs, system MUST concatenate, deduplicate by `event_id`, sort by deterministic key, and reduce.
- **FR-015**: Explicit reviewer rollback events (`for_review->in_progress` with `review_ref`) MUST take precedence over concurrent forward progression events for the same WP.

#### Commands

- **FR-016**: System MUST provide `status emit` — validate transition and guards, append event, materialize snapshot, emit SaaS telemetry when configured.
- **FR-017**: System MUST provide `status materialize` — rebuild `status.json` and derived views from canonical log.
- **FR-018**: System MUST provide `status validate` — check event schema, transition legality, done-evidence, and derived-view sync.
- **FR-019**: System MUST provide `status reconcile` — scan target repos for WP-linked commits, detect drift, emit reconciliation events in `--dry-run` and `--apply` modes.
- **FR-020**: System MUST provide `status doctor` — detect stale claims, orphan workspace contexts, unresolved drift.

#### Migration

- **FR-021**: System MUST provide a migration command that converts legacy frontmatter lane state to canonical event log entries.
- **FR-022**: Migration MUST map `doing` to `in_progress` in generated bootstrap events.
- **FR-023**: Migration MUST be idempotent — skip features that already have a canonical event log.

#### Dual-Write and Cutover

- **FR-024**: During Phase 1 (dual-write), system MUST write both canonical events AND legacy frontmatter updates on every transition.
- **FR-025**: During Phase 2 (read cutover), system MUST read status exclusively from canonical-derived `status.json`, with frontmatter as generated compatibility view only.
- **FR-026**: System MUST provide a configuration mechanism to control which phase is active (dual-write vs read-cutover).

#### SaaS Integration

- **FR-027**: After appending a canonical event and materializing, system MUST emit a corresponding SaaS telemetry event via the existing sync pipeline when SaaS sync is configured.
- **FR-028**: When SaaS sync is not configured (e.g., 0.1x without SaaS), the canonical local model MUST operate correctly with SaaS emission as a no-op.

#### Workspace Cleanup

- **FR-029**: System MUST provide automated hooks to clean up orphaned worktrees and workspace contexts when a feature's merge completes.

#### Branch Delivery

- **FR-030**: Phases 0-2 MUST ship on both `2.x` and the `0.1x` line with maximum implementation parity.
- **FR-031**: Phase 3 (`status reconcile`) MUST ship on `0.1x` in `--dry-run` mode at minimum; full `--apply` is 2.x-first.
- **FR-032**: A parity matrix MUST document any unavoidable deltas between `2.x` and `0.1x` implementations.

### Key Entities

- **StatusEvent**: An immutable record of a single lane transition. Contains event_id, feature_slug, wp_id, from_lane, to_lane, timestamp, actor, force flag, reason, execution_mode, and optional evidence/review_ref payloads.
- **StatusSnapshot** (`status.json`): The materialized current state of all WPs in a feature, derived deterministically from the event log.
- **TransitionMatrix**: The set of legal (from_lane, to_lane) pairs defining the 7-lane state machine, including guard conditions per transition.
- **DoneEvidence**: Structured payload required for `done` transitions: repos (branch, commit, files), verification results, and reviewer approval.
- **ReconciliationEvent**: A StatusEvent emitted by the reconcile command to align planning state with observed implementation reality.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero features pass CI validation with evidence-missing `done` transitions after Phase 2 cutover.
- **SC-002**: Zero unresolved drift between canonical event log and derived views (`status.json`, frontmatter, tasks.md) across all active features.
- **SC-003**: Same canonical `status.events.jsonl` file processed by both `2.x` and `0.1x` reducers produces identical `status.json` output (cross-branch compatibility).
- **SC-004**: Reducer produces byte-identical output when run multiple times on the same event log (determinism/idempotency verified by test suite).
- **SC-005**: All forced transitions across the codebase contain durable actor and reason fields (queryable via event log grep).
- **SC-006**: Orphaned workspace contexts are detected within one `status doctor` run and resolved within one operational cycle.
- **SC-007**: Migration command successfully converts 100% of existing features with legacy frontmatter state to canonical event logs without data loss.

## Assumptions

- The existing `sync/events.py` infrastructure in `2.x` is stable and can serve as the SaaS fan-out target after canonical event append.
- The current 4-lane model (`planned`, `doing`, `for_review`, `done`) covers all existing features; no features use unlisted lane values.
- Git merge of append-only JSONL files (line-level concatenation) is reliable for the expected concurrency levels.
- The `0.1x` line does not have the SaaS sync infrastructure, so SaaS emission is a no-op there.
- ULID generation is available or can be added as a dependency for event_id generation.

## Constraints

- The `0.1x` line is heading to 1.x then bug-fix mode — changes must be stable, low-risk, and supportable.
- `doing` alias must be maintained until `0.1x` reaches end-of-life.
- Implementation starts on `2.x`, then backports to `0.1x` with parity checks.
- No breaking changes to existing `/spec-kitty.*` slash command interfaces during migration phases.

## Risks

- **Dual-write complexity**: Writing both canonical events and legacy frontmatter during Phase 1 increases surface area for partial-write bugs. Mitigation: atomic operation wrapping with rollback on failure.
- **Merge conflict volume**: Append-only JSONL under high-concurrency multi-agent work may produce large merge diffs. Mitigation: optional per-WP sharding (`status-events/WP01.jsonl`) as a future optimization.
- **0.1x backport scope**: Phases 0-2 on a stabilizing branch is significant. Mitigation: land on 2.x first, thorough test suite, cherry-pick with parity verification.
- **Alias leakage**: `doing` alias could accidentally propagate into persisted events if input boundary normalization is missed. Mitigation: validation at emit time ensures only canonical values are written.

## Dependencies

- Existing `sync/events.py` and `sync/emitter.py` infrastructure (2.x only, for SaaS fan-out).
- Existing `frontmatter.py` module (both branches, for legacy compatibility and view generation).
- ULID library for event_id generation (may need to add dependency).
- Existing `cli/commands/agent/tasks.py` move-task command (primary integration point for transition enforcement).

# Feature Specification: GitHub Observability Event Metadata

**Feature Branch**: `033-github-observability-event-metadata`
**Created**: 2026-02-07
**Status**: Draft
**Target Branch**: 2.x
**Input**: Enrich CLI sync events with git correlation metadata for SaaS-side GitHub linkage

## Overview

The spec-kitty CLI 2.x emits events (WPStatusChanged, FeatureCreated, etc.) with project identity (`project_uuid`, `project_slug`, `team_slug`). However, events lack git-level correlation metadata — branch name, HEAD commit SHA, and repository slug (owner/repo). Without these fields, the SaaS cannot link events to specific GitHub commits, branches, or repositories for observability dashboards.

This feature adds three new correlation fields to every emitted event envelope and normalizes their placement so the SaaS can reliably correlate events with GitHub data — without the CLI ever calling the GitHub API.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Git Branch and SHA in Events (Priority: P1)

A developer runs `spec-kitty implement WP01` on the `033-github-observability-event-metadata-WP01` branch. The emitted WPStatusChanged event includes the current git branch name and HEAD commit SHA so the SaaS can display which branch and commit the status change occurred on.

**Why this priority**: Branch and SHA are the primary correlation keys for GitHub linkage. Without them, the SaaS cannot associate events with specific code changes.

**Independent Test**: Emit a WPStatusChanged event from a known branch/commit, then inspect the event envelope to verify `git_branch` and `head_commit_sha` are present and match `git rev-parse --abbrev-ref HEAD` and `git rev-parse HEAD`.

**Acceptance Scenarios**:

1. **Given** a developer is on branch `feature-branch` at commit `abc1234`, **When** any `emit_*` method is called, **Then** the event envelope includes `git_branch: "feature-branch"` and `head_commit_sha: "abc1234..."` (full 40-char SHA).

2. **Given** a developer switches branches mid-session from `branch-a` to `branch-b`, **When** events are emitted after the switch, **Then** the new events reflect `branch-b` (not the stale value from session start).

3. **Given** a detached HEAD state (e.g., during rebase or checkout of a tag), **When** an event is emitted, **Then** `git_branch` is set to `"HEAD"` (or the detached ref) and `head_commit_sha` contains the current commit SHA.

---

### User Story 2 - Repo Slug in Events (Priority: P1)

A developer working in a repository with `origin` set to `git@github.com:acme/spec-kitty.git` emits events. Each event includes `repo_slug: "acme/spec-kitty"` so the SaaS can map events to the correct GitHub repository.

**Why this priority**: The repo slug enables the SaaS to correlate events with a specific GitHub repository, which is the foundation for all GitHub observability features (linking to PRs, commits, branches).

**Independent Test**: Configure a git remote, emit an event, verify `repo_slug` matches the expected `owner/repo` format.

**Acceptance Scenarios**:

1. **Given** a repo with SSH remote `git@github.com:acme/spec-kitty.git`, **When** an event is emitted, **Then** the envelope includes `repo_slug: "acme/spec-kitty"`.

2. **Given** a repo with HTTPS remote `https://github.com/acme/spec-kitty.git`, **When** an event is emitted, **Then** the envelope includes `repo_slug: "acme/spec-kitty"`.

3. **Given** a `.kittify/config.yaml` with explicit `repo_slug: "custom-org/custom-repo"`, **When** an event is emitted, **Then** the override takes precedence over the auto-derived value.

4. **Given** a `.kittify/config.yaml` with invalid `repo_slug: "not-valid"` (missing slash), **When** an event is emitted, **Then** a warning is logged, and the auto-derived value is used instead.

5. **Given** a repo with no git remote configured, **When** an event is emitted, **Then** `repo_slug` is `null` (not an error — the field is optional).

---

### User Story 3 - Event-Time Git Metadata Resolution (Priority: P2)

Git metadata (branch, SHA) is resolved at event emission time, not at emitter initialization. This ensures correctness during long-running sessions where the developer may switch branches, make commits, or rebase.

**Why this priority**: Stale metadata would silently corrupt correlation data. Correctness of per-event metadata is critical, but the mechanism (caching, TTL) is an implementation detail that can be tuned later.

**Independent Test**: Emit an event, make a commit, emit another event, verify the two events have different `head_commit_sha` values.

**Acceptance Scenarios**:

1. **Given** a developer emits event A at commit `aaa...`, then commits new code (producing commit `bbb...`), **When** event B is emitted, **Then** event B's `head_commit_sha` is `bbb...` (not the stale `aaa...`).

2. **Given** a short TTL cache is used for git metadata, **When** two events are emitted within the TTL window from the same state, **Then** both events have identical metadata (cache hit, no subprocess overhead).

---

### User Story 4 - Backward-Compatible Event Envelope (Priority: P2)

Adding new fields to the event envelope does not break existing SaaS consumers, offline replay, or batch sync. New fields are optional — older consumers ignore them, and events emitted by older CLI versions (without the new fields) continue to work.

**Why this priority**: Breaking backward compatibility would disrupt all existing sync flows. Additive-only changes are essential.

**Independent Test**: Send an event with the new fields to the existing batch sync endpoint, verify it is accepted. Send an event without the new fields, verify it is also accepted.

**Acceptance Scenarios**:

1. **Given** events with `git_branch`, `head_commit_sha`, and `repo_slug` fields, **When** sent via batch sync, **Then** the endpoint accepts them without error.

2. **Given** events without the new fields (from an older CLI version), **When** processed by the SaaS, **Then** they are accepted with the new fields treated as absent/null.

3. **Given** an offline queue with events from before and after this feature, **When** replayed via batch sync, **Then** all events are accepted regardless of whether they contain the new fields.

---

### User Story 5 - Documented Event Envelope (Priority: P3)

The event envelope schema is documented with all correlation fields (existing and new), including field types, when each field is populated, and what consumers can rely on.

**Why this priority**: Documentation enables SaaS developers and third-party integrators to build reliable consumers. Lower priority because the metadata itself is more urgent.

**Independent Test**: Review the documentation and verify every field in the emitted event envelope has a corresponding entry.

**Acceptance Scenarios**:

1. **Given** the event envelope documentation, **When** a developer reads it, **Then** they can determine the type, optionality, and source of every correlation field.

---

### Edge Cases

- **Detached HEAD**: `git_branch` should report `"HEAD"` or the detached ref; `head_commit_sha` should still be populated.
- **No git repository**: If running outside a git repo (unusual but possible), both `git_branch` and `head_commit_sha` should be `null` with a warning logged.
- **Shallow clone**: `git rev-parse HEAD` works in shallow clones; no special handling needed.
- **Git not installed**: If `git` binary is not found, git metadata fields are `null` with a warning. Event emission is not blocked.
- **Non-GitHub remotes** (GitLab, Bitbucket, self-hosted): `repo_slug` derivation should work for any `owner/repo` format; it is not GitHub-specific.
- **Multiple remotes**: Only `origin` is used for auto-derivation. Users with non-standard setups use the config override.
- **Worktree context**: Events emitted from worktrees should reflect the worktree's branch and HEAD, not the main repo's.
- **Invalid config override**: Malformed `repo_slug` in config is warned and ignored (fallback to auto-derived).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include `git_branch` (current branch name) in every emitted event envelope.
- **FR-002**: System MUST include `head_commit_sha` (full 40-character SHA of HEAD) in every emitted event envelope.
- **FR-003**: System MUST include `repo_slug` (owner/repo format) in every emitted event envelope when derivable from the git remote.
- **FR-004**: System MUST resolve `git_branch` and `head_commit_sha` at event emission time (not cached from session startup).
- **FR-005**: System MUST allow manual override of `repo_slug` in `.kittify/config.yaml` under the `project` section.
- **FR-006**: System MUST validate overridden `repo_slug` matches the `owner/repo` format (contains exactly one `/`); if invalid, warn and fall back to auto-derived value.
- **FR-007**: System MUST auto-derive `repo_slug` from `git remote get-url origin` by extracting the `owner/repo` segment.
- **FR-008**: System MUST handle SSH (`git@host:owner/repo.git`) and HTTPS (`https://host/owner/repo.git`) remote URL formats for repo slug derivation.
- **FR-009**: System MUST set `git_branch`, `head_commit_sha`, and `repo_slug` to `null` (not error) when running outside a git repository or when git is unavailable.
- **FR-010**: System MUST NOT block event emission if git metadata resolution fails; missing fields are set to `null`.
- **FR-011**: New event envelope fields MUST be additive-only; existing fields and their semantics are unchanged.
- **FR-012**: Offline replay and batch sync MUST accept events both with and without the new fields.
- **FR-013**: System MUST log a warning (not error) when git metadata cannot be resolved.
- **FR-014**: System MUST resolve git metadata from the correct working directory (worktree-aware) when emitting from a worktree context.

### Key Entities

- **EventEnvelope**: Extended with three new optional fields: `git_branch` (string|null), `head_commit_sha` (string|null), `repo_slug` (string|null). Sits alongside existing fields (`project_uuid`, `project_slug`, `team_slug`, `node_id`, `lamport_clock`).
- **ProjectIdentity**: Extended with optional `repo_slug` field for persistence and override support. Stored in `.kittify/config.yaml` under the `project` section.
- **GitMetadataResolver**: Responsible for resolving branch name and HEAD SHA at event time. May use short-TTL caching to avoid excessive subprocess calls.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of events emitted from a git repository include `git_branch` and `head_commit_sha` in the envelope.
- **SC-002**: 100% of events emitted from a repo with a configured origin remote include a valid `repo_slug` in `owner/repo` format.
- **SC-003**: Events emitted after a branch switch or new commit reflect the updated git state (no stale metadata).
- **SC-004**: Zero regressions in existing sync tests (auth, offline replay, batch sync, WebSocket).
- **SC-005**: Event envelope documentation covers all correlation fields with types, optionality, and derivation rules.
- **SC-006**: Config override for `repo_slug` takes precedence over auto-derived value in 100% of cases.

## Assumptions

- The sync infrastructure (EventEmitter, OfflineQueue, BatchSync, WebSocketClient) is functional on the 2.x branch — this feature extends it, not replaces it.
- Feature 032 (identity-aware events) is merged and `project_uuid`/`project_slug` injection is working.
- The `spec_kitty_events` library's Pydantic `Event` model may need new optional fields, but this is coordinated separately and not a blocker — the CLI can include extra fields in the serialized dict even before the model is updated.
- The SaaS batch sync endpoint accepts unknown fields without error (standard JSON tolerance).

## Out of Scope

- No GitHub API calls from the CLI (the CLI only emits metadata; the SaaS uses it to call GitHub).
- No workflow automation logic (GitHub Actions, webhooks).
- No connector UI/config changes in the SaaS.
- No changes to the `spec_kitty_events` Pydantic Event model (coordinated separately).
- No changes to authentication or authorization flows.

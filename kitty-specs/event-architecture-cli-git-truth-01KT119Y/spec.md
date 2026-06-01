# Event Architecture: Git Semantic Truth + WebSocket Awareness (CLI)

**Mission:** event-architecture-cli-git-truth-01KT119Y
**Type:** software-dev
**Source issues:** spec-kitty #1546, #1547, #1548, #1549 (Epic: spec-kitty-saas #290)

---

## Summary

The CLI's current event system has four distinct problems that undermine data integrity, developer privacy, and real-time collaboration:

1. **Decision events live only in the SQLite queue.** If the queue drains or the SaaS is unreachable, the history of why decisions were made is lost. Git — the system developers already treat as canonical — should be that record.
2. **Event envelopes contain personally identifiable information.** Machine names, filesystem paths, and developer identity fields are written into logs that travel to external services.
3. **The SaaS has no awareness of local commits before a push.** A developer working offline or between pushes is invisible to the build surface.
4. **The queue is flooded with per-extraction glossary noise.** Hundreds of `GlossarySenseUpdated` events per session are queued for a SaaS consumer that derives no value from them.

This mission addresses all four by: routing decision events to git, sanitizing PII at the write boundary, adding a `LocalCommit` WebSocket notification with durable replay, and trimming the glossary queue to only semantically meaningful signals.

---

## Problem Statement

Developers and the SaaS platform rely on a shared understanding of mission state. Today, that shared understanding depends on a SQLite queue that was designed for HTTP batch delivery, not for semantic durability. The result is:

- Decision history is recoverable only while the queue persists and the SaaS is reachable.
- Every event logged or queued carries fields that identify the developer's machine, directory structure, and working hours.
- The SaaS build surface cannot distinguish between "no changes yet" and "changes not yet pushed."
- Queue consumers receive hundreds of low-value extraction events that obscure the few human decisions that matter.

---

## User Scenarios & Testing

### Scenario 1: Decision history survives a queue loss

A developer completes a mission session that included three decision points. The SaaS is offline for the next 24 hours and the local queue is cleared as part of a machine reset. The developer should still be able to see the full decision history — questions asked and answers given — by inspecting the mission's git log. No SaaS availability required.

**Edge case:** The developer answers a decision and immediately closes the CLI before the next operation. The answer event must already be committed to git before the session exits.

### Scenario 2: SaaS sees a local commit before push

A developer transitions a work package to `in_progress`. This triggers a git commit to `kitty-specs/`. Within one second, the SaaS build surface for that mission shows the change as "local only" — even though the developer has not pushed. If the developer's session ends and they reconnect later without having pushed, the SaaS still reflects the local change.

**Edge case:** The developer amends the commit (e.g., to fix a typo). The SaaS must discard the previous unconfirmed frame and display the amended hash.

**Edge case:** The WebSocket connection is not active at commit time. On the next connect, all commits since the last SaaS-confirmed hash are replayed in order.

### Scenario 3: No PII in any persisted event

A developer inspects `kitty-specs/<mission>/decisions.events.jsonl` and `kitty-specs/<mission>/status.events.jsonl` after a session. Neither file contains the developer's machine name, home directory path, name, email address, or the exact clock time when the session started or ended. Any external observer who receives a copy of these files learns nothing about the developer's identity or environment.

**Edge case:** A pre-existing event in the queue that was written before this change already contains PII. The sanitizer applies only at write time going forward; it does not retroactively rewrite existing queue entries.

### Scenario 4: Glossary clarification is durable; extraction noise is not

A developer resolves two glossary clarifications during a mission session. After the session, the SaaS glossary dashboard shows both resolutions. The seed file on disk reflects both immediately. No `GlossarySenseUpdated` events appear anywhere in the SaaS queue — the dozens of per-step extraction events produce no queue writes.

**Edge case:** The local `.kittify/events/glossary/` replay log retains all events for local reconstruction. The trimming applies only to the SaaS-destined queue.

---

## Functional Requirements

### Decision Event Durability (#1546)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | When a decision input is requested, the `DecisionInputRequested` event is appended to `kitty-specs/<mission>/decisions.events.jsonl`. | Proposed |
| FR-002 | When a decision input is answered, the `DecisionInputAnswered` event is appended to the same `decisions.events.jsonl` file. | Proposed |
| FR-003 | `DecisionInputRequested` and `DecisionInputAnswered` events are not written to the SQLite queue. The queue no longer holds these event types. | Proposed |
| FR-004 | After each append, the change to `decisions.events.jsonl` is committed to git on the mission's target branch. Request and answer events may be batched into a single commit if they occur within the same operation; the answer is committed no later than immediately after it is received. | Proposed |
| FR-005 | `decisions.events.jsonl` is append-only and is never rewritten. Each line is a self-contained JSON object. The format matches `status.events.jsonl`. | Proposed |

### PII Sanitization (#1547)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-006 | A dedicated sanitization step removes the following fields from any event envelope before the event is written to a git-tracked file: `machine_name`, `hostname`, `workspace_path`, `developer_name`, `developer_email`. | Proposed |
| FR-007 | Absolute session start and end timestamps are replaced by a relative session duration (elapsed seconds) before writing to any git-tracked file. | Proposed |
| FR-008 | The same sanitization step is applied before writing any event to the SQLite queue. | Proposed |
| FR-009 | Fields that are not PII — `node_id`, `build_id`, `mission_id`, `project_uuid`, `git_branch`, `head_commit_sha`, session duration — are preserved unchanged. The sanitizer preserves fields that are present in the input envelope; it does not add fields that are absent from the original. | Proposed |

### LocalCommit WebSocket Notification (#1548 — full scope)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-010 | After every git commit that touches files under `kitty-specs/`, the CLI emits a `LocalCommit` WebSocket frame to the SaaS. The frame includes: the full commit SHA, `mission_id`, `build_id`, the list of changed files under `kitty-specs/`, and the commit timestamp in UTC. | Proposed |
| FR-011 | A `LocalCommit` frame is never emitted for commits that do not touch `kitty-specs/`, or for commits on non-mission branches. | Proposed |
| FR-012 | Every `LocalCommit` frame is stored in `.kittify/sync-state.json` as a pending entry immediately on emit. When the WebSocket is connected, the frame is also sent immediately and later removed from pending upon receiving a `LocalCommitAck`. When the WebSocket is not connected, the frame remains in pending until the next session connect triggers a flush. | Proposed |
| FR-013 | `.kittify/sync-state.json` records the last commit hash acknowledged by the SaaS (`last_saas_confirmed_hash`) and the list of pending unacknowledged `LocalCommit` frames. | Proposed |
| FR-014 | On WebSocket connect, all pending `LocalCommit` frames in `sync-state.json` whose hashes are more recent than `last_saas_confirmed_hash` are sent to the SaaS in chronological order before normal session activity begins. | Proposed |
| FR-015 | When the SaaS sends a `LocalCommitAck` frame containing a commit hash, `last_saas_confirmed_hash` in `sync-state.json` is updated to that hash and the corresponding pending frame is removed. | Proposed |
| FR-016 | When a commit is amended, the new commit hash supersedes the previous unconfirmed `LocalCommit` frame for that build. A new `LocalCommit` frame is emitted with the new hash; the old pending frame is removed from `sync-state.json`. | Proposed |
| FR-017 | `sync-state.json` contains no PII fields. | Proposed |

### Glossary Queue Reduction (#1549)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-018 | `GlossarySenseUpdated` events are not written to the SQLite queue. No change is made to how these events are written to the local `.kittify/events/glossary/` replay log. | Proposed |
| FR-019 | `GlossaryClarificationResolved` events continue to be written to the SQLite queue. | Proposed |
| FR-020 | `GlossaryClarificationRequested` events continue to be written to the SQLite queue. | Proposed |
| FR-021 | Immediately after a `GlossaryClarificationResolved` event is emitted, the glossary seed file (`.kittify/glossaries/<scope>.yaml`) is updated to reflect the resolved clarification. This update does not wait for queue drain or SaaS acknowledgement. | Proposed |
| FR-022 | Glossary state reconstruction from seed file plus `GlossaryClarificationResolved` events produces the same state as reconstruction that previously included `GlossarySenseUpdated` events. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Zero PII fields appear in any git-committed event file after this change is deployed. | 0 occurrences of `machine_name`, `hostname`, `workspace_path`, `developer_name`, `developer_email`, or absolute session timestamps in `decisions.events.jsonl` or `status.events.jsonl`. | Proposed |
| NFR-002 | During an active WebSocket session, the SaaS build surface reflects a local commit within one second of that commit completing. An active session is defined as a WebSocket connection that is both established and authenticated. Measurement: wall-clock time from `safe_commit()` return to the SaaS receiving the `LocalCommit` frame. | ≤ 1 second end-to-end from commit to SaaS frame receipt under normal network conditions. | Proposed |
| NFR-003 | On-connect replay of unacknowledged `LocalCommit` frames does not perceptibly delay session start. | Replay of up to 50 pending frames adds ≤ 200 ms to session connect time. | Proposed |
| NFR-004 | Glossary queue write volume is substantially reduced after the `GlossarySenseUpdated` drop. | ≥ 90% reduction in glossary-related queue writes in a typical session that performs at least 10 extraction steps. | Proposed |
| NFR-005 | All new code paths have test coverage consistent with the project's 90% threshold. | ≥ 90% line coverage on new modules; all acceptance scenarios have at least one automated test. | Proposed |

---

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `decisions.events.jsonl` uses the identical JSONL format as `status.events.jsonl`: one JSON object per line, sorted keys, append-only, never rewritten or compacted. | Proposed |
| C-002 | The SQLite `OfflineQueue` drain, retry, and acknowledgement logic is not modified. Only which event types are enqueued changes. | Proposed |
| C-003 | The local `.kittify/events/glossary/<mission-id>.events.jsonl` file retains all event types including `GlossarySenseUpdated`. The change is scoped to the SaaS-destined queue only. | Proposed |
| C-004 | SaaS-side handling of the `LocalCommit` frame, the "local only → verified" upgrade on push, reading decision events from git on the SaaS side, and demoting the queue from semantic record on the SaaS side are all out of scope (covered in spec-kitty-saas #292, #293, #294, #295). | Proposed |
| C-005 | The `mypy --strict` type-checking requirement and the existing integration test suite must continue to pass after all changes. | Proposed |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| `decisions.events.jsonl` | New append-only, git-committed file per mission. Holds all `DecisionInputRequested` and `DecisionInputAnswered` events for that mission. Lives alongside `status.events.jsonl` in `kitty-specs/<mission>/`. |
| Event envelope | The wrapper structure applied to every domain event. Contains event-type-specific fields plus common metadata fields. The sanitizer operates on this envelope before any write. |
| `LocalCommit` frame | New outbound WebSocket message type. Emitted after every commit to `kitty-specs/`. Carries the commit SHA, `mission_id`, `build_id`, changed file list, and UTC timestamp. No PII fields. |
| `LocalCommitAck` frame | New inbound WebSocket message type. Sent by the SaaS to confirm it received and processed a `LocalCommit`. Carries the acknowledged commit hash. |
| `sync-state.json` | New file at `.kittify/sync-state.json`. Tracks `last_saas_confirmed_hash` (the most recent commit hash the SaaS has acknowledged) and the ordered list of pending unacknowledged `LocalCommit` frames. |
| Glossary seed file | `.kittify/glossaries/<scope>.yaml`. The authoritative current state of glossary terms for a given scope. Updated immediately on each `GlossaryClarificationResolved` event. |

---

## Success Criteria

1. A developer can reconstruct the complete decision history for any mission by reading `decisions.events.jsonl` from git alone, with no SaaS or queue access required.
2. A security audit of any git-committed event file finds zero instances of machine hostnames, filesystem paths, developer names, developer email addresses, or absolute session timestamps.
3. The SaaS build surface shows local commits as "local only" within one second during an active session, and replays any missed commits on reconnect with no manual intervention.
4. After any mission session, the SaaS queue contains zero `GlossarySenseUpdated` entries.
5. The glossary seed file reflects all resolved clarifications immediately after each resolution, without requiring a queue drain or SaaS response.

---

## Assumptions

1. The `safe_commit` function (or its equivalent call site) is the correct injection point for both the `decisions.events.jsonl` append and the `LocalCommit` WebSocket emit — both happen after a successful git commit.
2. The WebSocket connection's current state (connected/disconnected) is accessible from the code path that handles post-commit operations, so the emit-or-queue decision can be made without additional plumbing.
3. Glossary state reconstruction is valid using only the seed file plus `GlossaryClarificationResolved` events, without `GlossarySenseUpdated`. This is confirmed by the issue description.
4. Retrofitting PII sanitization to existing queue entries written before this change is not required — sanitization applies at write time from the deployment date forward.

---

## Out of Scope

- SaaS-side handling of `LocalCommit` frames and the "local only" build surface state (spec-kitty-saas #295)
- Upgrade from "local only" to "verified" when GitHub webhook confirms the push (spec-kitty-saas #292)
- Reading decision events from git on the SaaS side instead of the queue (spec-kitty-saas #293)
- Demoting the SaaS queue from semantic record to retry buffer (spec-kitty-saas #294)
- Retroactive PII removal from existing queue entries or git history
- Changes to the local `.kittify/events/glossary/` replay log

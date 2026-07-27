# WebSocket Frame Contracts: LocalCommit / LocalCommitAck

**Mission:** event-architecture-cli-git-truth-01KT119Y
**Date:** 2026-06-01
**Direction:** CLI ↔ SaaS (spec-kitty-saas counterpart: issues #292, #295)

> **Review required:** This contract must be shared with the spec-kitty-saas team and verified against issues [#292](https://github.com/Priivacy-ai/spec-kitty-saas/issues/292) and [#295](https://github.com/Priivacy-ai/spec-kitty-saas/issues/295) before WP06 merges. Any field-name or semantic mismatch between this document and the SaaS implementation must be resolved prior to merge.

---

## Outbound: `LocalCommit` (CLI → SaaS)

Emitted by the CLI after every successful `safe_commit()` call whose committed paths include at least one file under `kitty-specs/`.

### Frame shape

```json
{
  "type": "LocalCommit",
  "git_hash": "<full 40-char SHA>",
  "mission_id": "<ULID, 26 chars>",
  "build_id": "<ULID, 26 chars>",
  "changed_files": ["kitty-specs/<mission_slug>/decisions.events.jsonl"],
  "committed_at": "2026-06-01T07:30:00Z"
}
```

### Field definitions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"LocalCommit"` | ✓ | Discriminator. Must be exactly this string. |
| `git_hash` | string (40 hex chars) | ✓ | Full SHA of the new commit. Not abbreviated. |
| `mission_id` | string (ULID) | ✓ | Canonical mission identity. |
| `build_id` | string (ULID) | ✓ | Current session/build identifier. Used by SaaS to correlate with the session. |
| `changed_files` | array of strings | ✓ | Repo-relative paths of files touched by this commit that are under `kitty-specs/`. Minimum 1 entry. |
| `committed_at` | string (ISO8601 UTC) | ✓ | Timestamp of the commit. UTC, no local offset. |

### Constraints

- No PII fields anywhere in the frame.
- `changed_files` contains only paths under `kitty-specs/`; no other paths are included.
- Sent at most once per `safe_commit()` call. Multiple files committed together → one frame, all files listed.
- If the WebSocket is not connected at emit time, the frame is stored in `.kittify/sync-state.json` and replayed on reconnect.
- Amended commit: new frame with new `git_hash`, same `build_id`. Prior unacknowledged frame for the same `build_id` is replaced in the pending queue.

---

## Inbound: `LocalCommitAck` (SaaS → CLI)

Sent by the SaaS after it has received and processed a `LocalCommit` frame.

### Frame shape

```json
{
  "type": "LocalCommitAck",
  "git_hash": "<full 40-char SHA>"
}
```

### Field definitions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"LocalCommitAck"` | ✓ | Discriminator. |
| `git_hash` | string (40 hex chars) | ✓ | SHA of the commit being acknowledged. |

### CLI handling

On receiving `LocalCommitAck`:
1. Update `sync-state.json`: set `last_saas_confirmed_hash = git_hash`.
2. Remove all entries from `pending_local_commits` whose `git_hash` matches.
3. Write `sync-state.json` atomically.

---

## On-connect flush protocol

When the WebSocket connects:
1. Read `sync-state.json`.
2. Filter `pending_local_commits` to entries whose `git_hash` is not equal to `last_saas_confirmed_hash` (i.e., not yet acknowledged).
3. Send each pending `LocalCommit` frame in chronological order (`committed_at` ascending).
4. Do not wait for acks before completing the connect sequence; acks arrive asynchronously via `_listen()`.

---

## Ordering guarantee

The SaaS MUST process `LocalCommit` frames for a given `mission_id` in the order they are received. The CLI sends them in `committed_at` order. The SaaS implementation (spec-kitty-saas #295) is responsible for enforcing ordering.

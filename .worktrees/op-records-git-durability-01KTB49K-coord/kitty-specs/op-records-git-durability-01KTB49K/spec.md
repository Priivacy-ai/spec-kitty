# Op Record Git Durability

**Mission ID**: 01KTB49KJKRJ71YR8KERVDMHHA  
**Mission Slug**: op-records-git-durability-01KTB49K  
**Mission Type**: software-dev  
**Target Branch**: main  
**Source**: https://github.com/Priivacy-ai/spec-kitty/issues/1688 (Step 1 of 3)

---

## Overview

Op records produced by the `ask`, `advise`, and `do` commands are currently stored in a gitignored local directory, making them ephemeral — lost on `git clean` or re-clone. This feature moves Op storage to a git-tracked directory (`kitty-ops/`), auto-commits each completed record, and adds optional mission/work-package correlation fields to every Op record.

Step 2 (guaranteed SaaS delivery via OfflineQueue) and Step 3 (module rename `invocation` → `ops`) are explicitly out of scope for this mission.

---

## Actors

| Actor | Role |
|-------|------|
| **spec-kitty runtime** | Creates and closes Op records on behalf of each executing command |
| **operators / developers** | Query Op history via `git log`, detect orphans via `spec-kitty doctor ops`, and correlate Ops with mission timelines |

---

## User Scenarios & Testing

### Primary — Completed Op record survives git clean

After running `ask`, `advise`, or `do`, the resulting record is committed to git with a message matching `op(<profile-id>): <action> [<op-id-short>]`. An operator who subsequently runs `git clean -fdx kitty-ops/` can restore the record with `git checkout kitty-ops/`. The record appears in `git log` and in `git log --grep="^op("`.

### Mission-correlated Op

An agent command executed inside a running mission work package produces an Op record whose `mission_id` and `wp_id` fields are populated from the active execution context. A standalone invocation of `ask`, `advise`, or `do` produces a record with both fields set to null. A reader of the JSONL file can determine mission correlation without consulting any external index.

### Crashed session — orphan Op is not committed

A session terminates without closing an Op. The `started` event exists in `kitty-ops/<op_id>.jsonl` as an untracked working-tree file. The file does NOT appear in `git log kitty-ops/`. Running `spec-kitty doctor ops` reports the file as an orphan.

### `do` command produces a durable record (regression guard)

Before this change, `do` has no record persistence whatsoever. After this change, running `do` produces the same git-committed record as `ask` and `advise`. Verifiable by inspecting `git log kitty-ops/` immediately after a `do` invocation.

---

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | All Op records are written to `kitty-ops/` — a directory that is git-tracked by its absence from `.gitignore`, not by an explicit re-include | Proposed |
| FR-002 | Op completion triggers an auto-commit of the Op's JSONL file using direct git subprocess calls (not `safe_commit`, which requires `worktree_root` and refuses commits to protected branches such as `main`); the commit is best-effort — failure is logged at WARNING and does not block the Op response | Proposed |
| FR-003 | The auto-commit message follows the pattern `op(<profile-id>): <action> [<op-id-short>]`, where `op-id-short` is the first 8 characters of the Op's ULID | Proposed |
| FR-004 | Orphan Ops — those with a `started` event but no `completed` event — are never auto-committed; they exist only as untracked working-tree files | Proposed |
| FR-005 | `spec-kitty doctor ops` lists all orphan Op files present in `kitty-ops/` | Proposed |
| FR-006 | The Op record model gains two optional fields: `mission_id` (string or null) and `wp_id` (string or null) | Proposed |
| FR-007 | `mission_id` and `wp_id` are populated when the caller explicitly supplies them from the surrounding execution context; both fields are null (and excluded from serialisation) for standalone invocations where no context is provided | Proposed |
| FR-008 | The `do` command writes its Op record to `kitty-ops/` and commits it on completion, closing the existing zero-persistence gap | Proposed |
| FR-009 | A performance index is maintained at `kitty-ops/ops-index.jsonl` to support efficient reverse-scan operations | Proposed |
| FR-010 | The loop-lifecycle pairing log is stored at `kitty-ops/lifecycle.jsonl` | Proposed |

---

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Completed Op records committed to git must be fully restorable after `git clean -fdx kitty-ops/` followed by `git checkout kitty-ops/` | 100% of completed Op records restorable | Proposed |
| NFR-002 | The auto-commit mechanism must not require any changes to `.gitignore` | Zero `.gitignore` modifications | Proposed |
| NFR-003 | Op commits must be filterable from git history using a single grep pattern | All Op commits and only Op commits match `git log --grep="^op("` | Proposed |

---

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | No changes to `.gitignore` — `kitty-ops/` is tracked by its absence from ignore rules | Accepted |
| C-002 | Existing records in `.kittify/events/profile-invocations/` are abandoned with no migration; the changelog records this loss | Accepted |
| C-003 | `InvocationSaaSPropagator` and all OfflineQueue wiring remain unchanged (Step 2 scope boundary) | Accepted |
| C-004 | Module rename (`invocation` → `ops`, `InvocationRecord` → `OpRecord`, `invocation_id` → `op_id`) is not performed in this mission (Step 3 scope boundary) | Accepted |
| C-005 | The per-file JSONL event structure (append-only, `started` + `completed` events), ULID identity scheme, governance context hash mechanism, profile resolution, and GlossaryChokepoint integration are unchanged | Accepted |
| C-006 | Index writes to `ops-index.jsonl` may silently swallow errors — this behavior is intentional and documented | Accepted |

---

## Key Entities

| Entity | Description |
|--------|-------------|
| **Op** | A bounded, doctrine-governed agent action with a ULID identity and a permanent JSONL record in `kitty-ops/` |
| **kitty-ops/** | Git-tracked directory, peer of `kitty-specs/`; stores all Op JSONL files, the ops index, and the lifecycle log |
| **Op JSONL** | `kitty-ops/<op_id>.jsonl` — append-only file containing `started` and `completed` events for one Op |
| **Orphan Op** | An Op with a `started` event and no `completed` event; untracked, never committed |

---

## Success Criteria

- All completed Op records are committed to git within the repository where the Op ran
- An operator can restore any committed Op record after `git clean -fdx kitty-ops/` by running `git checkout kitty-ops/`
- `git log --grep="^op("` surfaces all Op commits and no non-Op commits
- Orphan Ops are surfaced by `spec-kitty doctor ops` without requiring any filesystem scan outside `kitty-ops/`
- The `do` command produces the same durable commit as `ask` and `advise`, observable by inspecting `git log kitty-ops/` after a `do` invocation

---

## Assumptions

- `safe_commit` is already available in the codebase and handles `git add --force` semantics; no changes to `safe_commit` itself are needed
- The `kitty-ops/` directory is created automatically the first time an Op record is written; no explicit initialization command is required
- Pre-existing records in `.kittify/events/profile-invocations/` are treated as abandoned; the CHANGELOG will note this as an accepted data loss

---

## Out of Scope

- OfflineQueue-based SaaS delivery (Step 2 — gated on issue #1693 and SaaS handler implementation for `OpStarted`/`OpCompleted`)
- Module rename (`invocation` → `ops`, `InvocationRecord` → `OpRecord`, `invocation_id` → `op_id`) — Step 3
- Any new `spec-kitty ops list` command surface
- Changes to SaaS-side event handler definitions

---
work_package_id: WP05
title: Server Sync How-To
lane: "done"
dependencies: [WP01]
base_branch: 030-2x-sync-auth-docs-WP01
base_commit: 514106af212e8706bdecdde924cd95167e73b67d
created_at: '2026-02-05T15:20:55.302176+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
phase: Phase 3 - How-To
assignee: ''
agent: ''
shell_pid: "17438"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-05T15:08:07Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP05 – Server Sync How-To

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `docs/how-to/sync-to-server.md` — task-oriented guide for syncing events with the server.
- **FR-003**: How-to for each new `sync` subcommand (`now`, `status`).
- **FR-011**: Clear distinction between local workspace sync and server sync.
- A developer can push queued events and check sync status after reading this page.

## Context & Constraints

- **Branch**: `docs/2x-sync-auth` off `2.x`
- **CRITICAL**: The existing `docs/how-to/sync-workspaces.md` documents LOCAL worktree rebasing (`sync workspace`). This new page documents SERVER sync (`sync now`, `sync status`). They must be clearly distinguished.
- **Source**: `git show 90dc9edd~1:src/specify_cli/cli/commands/sync.py` and `git show 90dc9edd~1:src/specify_cli/sync/batch.py`
- **Implementation command**: `spec-kitty implement WP05 --base WP01`

## Subtasks & Detailed Guidance

### Subtask T023 – Write introduction distinguishing server sync from local sync

- **Purpose**: Prevent confusion between `sync workspace` (local) and `sync now` / `sync status` (server).
- **Steps**:
  1. Create `docs/how-to/sync-to-server.md`
  2. Write H1: `# How to Sync with a Spec Kitty Server`
  3. Write intro paragraph explaining this page covers server synchronization
  4. Add a prominent callout box:

     > **Not what you're looking for?**
     >
     > - To sync your workspace with upstream worktree changes (local), see [Sync Workspaces](sync-workspaces.md).
     > - This page covers pushing/pulling events to/from a remote spec-kitty server.

  5. Write brief explanation: spec-kitty stores events locally and syncs them with the team server. This page covers how to trigger and monitor that sync.
  6. Prerequisites: authenticated session (`spec-kitty auth status` shows ✅), server URL configured
- **Files**: `docs/how-to/sync-to-server.md`

### Subtask T024 – Write batch sync procedure (`sync now`)

- **Purpose**: Document how to push queued events and pull updates.
- **Steps**:
  1. Add `## Push and Pull Events` section
  2. Document:
     ```bash
     spec-kitty sync now
     ```
  3. Explain what happens:
     - All locally queued events are sent to the server in batches
     - New events from the server are pulled down
     - The offline queue is drained
  4. Show expected output (representative):
     ```
     Syncing with https://your-server.example.com...
     ↑ Pushed 12 events (2 batches)
     ↓ Pulled 5 new events
     ✅ Sync complete
     ```
  5. Document `--verbose` for detailed per-event output
  6. Document `--dry-run` to preview without syncing
  7. Note: Events are sent in batches of up to 1000, gzip-compressed
- **Files**: `docs/how-to/sync-to-server.md`

### Subtask T025 – Write sync status procedure

- **Purpose**: Document how to check sync connection and queue status.
- **Steps**:
  1. Add `## Check Sync Status` section
  2. Document:
     ```bash
     spec-kitty sync status
     ```
     Output:
     ```
     Spec Kitty Sync Status

     Server URL   https://your-server.example.com
     Config File  /Users/you/.spec-kitty/config.toml
     Connection   Not checked (use --check to test)
     ```
  3. Document `--check` flag:
     ```bash
     spec-kitty sync status --check
     ```
     Output with `--check`:
     ```
     Connection   Reachable (auth required)
                  Server online (access forbidden)
     ```
  4. Explain connection states: Connected, Reachable, Unreachable, Error
- **Files**: `docs/how-to/sync-to-server.md`

### Subtask T026 – Write offline workflow section

- **Purpose**: Explain how spec-kitty works when offline.
- **Steps**:
  1. Add `## Working Offline` section
  2. Explain the offline workflow:
     - When you work without a server connection, events are queued locally in SQLite
     - Your work is never lost — events accumulate in the offline queue
     - When you're back online, run `sync now` to push everything
     - The Lamport clock ordering ensures events merge correctly even after a long offline period
  3. Explain: the WebSocket connection (if configured) will also drain the queue automatically when it reconnects
  4. Add a note: "You can check how many events are queued with `sync status`"
- **Files**: `docs/how-to/sync-to-server.md`

### Subtask T027 – Write troubleshooting section

- **Purpose**: Address common sync problems.
- **Steps**:
  1. Add `## Troubleshooting` section
  2. Document these scenarios:
     - **"Cannot reach server"**: Check network, verify URL, try `sync status --check`
     - **"Authentication expired"**: Run `spec-kitty auth login` to re-authenticate
     - **"Partial sync"**: Some events may fail — the server returns per-event status. Failed events remain in queue.
     - **"Queue not draining"**: Check that auth is valid, server is reachable, and no event format errors
  3. Add note: `sync now` is idempotent — safe to run multiple times
- **Files**: `docs/how-to/sync-to-server.md`

### Subtask T028 – Write See Also links

- **Purpose**: Cross-reference related pages.
- **Steps**:
  1. Add `## See Also` section
  2. Links:
     - [Sync Workspaces](sync-workspaces.md) — Local worktree sync (different from server sync)
     - [CLI Commands: `spec-kitty sync`](../reference/cli-commands.md#spec-kitty-sync) — Detailed command reference
     - [Authentication How-To](authenticate.md) — Setting up credentials
     - [Sync Architecture](../explanations/sync-architecture.md) — How the sync system works
- **Files**: `docs/how-to/sync-to-server.md`

## Risks & Mitigations

- **Risk**: `sync now` output is speculative → Mark as representative, not exact
- **Risk**: Confusion with existing `sync-workspaces.md` → Prominent callout box in intro (T023)

## Review Guidance

- **MOST IMPORTANT**: Verify the callout distinguishing server sync from local workspace sync is prominent
- Check that the page doesn't overlap with `sync-workspaces.md` content
- Verify `sync now` examples are clearly marked as provisional
- Confirm troubleshooting covers the most common failure modes

## Activity Log

- 2026-02-05T15:08:07Z – system – lane=planned – Prompt created.
- 2026-02-05T15:23:14Z – unknown – shell_pid=17438 – lane=for_review – Created how-to/sync-to-server.md covering sync now, sync status, offline workflow, troubleshooting, and see-also links. Added entry to toc.yml.

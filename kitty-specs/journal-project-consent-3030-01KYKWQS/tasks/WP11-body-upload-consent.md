---
work_package_id: WP11
title: Body-upload consent (uncovered egress path)
dependencies:
- WP05
requirement_refs:
- FR-002
- FR-016
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
base_commit: 988b42b8330d2fc51e3b4b7c34b07d88c717698d
created_at: '2026-07-28T14:17:00.517494+00:00'
subtasks:
- T025
- T026
history: []
authoritative_surface: src/specify_cli/sync/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/sync/body_upload.py
tags: []
tracker_refs: []
---

# WP11 — Body-upload consent

**Found by the post-tasks squad. No spec, plan or task artefact before it mentioned body uploads** —
this is the same breach class as the P0, on a live path, on the same command the operator ran, and it
was owned by nobody.

## The gap

`sync now` calls `service.drain_body_uploads_only()` (`cli/commands/sync.py:2368`) — invoked twice
during the incident. That path is gated **once, at enqueue**, on
`is_sync_enabled_for_checkout(repo_root)` (`sync/body_upload.py:150`), which falls through to
`effective_sync_enabled = True` at `sync/routing.py:87` when neither a checkout override nor a repo
default exists — exactly the state of the five leaked projects. After enqueue, `_drain_body_queue`
POSTs every task with the machine-global `is_saas_sync_enabled()` as the only gate.

What ships is not metadata. `_TOP_LEVEL_ARTIFACTS` (`body_upload.py:33-52`) is
`spec.md, plan.md, tasks.md, analysis-report.md, research.md, quickstart.md, data-model.md` plus
`research/`, `contracts/`, `checklists/` and `tasks/WP*.md` — verbatim prose, the most confidential
text on the machine.

## Why the event-side fix does not cover it

WP06 makes the stored `project_uuid` column the sole authority for **event** selection. The body queue
is a different store with a different drain, and its consent decision is resolved from
`Path.cwd()` rather than from the task's project (`emitter.py:1891,1920` call
`is_sync_enabled_for_checkout()` with no argument). In a daemon, a monorepo of worktrees, or any agent
session that `cd`s between checkouts, one project's consent is applied to another project's upload.

## Definition of done

- Consent resolved **per task at drain time**, keyed on the task's namespace project identity, never on
  cwd. A test with two checkouts and a mismatched cwd proves it.
- A body-upload task for a project with **no consent record** is not POSTed (deny on absence, matching
  WP05's FR-002 inversion).
- T026: the body-upload queue is included in WP08's purge differential. It shares the offline-queue DB
  file (`OfflineBodyUploadQueue(db_path=OfflineQueue().db_path)`), so a purge that reports 100% today
  leaves queued bodies behind — a false remediation attestation.
- `sync/routing.py`'s call sites are passed an explicit repo root rather than defaulting to cwd.

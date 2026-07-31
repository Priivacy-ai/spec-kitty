---
work_package_id: WP12
title: 'Local-commit frames: the third uncovered egress path'
dependencies:
- WP05
requirement_refs:
- FR-002
- NFR-001
planning_base_branch: feat/journal-project-consent-3030
merge_target_branch: feat/journal-project-consent-3030
branch_strategy: Planning artifacts for this mission were generated on feat/journal-project-consent-3030. Completed changes must merge back into feat/journal-project-consent-3030 unless the human explicitly redirects the landing branch.
created_at: '2026-07-30T00:00:00+00:00'
subtasks:
- T027
- T028
history: []
execution_mode: code_change
tags: []
tracker_refs: []
authoritative_surface: src/specify_cli/sync/
owned_files:
- src/specify_cli/sync/local_commit.py
- src/specify_cli/git/commit_helpers.py
---

# WP12 — Local-commit frames ship project identity with no consent check

**Found by the post-WP06 adversarial review (2026-07-30), not by any earlier artefact.**
Same breach class as WP11, on a live path, previously unowned. Folded into this mission by
operator decision rather than deferred — shipping a P0 that claims "the leak is closed" while a
known ungated egress path remains would repeat the mistake the mission exists to fix.

## The path

`grep -c "is_saas_sync_enabled\|is_sync_enabled_for_checkout\|consent" src/specify_cli/sync/local_commit.py` → **0**.

1. `git/commit_helpers.py:1141-1157` — after **every** `safe_commit` touching `kitty-specs/`, calls
   `emit_local_commit(...)` with `changed_files=mission_specs_files`. No gate of any kind.
2. `sync/local_commit.py:143-169` — persists the frame to `.kittify/sync-state.json` and attempts an
   immediate WebSocket send.
3. `sync/client.py:181-189` — on **every** WebSocket connect: `flush_pending_local_commits(self._repo_root, self)`,
   where `_repo_root` defaults to `Path.cwd()` (`client.py:104`) because `runtime.py:194` constructs
   `WebSocketClient` without it.

Payload: `git_hash`, `mission_id`, `build_id`, `committed_at`, and `changed_files` — relative paths under
`kitty-specs/`, i.e. **mission slugs**. For the incident's population those slugs are client engagement
names. Metadata, not payloads — but the confidentiality claim is about *which clients exist*, and this
leaks exactly that.

## Why it is live, not theoretical

`_auto_start_enabled()` (`sync/runtime.py:62-80`) **fails open twice**: `return True` when
`locate_project_root` yields `None` (line 70), and `return True` on any exception resolving routing
(line 80). A project-local `sync.auto_start: true` (line 72-74) outranks the consent-derived gate
entirely.

Reproduction shape: cwd is a never-opted-in checkout, operator authenticated,
`SPEC_KITTY_ENABLE_SAAS_SYNC=1` — the incident's exact machine state. Any spec-kitty command that
commits a dossier file writes a frame; the next WS connect from that cwd POSTs it.

The reviewer assessed the *immediate* send at `local_commit.py:220-243` as probably dead (it reads
`token_manager._ws_client`, for which no production writer was found) but the **connect-time flush is
live**. Confirm both before deciding scope.

## Subtasks

- **T027** — Gate frame emission and flush on per-project consent via `sync/consent.py`'s single
  resolver. Resolve consent from the **frame's own** `mission_id`/`build_id` identity, never from cwd —
  `flush_pending_local_commits` runs against `Path.cwd()`, so a cwd-derived check has the same defect
  T025 names for body uploads and M1 names for capture.
- **T028** — Close `_auto_start_enabled`'s two fail-open returns (`runtime.py:70,80`). Inability to
  determine consent is not consent (FR-003's rule, applied to this gate).

## Definition of done

- A never-opted-in checkout produces **no** local-commit frame, and any frame already on disk for a
  non-consenting project is **not** flushed. Assert no network request was made, not merely that a
  boolean flipped.
- Frames already persisted in `.kittify/sync-state.json` for non-consenting projects are covered — this
  is residual state, exactly like WP11's pre-flip body queue and WP04's pre-T006 journal rows. Decide
  and record whether they are dropped, retained-and-ignored, or purged; do not leave it implicit.
- The consent decision is made from frame identity, with a test that fails if it is taken from cwd
  (spawn the check from a different working directory than the frame's project).
- `_auto_start_enabled`'s fail-open paths have a test each.

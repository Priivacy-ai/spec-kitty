---
work_package_id: WP11
title: Dashboard read-only status (no tracked write on read)
dependencies:
- WP07
requirement_refs:
- FR-014
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
phase: Phase 3 - Runtime
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4055573"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Re-scoped to dashboard-only after squad validation; daemon singleton/reaper split to WP12
agent_profile: ''
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/dashboard/handlers/features.py
- src/specify_cli/dashboard/scanner.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP11 – Dashboard read-only status

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/dashboard/`.

---

## ⚠️ Read the validation first
Read `research/wp11-daemon-validation.md`. **The sync daemon writes NO tracked status** — that is WP12's
surface. This WP fixes the **dashboard**, which is the *actual* background writer of tracked `status.json`.

## Objectives & Success Criteria
- The dashboard handlers call the **writing** `materialize()` (`status/reducer.py:318`, unguarded atomic write)
  on every kanban request — this is the #1789 git-op clobber (a long rebase races these writes and aborts).
- Switch the dashboard read paths to the **read-only** `materialize_snapshot` (`reducer.py:289`) so serving a
  read never writes tracked status; share WP07's in-progress-git-op detection (do not duplicate it → C-005).
- **Done when (SC-6a):** a long `git rebase` with the dashboard live serves kanban with **no `status.json`
  write / no clobber**; kanban payload unchanged.

## Context & Constraints
- Design: `spec.md` FR-014(a) + SC-6a; `plan.md` IC-12; `research/wp11-daemon-validation.md` (binding).
- `MissionStatus` is a **transition** API, not a refresh API — the dashboard only reads, so do NOT route it
  through `MissionStatus.transition`; use the read-only snapshot.
- Depends on **WP07** (git-op guard / shared detection).

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T035 — Dashboard read-only snapshot
- In `dashboard/handlers/features.py:169` and `dashboard/scanner.py:557`, replace the writing `materialize()`
  with the read-only `materialize_snapshot` (`reducer.py:289`). Verify the kanban payload is unchanged.
  Grep-confirm no writing `materialize(` call remains on a dashboard request path.
### T036 — Share WP07 git-op detection
- Ensure no dashboard path re-materializes tracked status during a git op, consuming WP07's detection
  (`.git/rebase-merge/`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, `index.lock`). Do not duplicate the detection.
### T037 — SC-6a test
- Dashboard-serves-kanban-during-rebase → assert no `status.json` write / no clobber. Do not leak
  `test-feature-*` artifacts.

## Test Strategy
- SC-6a test; `ruff`+`mypy` zero issues; grep-confirm no writing `materialize()` on dashboard read paths.

## Risks & Mitigations
- *Snapshot drift* → confirm `materialize_snapshot` returns the same shape the dashboard renders.

## Review Guidance
- Recommended: **reviewer-renata**. Confirm the dashboard no longer writes tracked status on read; no duplicate git-op detection (C-005).

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T17:17:15Z – system – Re-scoped to dashboard-only; daemon work split to WP12.
- 2026-06-10T05:19:47Z – claude:opus:python-pedro:implementer – shell_pid=4043492 – Assigned agent via action command
- 2026-06-10T05:27:48Z – claude:opus:python-pedro:implementer – shell_pid=4043492 – Dashboard read paths switched to read-only materialize_snapshot (features.py + scanner.py); no tracked status.json write on kanban read. SC-6a proven: no clobber during real git rebase. Shares WP07 git_operation_in_progress (no duplicate detection, C-005). Payload unchanged (C-004).
- 2026-06-10T05:28:17Z – claude:opus:reviewer-renata:reviewer – shell_pid=4055573 – Started review via action command
- 2026-06-10T05:30:47Z – user – shell_pid=4055573 – Review passed: both clobber sites (features.py:169, scanner.py:557) now route through read-only materialize_snapshot via shared read_only_weighted_percentage helper — grep confirms no live writing materialize() remains in dashboard/ (only docstring refs). WP07 git_operation_in_progress reused (C-005, no duplicate marker probing). Parity test proves payload unchanged vs writing materialize() (C-004). SC-6a re-run green: real conflicted git rebase, git_operation_in_progress True mid-rebase, kanban read serves no status.json clobber. Gates: 245 passed/1 xfailed, ruff clean. 1 pre-existing mypy error at features.py:97 (DashboardHandler->Any class decl, verbatim on base, untouched by diff). Scope: 2 dashboard files + test edits only.

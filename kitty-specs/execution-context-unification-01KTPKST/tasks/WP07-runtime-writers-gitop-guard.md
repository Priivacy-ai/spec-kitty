---
work_package_id: WP07
title: Runtime writers git-op guard (Cluster E)
dependencies:
- WP02
- WP03
requirement_refs:
- FR-005
- FR-012
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
phase: Phase 3 - Runtime
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3961559"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/status/views.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/status/views.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Runtime writers git-op guard

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/status/views.py`.

---

## Objectives & Success Criteria
- `materialize_if_stale` must **never re-materialize tracked status during a git op** (rebase/reset) — #1789/#1062.
- Its staleness key must be **context-aware** so it does not false-positive across CWDs (FR-012).
- **Done when (SC-5):** a long `git rebase` on a mission branch completes with no daemon/dashboard status-file clobber; WP01 runtime-write parity flips green.

## Context & Constraints
- Design: `spec.md` FR-005/FR-012; `plan.md` IC-06; `contracts/...` C-RT-1; `quickstart.md` SC-5.
- **Highest blast radius** (daemons/dashboard write here) — runs after WP02 (facade) + WP03 (context). Strangle carefully.
- Writes go through the WP02 facade; keep reducer/store semantics intact.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T023 — git-op guard
- Detect an in-progress git op (rebase/reset in progress, e.g. `.git/rebase-*`/`MERGE_HEAD`) and skip re-materializing tracked status; defer until the op completes.
### T024 — Context-aware stale-key
- Compute the staleness key from the resolved context (not a CWD-relative heuristic) so the same mission is not falsely stale from a different CWD.
### T025 — SC-5 scenario + parity
- Add the long-rebase no-clobber scenario (quickstart SC-5); flip WP01 runtime-write parity.

## Test Strategy
- SC-5 scenario test; WP01 runtime parity green; `ruff`+`mypy` zero issues.

## Risks & Mitigations
- *Daemon races* → guard must be conservative (skip-when-unsure); never write during an active git op.

## Review Guidance
- Recommended: **reviewer-renata** + **architect-alphonso** (highest-risk surface). Confirm SC-5 is a real rebase, not mocked.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-10T03:48:53Z – claude:opus:python-pedro:implementer – shell_pid=3949398 – Assigned agent via action command
- 2026-06-10T03:57:08Z – claude:opus:python-pedro:implementer – shell_pid=3949398 – git-op guard skips materialize_if_stale during rebase/merge/cherry-pick/revert/index.lock (FR-005/C-RT-1, #1789/#1062); reusable public git_operation_in_progress() for WP11; context-aware stale-key via canonical mission_slug (FR-012); SC-5 real-rebase no-clobber test green
- 2026-06-10T03:58:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=3961559 – Started review via action command
- 2026-06-10T04:02:08Z – user – shell_pid=3961559 – Review passed: git-op guard correct (filesystem-only, both per-worktree + common gitdirs scanned, all 6 markers, conservative skip-when-unsure, never blocks when no op active); SC-5 re-run as REAL git rebase (conflict pause, guard asserted active mid-rebase, no status-file clobber, content intact after --continue) — 15/15 pass; context-aware stale-key resolves canonical mission_slug from meta.json with legacy dir-name fallback; git_operation_in_progress exported as single reusable source for WP11; parity+status gates 2386 passed/2 xfailed; ruff clean; sole mypy no-any-return is PRE-EXISTING in untouched generate_status_view (WP07 actually fixed a 2nd base error in _is_stale). Lifecycle xfail correctly left strict-xfail (needs ACTION_NAMES in mission_runtime/resolution.py — resolver work outside views.py); flag to orchestrator for ownership. Scope = views.py + export + tests only.

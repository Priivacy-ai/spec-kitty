---
work_package_id: WP12
title: Sync-daemon singleton + reaper consolidation
dependencies: []
requirement_refs:
- FR-014
- FR-015
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
phase: Phase 3 - Runtime
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3787375"
history:
- at: '2026-06-09T17:17:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks (reaper-collapse WP added per operator)
agent_profile: ''
authoritative_surface: src/specify_cli/sync/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/owner.py
- src/specify_cli/sync/orphan_sweep.py
- src/specify_cli/sync/daemon.py
- src/specify_cli/dashboard/lifecycle.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP12 – Sync-daemon singleton + reaper consolidation

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load`; if none set, pick an implementer profile for `code_change` on `src/specify_cli/sync/`.

---

## ⚠️ Read the validation first
Read `research/wp11-daemon-validation.md`. **The sync daemon writes NO tracked status** — do not hunt `sync/`
for a `status.json` write (the dashboard write is WP11). This WP is the **daemon lifecycle**: collapse the
duplicate reapers and re-fix the singleton.

## Objectives & Success Criteria
- **Collapse (FR-015):** there are **three** duplicate sync orphan-reapers today —
  `owner.is_orphan`/`list_orphan_records`, `orphan_sweep.sweep_orphans`/`enumerate_orphans`,
  `daemon.scan_sync_daemons`/`cleanup_orphan_sync_daemons`/`_iter_sync_daemon_processes` (~390 LOC) — plus a
  duplicated `_is_process_alive` + health-probe shared with `dashboard/lifecycle.py`. Collapse to **one**
  canonical reaper keyed on `DaemonOwnerRecord`; one `_is_process_alive`/health-probe.
- **Singleton (FR-014b, #1071):** enforce **one daemon per host/auth-scope** (operator decision — NOT
  per-checkout) and wire the ONE collapsed reaper into the `ensure_sync_daemon_running` spawn path, scoped by
  executable/auth-identity.
- **Done when (SC-6b + SC-7):** across multiple interpreters on one host exactly one `run_sync_daemon` runs
  per host/auth-scope, stale orphans reaped at spawn; `rg` finds exactly one reaper + one liveness probe.

## Context & Constraints
- Design: `spec.md` FR-014(b)/FR-015 + SC-6b/SC-7; `plan.md` IC-13; `research/wp11-daemon-validation.md` (binding).
- **Operator decision:** singleton scope = **one-per-host/auth-scope** (matches existing machine-global design).
- **No per-action context** — the detached daemon (`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`) has no
  `MissionExecutionContext`; key on `DaemonOwnerRecord` identity (auth-scope/queue), not a path/worktree.
- C-005/NFR-005: this is a **net-subtraction** WP — collapse, do not add a fourth reaper. Report delete-vs-add LOC.
- **Characterize before deleting** (C-004 burn-down): the three reapers differ (record-based / port-scan /
  cmdline-scan). Capture each real behavior in the one canonical reaper before removing the others.

## Branch Strategy
- **Planning base / merge target**: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance
### T038 — Collapse 3 reapers → ONE
- Define one canonical reaper (in `sync/owner.py` or a single `sync/` home) keyed on `DaemonOwnerRecord`,
  subsuming port-scan + cmdline-scan + record-based detection; delete the other two (strangler-ordered).
### T039 — Dedup liveness/health-probe
- One `_is_process_alive` + one daemon-health-probe shared by `sync/` and `dashboard/lifecycle.py`
  (today duplicated). Pick the canonical home; re-point the dashboard.
### T040 — Singleton one-per-host/auth-scope + wire reaper into spawn
- `ensure_sync_daemon_running` reaps stale `run_sync_daemon` orphans (via the ONE reaper) before/at spawn,
  scoped by executable/auth-identity; enforce single owner per host/auth-scope.
### T041 — SC-6b / SC-7 tests
- Multi-interpreter spawn → one daemon per host/auth-scope + stale reaping; assert exactly one reaper +
  one liveness probe remain (`rg`). Reap every spawned daemon in teardown (no test-induced leak).

## Test Strategy
- SC-6b + SC-7 tests; `ruff`+`mypy` zero issues; report net LOC removed (NFR-005).

## Risks & Mitigations
- *Reaper over-kill* → scope by executable/auth-identity; never reap legitimately-separate `$HOME`/container daemons.
- *Behavior loss on collapse* → characterize all three reapers' real behaviors first (C-004); cover with tests before deleting.

## Review Guidance
- Recommended: **reviewer-renata** + **architect-alphonso** (process-lifecycle blast radius + C-005 consolidation).
  Confirm exactly one reaper + one liveness probe remain; singleton is host/auth-scoped; reaper scoped safely; net LOC down.

## Activity Log
- 2026-06-09T17:17:15Z – system – Prompt created.
- 2026-06-09T20:26:06Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Assigned agent via action command
- 2026-06-09T20:44:21Z – claude:opus:python-pedro:implementer – shell_pid=3730248 – Reapers 3->1: canonical reap_orphan_daemons (owner.py) keyed on DaemonOwnerRecord subsumes record/port-scan/cmdline-scan discovery + single _sweep_daemon_process kill; orphan_sweep+daemon sweeps delegate. Dedup _is_process_alive + localhost health-probe -> daemon.py (dashboard+orphan_sweep delegate). Singleton=one-per-host/auth-scope, executable-identity-scoped reaper wired into ensure_sync_daemon_running spawn path (reaper-over-kill guarded). Code-only net subtraction in orphan_sweep(-14)/daemon(+13)/lifecycle(-8); owner.py grows by the single canonical reaper. SC-6b/SC-7 tests green (8). ruff+mypy clean on changed code (pre-existing daemon.py Popen + 2 dashboard-cli + 1 token-manager failures unrelated).
- 2026-06-09T20:46:04Z – claude:opus:reviewer-renata:reviewer – shell_pid=3763005 – Started review via action command
- 2026-06-09T20:53:43Z – user – shell_pid=3763005 – Moved to planned
- 2026-06-09T20:55:56Z – claude:opus:python-pedro:implementer – shell_pid=3784646 – Started implementation via action command
- 2026-06-09T20:57:18Z – claude:opus:python-pedro:implementer – shell_pid=3784646 – Cycle-2: fixed no-any-return (dict|None narrow); mypy+ruff clean, 8 SC tests green
- 2026-06-09T20:57:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=3787375 – Started review via action command
- 2026-06-09T20:59:41Z – user – shell_pid=3787375 – Cycle-2 review passed: no-any-return fixed via dict|None narrow, behavior unchanged, gates clean

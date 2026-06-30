---
work_package_id: WP03
title: Tracker binding_ref report-only on read paths
dependencies: []
requirement_refs:
- FR-001
- FR-004
tracker_refs: []
planning_base_branch: fix/sync-worktree-clean-invariant
merge_target_branch: fix/sync-worktree-clean-invariant
branch_strategy: Planning artifacts for this mission were generated on fix/sync-worktree-clean-invariant. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-worktree-clean-invariant unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 2 - Tracker reads
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "16702"
history:
- at: '2026-06-30T13:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/
create_intent:
- tests/specify_cli/tracker/test_binding_report_only.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/tracker/saas_service.py
- src/specify_cli/tracker/config.py
- tests/specify_cli/tracker/test_binding_report_only.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Tracker binding_ref report-only

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/tracker/`.

---

## Objective

Stop read-like tracker operations from persisting `binding_ref` to
`.kittify/config.yaml`. Today `_maybe_upgrade_binding_ref` calls
`save_tracker_config` (which writes `config.yaml`) opportunistically from
`status`/`sync_pull`/`sync_push`/`sync_run`/`map_list`. Make those reads
**report** an available upgrade (`pending_binding_upgrade`) instead of writing;
persist only on an explicit `tracker bind`/apply.

## Context & Constraints

- File: `src/specify_cli/tracker/saas_service.py`.
  - `_maybe_upgrade_binding_ref` (≈:141) calls `save_tracker_config(...)` (≈:174); it early-returns when the response has no `binding_ref` or it already matches.
  - Callers: `status` (≈:475), `sync_pull` (≈:484), `sync_push` (≈:498), `sync_run` (≈:507), `map_list` (≈:518).
- File: `src/specify_cli/tracker/config.py` — `save_tracker_config` (≈:155) writes **`.kittify/config.yaml`** ("Persist tracker config into .kittify/config.yaml, preserving other sections").
- **LEAVE these — write-authorized `bind`/rebind boundaries that MUST keep persisting** (do NOT make them report-only): `saas_service.py:224` (`bind`), `saas_service.py:272` (rebind/connect), `tracker/local_service.py:63` (local `bind`). The **only** read-path writer to convert is `_maybe_upgrade_binding_ref` (`:174`). `local_service.py` is intentionally not in this WP's `owned_files` because it has no read-path writer.
- **Constraints**: FR-004; C-003 (config.yaml stays canonical store — we only move *when* it's written); do not break an intentional `tracker bind`; no lint/type suppressions.
- Contract reference: `contracts/tracker-binding-report.md` (C-TB-1..3).
- **Do not touch** identity call sites (WP02) — `tracker/origin.py` and `cli/commands/tracker.py` belong to WP02.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `fix/sync-worktree-clean-invariant`
- **Merge target branch**: `fix/sync-worktree-clean-invariant`

> No dependencies — parallelizable with WP01/WP02. Owns `tracker/saas_service.py`
> and `tracker/config.py` exclusively.

## Subtasks & Detailed Guidance

### T011 — Make `_maybe_upgrade_binding_ref` report-only

**Steps**:
1. Change `_maybe_upgrade_binding_ref` so on a read path it **does not** call `save_tracker_config`. Instead, return the pending ref (e.g. return the changed `binding_ref` or `None`).
2. Preserve the existing early-return (no `binding_ref` / unchanged) → returns `None` (nothing pending).
3. Keep the method's signature stable for callers, or introduce a small return type carrying `pending_binding_upgrade`.

**Validation**: the function performs no file I/O on read paths.

### T012 — Surface `pending_binding_upgrade` on read results

**Steps**:
1. In `status`/`sync_pull`/`sync_push`/`sync_run`/`map_list`, capture the pending ref from T011 and attach it to the returned result object/dict as `pending_binding_upgrade=<ref>` (None when nothing pending).
2. Optionally emit a single non-fatal notice ("A tracker binding upgrade is available; run `tracker bind` to apply") — the notice MUST NOT write any tracked file.
3. Do not change the success/exit semantics of these read commands.

**Validation**: a read op with a changed server `binding_ref` returns `pending_binding_upgrade` set and writes nothing.

### T013 — Keep explicit bind/apply persisting

**Steps**:
1. Identify the explicit, user-initiated bind/apply path (e.g. a `tracker bind` command or an apply method). If one exists, confirm it calls `save_tracker_config` to persist `binding_ref` (write-authorized).
2. If no explicit apply path exists yet, add a minimal one (method/flag) that persists the `pending_binding_upgrade` — this is the *only* sanctioned write of `binding_ref`.
3. Document the write boundary in a comment.

**Validation**: an explicit bind persists `binding_ref` to `config.yaml`.

### T014 — Tests

**File**: `tests/specify_cli/tracker/test_binding_report_only.py`.

**Cases** (stub the server response to return a changed `binding_ref`):
- `status`/`sync_pull`/`map_list` with a changed server `binding_ref`: `config.yaml` unchanged; result carries `pending_binding_upgrade` (FR-004, AS-3).
- unchanged/absent `binding_ref`: no pending, no write (no-op).
- explicit bind/apply: `config.yaml` updated with the new `binding_ref`.

**Validation**: ≥90% coverage on changed lines; deterministic.

## Test Strategy

```bash
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/tracker/test_binding_report_only.py -q
.venv/bin/mypy --strict src/specify_cli/tracker/saas_service.py src/specify_cli/tracker/config.py
.venv/bin/ruff check src/specify_cli/tracker/
```

## Risks & Mitigations

- **Risk**: breaking an intentional binding upgrade (a real feature). **Mitigation**: T013 preserves an explicit persist path; only the *opportunistic read-time* write is removed.
- **Risk**: callers rely on side-effect persistence. **Mitigation**: grep callers of the read methods; ensure none depend on `binding_ref` being written as a side effect.
- **Risk**: return-type change ripples. **Mitigation**: prefer attaching `pending_binding_upgrade` to existing result dicts over changing positional returns.

## Review Guidance

- No `save_tracker_config` call remains on any read path.
- `pending_binding_upgrade` is surfaced and tested.
- An explicit bind still persists.
- `config.yaml` writes only happen at the explicit boundary.

## Activity Log

- 2026-06-30 — Prompt generated via /spec-kitty.tasks.
- 2026-06-30T14:44:32Z – claude:opus:python-pedro:implementer – shell_pid=75172 – Assigned agent via action command
- 2026-06-30T14:55:33Z – claude:opus:python-pedro:implementer – shell_pid=75172 – binding_ref report-only on reads; binds still persist; tests+mypy+ruff green
- 2026-06-30T14:56:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=2639 – Started review via action command
- 2026-06-30T15:04:15Z – user – shell_pid=2639 – Moved to planned
- 2026-06-30T15:06:55Z – claude:opus:python-pedro:implementer – shell_pid=10020 – Started implementation via action command
- 2026-06-30T15:12:13Z – claude:opus:python-pedro:implementer – shell_pid=10020 – Cycle 1 fix: retargeted test_scenario_6 to report-only contract; pytest -k tracker now 0 failed
- 2026-06-30T15:13:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=16702 – Started review via action command
- 2026-06-30T15:18:25Z – user – shell_pid=16702 – Cycle-1 fix verified: coupled discovery test retargeted to report-only (not weakened); pytest -k tracker 0 failed; mypy --strict + ruff clean; scope = one test file

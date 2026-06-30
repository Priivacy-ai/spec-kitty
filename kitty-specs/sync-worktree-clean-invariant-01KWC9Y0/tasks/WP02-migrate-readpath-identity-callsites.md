---
work_package_id: WP02
title: Migrate read-path identity call sites to resolve_identity
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-008
tracker_refs: []
planning_base_branch: fix/sync-worktree-clean-invariant
merge_target_branch: fix/sync-worktree-clean-invariant
branch_strategy: Planning artifacts for this mission were generated on fix/sync-worktree-clean-invariant. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-worktree-clean-invariant unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Call-site migration
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "30010"
history:
- at: '2026-06-30T13:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/specify_cli/sync/test_emit_readonly_identity.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/routing.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/__init__.py
- src/specify_cli/sync/dossier_pipeline.py
- src/specify_cli/tracker/origin.py
- src/specify_cli/cli/commands/tracker.py
- tests/specify_cli/sync/test_emit_readonly_identity.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Migrate read-path identity call sites

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: src/specify_cli/sync/`.

---

## Objective

Route every **read / emit / background** `ensure_identity(...)` call site to the
side-effect-free `resolve_identity(...)`, so those paths stop writing
`.kittify/config.yaml`. Keep `ensure_identity` **only** at write-authorized
boundaries (`init`). Depends on WP01 — without the deterministic `build_id`, these
swaps would introduce identity drift.

## Context & Constraints

- `resolve_identity` lives at `src/specify_cli/identity/project.py:336` (read-only twin; do not modify it here — WP01 owns that file).
- Call-site inventory (from `grep -rn "ensure_identity(" src/specify_cli/`):
  - **MIGRATE (read context, owned by this WP)**:
    - `sync/emitter.py:100` (`_get_project_identity`), `sync/emitter.py:115` (`_create_git_resolver`)
    - `sync/routing.py:47`
    - `sync/events.py:180`
    - `sync/__init__.py:253`
    - `sync/dossier_pipeline.py:233`
    - `tracker/origin.py:452`
    - `cli/commands/tracker.py:680`
  - **KEEP (write-authorized, do NOT change)**: `cli/commands/init.py:99`, `cli/commands/init.py:863`.
- **Tracker `saas_service.py` / `config.py` are NOT in this WP** (WP03 owns the binding-ref change).
- **Constraints**: FR-003 (persistence only at write boundary), C-005 (complete identities unchanged), no lint/type suppressions.
- Line numbers may have shifted — locate by symbol, confirm each site is genuinely read-context before swapping.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `fix/sync-worktree-clean-invariant`
- **Merge target branch**: `fix/sync-worktree-clean-invariant`

> Depends on WP01. `lanes.json` (finalize-tasks) governs the lane. This WP owns the
> listed `sync/*`, `tracker/origin.py`, and `cli/commands/tracker.py` files exclusively.

## Subtasks & Detailed Guidance

### T006 — Swap emitter call sites

**Steps**:
1. In `sync/emitter.py`, change `_get_project_identity` (≈:100) and `_create_git_resolver` (≈:115) from `ensure_identity(repo_root)` to `resolve_identity(repo_root)`; update the import.
2. Confirm neither is a write boundary (they exist to *read* identity for emission). The emit path must not persist.
3. Verify the emitted event still carries a complete identity (WP01 guarantees stability).

**Validation**: emitting a status event on an incomplete-identity checkout writes nothing to `config.yaml`.

### T007 — Swap remaining sync read paths

**Steps**:
1. `sync/routing.py:47`, `sync/events.py:180`, `sync/__init__.py:253`, `sync/dossier_pipeline.py:233`: swap `ensure_identity` → `resolve_identity`.
2. For each, read the enclosing function and confirm it is read/emit/background context (not an explicit user-initiated persist). If any site turns out to be a legitimate write boundary, leave it and record why in the Activity Log.
3. Note: `sync/routing.py` already has a read-only routing twin (`resolve_checkout_sync_routing_readonly`) from #1916 — this WP only changes the identity call, not routing.

**Validation**: `grep -n "ensure_identity(" src/specify_cli/sync/` returns nothing after this subtask.

### T008 — Swap tracker read-context identity call sites

**Steps**:
1. `tracker/origin.py:452` and `cli/commands/tracker.py:680`: swap to `resolve_identity` **only if** read-context.
2. `cli/commands/tracker.py:680` — verify whether this is part of an explicit `tracker bind`/connect (a write boundary). If it is genuinely a write-authorized action, **leave `ensure_identity`** and document it. Otherwise swap.
3. Do not touch `tracker/saas_service.py` or `tracker/config.py` (WP03).

**Validation**: any remaining `ensure_identity` in tracker read paths is justified in the Activity Log.

### T009 — Confirm init write boundary unchanged

**Steps**:
1. Confirm `cli/commands/init.py:99` and `:863` still call `ensure_identity` (these MUST persist).
2. Add a one-line comment at each marking it the write-authorized boundary (so a future reader does not "fix" it to `resolve_identity`).
3. No functional change.

**Validation**: `grep -n "ensure_identity(" src/specify_cli/` shows only `init.py` (2 sites).

### T010 — Integration test: emit is side-effect-free + stable

**File**: `tests/specify_cli/sync/test_emit_readonly_identity.py`.

**Cases** (use per-worker HOME isolation; SaaS sync enabled):
- Given an incomplete-identity checkout, emitting a status event leaves `config.yaml` byte-identical and `git status --porcelain` unchanged (FR-001, FR-002, AS-2).
- Two consecutive emits produce events carrying the **same** `project_uuid` and `build_id` (NFR-001).
- With sync disabled/unauthenticated, the emit path is still side-effect-free (FR-008, AS-6).

**Validation**: ≥90% coverage on changed lines; test deterministic.

## Test Strategy

```bash
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/sync/test_emit_readonly_identity.py -q
grep -rn "ensure_identity(" src/specify_cli/ | grep -v -e "init.py" -e "cli/commands/tracker.py"   # expect: empty
.venv/bin/mypy --strict src/specify_cli/sync/ src/specify_cli/tracker/origin.py src/specify_cli/cli/commands/tracker.py
.venv/bin/ruff check src/specify_cli/sync/
```

## Risks & Mitigations

- **Risk**: a "read" call site is actually a write boundary. **Mitigation**: read each enclosing function; when in doubt, leave `ensure_identity` and document — never silently turn a persist into a no-op for an intentional write.
- **Risk**: `cli/commands/tracker.py:680` is an explicit bind. **Mitigation**: T008 explicitly checks this; coordinate with WP03's explicit-bind path.
- **Risk**: drift if WP01 not merged first. **Mitigation**: hard dependency on WP01.

## Review Guidance

- `grep ensure_identity(` shows only `init.py` and the `tracker bind` write boundary.
- Emit/sync/tracker-read paths import and use `resolve_identity`.
- Integration test proves no `config.yaml` write + stable identity.
- No allowlist changes anywhere.

## Activity Log

- 2026-06-30 — Prompt generated via /spec-kitty.tasks.
- 2026-06-30T15:01:52Z – claude:opus:python-pedro:implementer – shell_pid=6034 – Assigned agent via action command
- 2026-06-30T15:31:13Z – claude:opus:python-pedro:implementer – shell_pid=6034 – 8 read-path sites -> resolve_identity; init+tracker-bind write boundaries kept (AS-5); grep shows only init.py + tracker.py bind; mypy --strict (1 pre-existing origin.py:441 error)+ruff+tests green
- 2026-06-30T15:33:18Z – claude:opus:reviewer-renata:reviewer – shell_pid=30010 – Started review via action command
- 2026-06-30T15:46:57Z – user – shell_pid=30010 – APPROVED (renata A-E adjudication). (A) KEEP@tracker.py:680 CORRECT: _bind_saas reached ONLY from @app.command('bind') write boundary (AS-5); swapping would no-op an intentional persist. (B) 7 swaps all read/emit/background: emitter/routing/events/__init__/dossier confirmed read-context; events.py _seed_emitter_identity dead read_only_identity param removed cleanly, both branches now read-only via resolve_identity; origin.py _project_identity_payload feeds bind_resolve/bind_validate SERVER lookup, local persist still to meta.json not config.yaml. (C) 5 coupled test edits all minimal: 4 are pure mock-target swaps ensure->resolve_identity to track the production call; test_accept_readiness_no_write.py flip is CORRECT DIRECTION (default emit now must NOT write config.yaml per FR-001/FR-003/AS-2) and STRENGTHENS coverage (adds byte-identity + in-memory-completeness), positive-contrast test_write_authorized_ensure_identity_still_persists preserved. (D) mypy --strict: sole error origin.py:441 [no-any-return] PROVEN pre-existing (reproduced on merge-base origin.py, in _resolve_repo_root which WP02 never touched); WP02 changed lines strict-clean. (E) routing failures PROVEN pre-existing: identical queue.size()==265 shared-queue + missing config.toml leak reproduce on BASE routing.py; all 33 tests/sync master-process failures are shared-HOME/daemon env coupling unrelated to diff. Headline test test_emit_readonly_identity.py 4/4 PASS, genuinely asserts byte-identical config.yaml + clean git porcelain + stable uuid/build_id (not synthetic). 5 coupled files 125/125 PASS. ruff clean. grep end-state: ensure_identity only at project.py def + init.py(2) + tracker.py:680 bind. No --feature regressions, no dead code, no scope violations (init.py comment-only per T009).

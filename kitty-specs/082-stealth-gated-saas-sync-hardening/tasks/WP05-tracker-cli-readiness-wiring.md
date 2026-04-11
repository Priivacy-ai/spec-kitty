---
work_package_id: WP05
title: Tracker CLI readiness wiring and dual-mode tests
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-007
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
agent: "claude:sonnet:python-implementer:implementer"
shell_pid: "78529"
history:
- at: '2026-04-11T06:22:58Z'
  actor: claude:/spec-kitty.tasks
  event: created
  note: Generated from contracts/hosted_readiness.md, contracts/background_daemon_policy.md, and plan.md.
authoritative_surface: src/specify_cli/cli/commands/tracker.py
execution_mode: code_change
feature_slug: 082-stealth-gated-saas-sync-hardening
owned_files:
- src/specify_cli/cli/commands/tracker.py
- src/specify_cli/cli/commands/__init__.py
- tests/agent/cli/commands/test_tracker.py
- tests/agent/cli/commands/test_tracker_discover.py
- tests/agent/cli/commands/test_tracker_status.py
priority: P1
tags: []
---

# WP05 — Tracker CLI readiness wiring and dual-mode tests

## Objective

Replace the generic `_require_enabled()` guard in `src/specify_cli/cli/commands/tracker.py:50-54` with per-command `evaluate_readiness()` calls that produce actionable, per-prerequisite failure messages. Wire each tracker command to the correct readiness flags (`require_mission_binding` and `probe_reachability`) per `contracts/hosted_readiness.md`. Implement manual-mode CLI surfacing so `sync run`/`pull`/`push`/`publish` print stable wording and exit 0 when the background daemon policy is set to `manual`. Parametrize the existing tracker test suites over both rollout-on and rollout-off modes and assert the per-prerequisite wording byte-wise.

## Context

This is the integration WP. It depends on all four preceding WPs:

- **WP01** ships `is_saas_sync_enabled` at the canonical import path (`specify_cli.saas.rollout`), which this WP switches over to from the BC shim at `cli/commands/__init__.py:37-40`.
- **WP02** ships the `HostedReadiness` evaluator that replaces `_require_enabled()`.
- **WP03** ships the `BackgroundDaemonPolicy` config field consulted by the manual-mode path.
- **WP04** ships `DaemonIntent` and the intent-gated `ensure_sync_daemon_running()` — this WP's sync commands pass `REMOTE_REQUIRED` and handle the `policy_manual` outcome.

**The conditional Typer registration pattern stays unchanged.** `cli/commands/__init__.py:37-40, 71-72` currently does a conditional import + conditional `add_typer(...)`. That mechanism is correct and this WP preserves it; the only change is the source of the import (`specify_cli.saas.rollout` instead of `specify_cli.tracker.feature_flags`). The existing pattern already ensures customers without the env var never see the tracker group at all.

**Manual-mode surfacing**: When a sync command calls the daemon with `REMOTE_REQUIRED` and the outcome is `policy_manual`, the command must print the stable wording from `contracts/background_daemon_policy.md` and exit 0 — this is not an error, the operator chose it.

**Per-command readiness flags** (from `contracts/hosted_readiness.md`):

| Command | `require_mission_binding` | `probe_reachability` |
|---|---|---|
| `providers` | `False` | `False` |
| `bind` | `False` | `False` |
| `discover` | `True` | `False` |
| `status` | `True` | `False` |
| `map add` | `True` | `False` |
| `map list` | `True` | `False` |
| `sync pull` | `True` | `True` |
| `sync push` | `True` | `True` |
| `sync run` | `True` | `True` |
| `sync publish` | `True` | `True` |
| `unbind` | `True` | `False` |

**Branch strategy**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main. Execution worktrees are allocated per computed lane from `lanes.json`; this WP depends on the tips of Lane A (WP02) and Lane B (WP04) and runs after both.

## Files touched

| File | Action | Notes |
|---|---|---|
| `src/specify_cli/cli/commands/tracker.py` | **modify** | Replace callback guard with per-command readiness; add manual-mode surfacing on sync commands. |
| `src/specify_cli/cli/commands/__init__.py` | **modify** | Switch conditional import source to `specify_cli.saas.rollout`. |
| `tests/agent/cli/commands/test_tracker.py` | **modify** | Parametrize over rollout-on/off × prerequisite-state matrix. |
| `tests/agent/cli/commands/test_tracker_discover.py` | **modify** | Readiness-aware assertions. |
| `tests/agent/cli/commands/test_tracker_status.py` | **modify** | Readiness-aware + manual-mode behavior. |

## Subtasks

### T021 — Rewrite tracker callback to use per-command `evaluate_readiness()`

**Purpose**: Deliver per-prerequisite failure messages that name the missing prerequisite and give one concrete next action (NFR-002).

**Steps**:

1. In `src/specify_cli/cli/commands/tracker.py`, remove or repurpose `_require_enabled()` — its generic behavior is replaced.
2. Add a module-level dispatch table keyed by Typer subcommand name, matching the table in the Context section above:

   ```python
   _COMMAND_READINESS_FLAGS: dict[str, tuple[bool, bool]] = {
       "providers": (False, False),
       "bind": (False, False),
       "discover": (True, False),
       "status": (True, False),
       "map.add": (True, False),   # or whatever joint name Typer uses
       "map.list": (True, False),
       "sync.pull": (True, True),
       "sync.push": (True, True),
       "sync.run": (True, True),
       "sync.publish": (True, True),
       "unbind": (True, False),
   }
   ```

   Verify the exact command-name strings against the current Typer app structure at lines 32–43 before finalizing the keys.

3. Update `tracker_callback()` (currently calls `_require_enabled()` at line 81) to:
   - Resolve the invoked subcommand name from the Typer `Context` (`ctx.invoked_subcommand` or equivalent).
   - Look up the `(require_mission_binding, probe_reachability)` tuple from the dispatch table.
   - Resolve `repo_root` from the current working directory (follow existing pattern in `tracker.py`).
   - Resolve `feature_slug` from the active mission binding or from `meta.json` — whatever the existing tracker code does today.
   - Call `from specify_cli.saas.readiness import evaluate_readiness; result = evaluate_readiness(repo_root=..., feature_slug=..., require_mission_binding=..., probe_reachability=...)`.
   - If `not result.is_ready`, print `result.message`, a blank line, and `result.next_action` to stdout (or stderr — match the existing tracker error-output convention), then `raise typer.Exit(code=1)`.
   - Otherwise, proceed to the subcommand body.

4. Defense-in-depth: include `ROLLOUT_DISABLED` in the failure handling even though the conditional import in `cli/commands/__init__.py` should have already hidden the group. This protects against import-time env-var state drift.

**Files**: `src/specify_cli/cli/commands/tracker.py` (modifications, ~80 lines net change)

**Validation**: Manual smoke test with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and no auth → `spec-kitty tracker status` prints the `MISSING_AUTH` message. mypy --strict clean.

### T022 — Manual-mode CLI surfacing for sync commands

**Purpose**: When `REMOTE_REQUIRED` commands encounter `policy_manual`, print stable wording and exit 0 (not an error).

**Steps**:

1. For each of `sync pull`, `sync push`, `sync run`, `sync publish`, locate the daemon startup call. After WP04 landed, these call `ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED)` and receive a `DaemonStartOutcome`.

2. Handle each outcome:
   - `started=True` → continue the command normally.
   - `skipped_reason == "policy_manual"` → print the stable wording (byte-wise asserted by tests):

     ```
     Background sync is in manual mode (`[sync].background_daemon = "manual"`).
     Run `spec-kitty sync run` to perform a one-shot remote sync.
     ```

     Then `raise typer.Exit(code=0)`. Do **not** raise exit code 1 — manual mode is not an error.

     **Exception**: When `sync run` itself encounters `policy_manual`, the wording above is misleading (it tells the user to run the command they just ran). For `sync run` specifically, print:

     ```
     Background sync is in manual mode. Running a one-shot remote sync now.
     ```

     and proceed with the command body as a foreground one-shot.

   - `skipped_reason == "rollout_disabled"` → defense-in-depth: should be unreachable because the command group is hidden; print a stable disabled-message and exit 1.
   - `skipped_reason.startswith("start_failed:")` → print the inner reason and exit 1 (preserve current error path).
   - `skipped_reason == "intent_local_only"` → unreachable by construction (these commands pass `REMOTE_REQUIRED`); assert-and-crash is acceptable because it would indicate a code bug.

3. Define the stable wording once as a module-level constant (e.g., `_MANUAL_MODE_MESSAGE`) so tests can import and assert against it.

**Files**: `src/specify_cli/cli/commands/tracker.py` (extended, ~40 lines)

**Validation**: Manual smoke test with `[sync].background_daemon = "manual"` → `spec-kitty tracker sync pull` prints the manual-mode message and exits 0.

### T023 — Switch conditional import in `cli/commands/__init__.py` to `specify_cli.saas.rollout`

**Purpose**: Remove the dependency on the BC shim from the one critical registration path.

**Steps**:

1. In `src/specify_cli/cli/commands/__init__.py`, locate the import at lines 37–40 (currently something like `from specify_cli.tracker.feature_flags import is_saas_sync_enabled`).
2. Change the import to `from specify_cli.saas.rollout import is_saas_sync_enabled`.
3. Do **not** change any other logic. The conditional `if is_saas_sync_enabled():` block around lines 71–72 stays identical.
4. The BC shims from WP01 continue to live on for any third-party or internal caller that has not yet migrated — this WP only moves the single most important call site.

**Files**: `src/specify_cli/cli/commands/__init__.py` (one-line import change)

**Validation**: `spec-kitty --help` with and without `SPEC_KITTY_ENABLE_SAAS_SYNC=1` behaves identically to before (tracker hidden vs visible).

### T024 — Parametrize `tests/agent/cli/commands/test_tracker.py` over rollout × prerequisite matrix

**Purpose**: Make dual-mode behavior a test-time assertion, not an ops-time surprise.

**Steps**:

1. Read the existing `tests/agent/cli/commands/test_tracker.py:22-66` to understand the current test pattern (fresh Typer app per test, monkey-patch env).
2. Introduce a `mode` fixture parametrization:

   ```python
   @pytest.fixture(params=["rollout_disabled", "rollout_enabled"])
   def rollout_mode(request, monkeypatch):
       if request.param == "rollout_disabled":
           monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
       else:
           monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
       yield request.param
   ```

3. For rollout-disabled mode, assert that:
   - `spec-kitty --help` output does not contain `"tracker"` (use the Typer test runner's `invoke`)
   - Direct invocation `spec-kitty tracker status` returns a "no such command" exit code (matching current typer behavior)

4. For rollout-enabled mode, add a prerequisite-state matrix: stub the readiness probes (via the shared `tests/saas/conftest.py` fixtures — cross-import them) and assert each state produces the expected byte-wise message.

5. Re-use the existing fresh-app pattern so env-var changes take effect. Do **not** cache the Typer app across parametrizations.

6. Where existing tests already exist, extend them rather than replacing — preserve the current regression coverage.

**Files**: `tests/agent/cli/commands/test_tracker.py` (modifications, ~150 lines of net change)

**Validation**: `pytest tests/agent/cli/commands/test_tracker.py -q` green in both modes.

### T025 — Update `tests/agent/cli/commands/test_tracker_discover.py` to readiness-aware

**Purpose**: The existing `discover` test uses the env-var flag; make it use readiness-state fixtures instead.

**Steps**:

1. Import the shared `rollout_enabled`/`rollout_disabled` fixtures and the auth/config/binding factories from `tests/saas/conftest.py`.
2. Parametrize the existing discover tests over both modes.
3. For rollout-enabled mode, additionally assert that:
   - Missing auth → `MISSING_AUTH` message and exit 1
   - Missing host config → `MISSING_HOST_CONFIG` message and exit 1
   - All prerequisites present → discover flow succeeds (mock the actual HTTP discovery if necessary, matching the existing test pattern)

**Files**: `tests/agent/cli/commands/test_tracker_discover.py` (modifications)

**Validation**: `pytest tests/agent/cli/commands/test_tracker_discover.py -q` green.

### T026 — Update `tests/agent/cli/commands/test_tracker_status.py` for readiness + manual-mode

**Purpose**: The existing `status` test uses the env-var flag; extend with manual-mode coverage.

**Steps**:

1. Same fixture approach as T025.
2. Add a test for the `policy_manual` outcome: set `background_daemon=manual` via `SyncConfig` fixture, invoke `spec-kitty tracker sync pull` (or whichever command this test file covers), and assert:
   - Exit code is `0` (not `1`)
   - Stdout contains the stable `_MANUAL_MODE_MESSAGE` wording
3. Add a test for the exception path: stub a readiness probe to raise, verify the result is `HOST_UNREACHABLE` and the message is printed (this validates the try/except in the evaluator from WP02 is exercised via the CLI path).

**Files**: `tests/agent/cli/commands/test_tracker_status.py` (modifications)

**Validation**: `pytest tests/agent/cli/commands/test_tracker_status.py -q` green.

## Test Strategy

This WP is primarily integration and test coverage. The implementation touches CLI wiring; tests lock down:
1. Hidden surface in rollout-disabled mode (NFR-001)
2. Per-prerequisite failure messages in rollout-enabled mode (NFR-002)
3. Manual-mode exit 0 with stable wording (FR-006 / NFR-003)
4. Every tracker command's readiness flags match the contract table

All tracker test modules parametrize over both rollout modes. Shared fixtures live in `tests/saas/conftest.py` (from WP02); if the cross-package import does not work, duplicate the two rollout fixtures into a local `tests/agent/cli/commands/conftest.py` — do not silently drop the dual-mode requirement.

## Definition of Done

- [ ] `_require_enabled()` is replaced by a per-command readiness dispatch in `tracker.py`.
- [ ] Every tracker subcommand uses the `(require_mission_binding, probe_reachability)` flags from the contract table.
- [ ] `sync pull`/`push`/`run`/`publish` handle `policy_manual` with exit 0 and stable wording.
- [ ] `cli/commands/__init__.py` imports `is_saas_sync_enabled` from `specify_cli.saas.rollout` (not the shim).
- [ ] All three tracker test modules are parametrized over rollout-on and rollout-off modes.
- [ ] Byte-wise wording assertions exist for every `ReadinessState` failure that reaches stdout.
- [ ] `pytest -q` full suite green.
- [ ] `mypy --strict src/specify_cli/cli/commands/tracker.py` clean.
- [ ] Manual smoke test: quickstart.md Scenarios 1, 2, 3 all pass on a local machine.
- [ ] No files outside `owned_files` modified.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Typer conditional import evaluates at module-load time; tests that flip env vars after import don't take effect | Mirror the existing "fresh Typer app per test" pattern in `test_tracker.py:22-66`. Do not reuse a cached `app` across parametrizations. |
| Autouse fixture in `tests/conftest.py:57-60` sets the env var ON by default and masks rollout-disabled tests | `rollout_disabled` fixture uses `monkeypatch.delenv(..., raising=False)` explicitly. Verified pattern from R-006. |
| Subcommand name resolution from Typer context differs between nested and top-level commands | Inspect `ctx.invoked_subcommand` AND parent context; joint names like `map.add` may require walking the context stack. Inspect the current tracker Typer app structure before coding. |
| Stable wording drifts between implementation and tests | Define `_WORDING` / `_MANUAL_MODE_MESSAGE` as module-level constants in `tracker.py` and `readiness.py`. Tests import and compare. |
| Cross-package fixture import (`tests/saas/conftest.py` → `tests/agent/cli/commands/`) fails | Fallback: duplicate only the two rollout fixtures into a local conftest. The auth/config/binding factories can remain in `tests/saas/` and be imported directly if pytest discovery permits. |
| Manual-mode behavior for `sync run` specifically (user just invoked the command the wording recommends) | Special-cased in T022 — `sync run` proceeds as a foreground one-shot instead of printing the "run sync run" message. |

## Reviewer Guidance

- Verify every row of the per-command flag table in this WP is reflected in the `_COMMAND_READINESS_FLAGS` dispatch in `tracker.py`.
- Verify byte-wise wording assertions for every non-READY state at the CLI boundary.
- Confirm `cli/commands/__init__.py` still hides the tracker group when the env var is unset — run `spec-kitty --help` manually both ways.
- Confirm manual-mode exit code is 0 (not 1).
- Walk through `quickstart.md` Scenarios 1, 2, 3 on a local machine to validate the operator story end-to-end.
- Ensure the autouse fixture in `tests/conftest.py:57-60` is unchanged.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Activity Log

- 2026-04-11T09:11:21Z – claude:sonnet:python-implementer:implementer – shell_pid=78529 – Started implementation via action command
- 2026-04-11T09:30:29Z – claude:sonnet:python-implementer:implementer – shell_pid=78529 – Tracker CLI wired to HostedReadiness per-command; manual-mode surfacing; dual-mode parametrized tests

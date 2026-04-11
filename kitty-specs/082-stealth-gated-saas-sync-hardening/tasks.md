# Tasks — 082 Stealth-Gated SaaS Sync Hardening

**Feature dir**: `/Users/robert/spec-kitty-dev/linear2/spec-kitty/kitty-specs/082-stealth-gated-saas-sync-hardening/`
**Planning base branch**: `main`
**Merge target branch**: `main`
**Generated**: 2026-04-11T06:22:58Z
**Inputs**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

---

## Overview

This mission preserves the stealth rollout posture of the CLI's hosted SaaS/tracker surface and hardens the *enabled-mode* experience inside that gate. Work is decomposed into **6 work packages** along three concurrent threads (rollout+readiness, daemon+config, CLI integration) plus a documentation package. No customer-facing surface appears unless the `SPEC_KITTY_ENABLE_SAAS_SYNC` env var is set; inside enabled mode, a new shared `HostedReadiness` evaluator replaces ad hoc preflight checks and the background sync daemon becomes intent-gated with an operator-facing config toggle.

**Total subtasks**: 29
**Work packages**: 6
**Parallelization**: WP01 and WP03 are entry points with no dependencies; WP02 depends on WP01; WP04 depends on WP01+WP03; WP05 depends on WP01+WP02+WP03+WP04; WP06 depends on WP01+WP02+WP03+WP04.

---

## Subtask Index

| ID   | Description                                                                                              | WP   | Parallel |
|------|----------------------------------------------------------------------------------------------------------|------|----------|
| T001 | Create `src/specify_cli/saas/__init__.py` with rollout-symbol exports                                    | WP01 | —        |
| T002 | Create canonical `src/specify_cli/saas/rollout.py` (`is_saas_sync_enabled`, `saas_sync_disabled_message`) | WP01 | —        |
| T003 | Convert `src/specify_cli/tracker/feature_flags.py` to a re-export shim                                   | WP01 | [P]      |
| T004 | Convert `src/specify_cli/sync/feature_flags.py` to a re-export shim                                      | WP01 | [P]      |
| T005 | Write `tests/saas/test_rollout.py` (env-var variants, shim re-export, stable message)                    | WP01 | —        |
| T006 | Create `src/specify_cli/saas/readiness.py` with `ReadinessState`, `ReadinessResult`, `evaluate_readiness` | WP02 | —        |
| T007 | Implement the stable failure-message catalog per `contracts/hosted_readiness.md`                         | WP02 | —        |
| T008 | Implement check ordering, short-circuit, and exception→`HOST_UNREACHABLE` conversion                     | WP02 | —        |
| T009 | Create `tests/saas/conftest.py` with rollout + auth/config/binding fixtures                              | WP02 | —        |
| T010 | Write `tests/saas/test_readiness_unit.py` (stubbed probes, every state, wording, ordering)               | WP02 | [P]      |
| T011 | Write `tests/saas/test_readiness_integration.py` (real evaluator, tmp_path fixtures, local stub server)  | WP02 | [P]      |
| T012 | Add `BackgroundDaemonPolicy` enum and `background_daemon` field to `SyncConfig`                          | WP03 | —        |
| T013 | Update TOML loader: parse `[sync].background_daemon` (case-insensitive, warn+default, reject empty)     | WP03 | —        |
| T014 | Write `tests/sync/test_config_background_daemon.py`                                                      | WP03 | —        |
| T015 | Add `DaemonIntent` enum and `DaemonStartOutcome` dataclass to `src/specify_cli/sync/daemon.py`           | WP04 | —        |
| T016 | Refactor `ensure_sync_daemon_running()` — mandatory `intent=`, full decision matrix, outcome return     | WP04 | —        |
| T017 | Update `src/specify_cli/dashboard/server.py` to pass `intent=LOCAL_ONLY`                                 | WP04 | [P]      |
| T018 | Update `src/specify_cli/dashboard/handlers/api.py` (read endpoints `LOCAL_ONLY`; sync-now `REMOTE_REQUIRED`) | WP04 | [P]  |
| T019 | Update `src/specify_cli/sync/events.py` to pass `intent=REMOTE_REQUIRED`                                 | WP04 | [P]      |
| T020 | Write `tests/sync/test_daemon_intent_gate.py` (decision matrix, missing-intent TypeError, audit-grep guard) | WP04 | — |
| T021 | Rewrite tracker callback in `src/specify_cli/cli/commands/tracker.py` — per-command `evaluate_readiness()` | WP05 | — |
| T022 | Implement manual-mode CLI surfacing for `sync run`/`pull`/`push`/`publish` (exit 0, stable wording)      | WP05 | —        |
| T023 | Update `src/specify_cli/cli/commands/__init__.py` conditional import to source from `specify_cli.saas.rollout` | WP05 | — |
| T024 | Parametrize `tests/agent/cli/commands/test_tracker.py` (rollout-on/off × prerequisite-state matrix)      | WP05 | [P]      |
| T025 | Update `tests/agent/cli/commands/test_tracker_discover.py` to readiness-aware assertions                 | WP05 | [P]      |
| T026 | Update `tests/agent/cli/commands/test_tracker_status.py` (readiness-aware + manual-mode behavior)        | WP05 | [P]      |
| T027 | Write `architecture/ADR-XXXX-saas-rollout-and-readiness.md` (DIRECTIVE_003)                              | WP06 | —        |
| T028 | Update `architecture/README.md` index to reference the new ADR                                           | WP06 | —        |
| T029 | Refresh `docs/` cross-references if any existing SaaS-sync doc points at the old single gate             | WP06 | —        |

*The `[P]` column marks subtasks that can be parallelized **within** their WP (different files, no shared state). It is a reference column, not a status column.*

---

## Work Package WP01 — Canonical rollout gate and BC shims

**Prompt file**: [tasks/WP01-canonical-rollout-gate-and-bc-shims.md](tasks/WP01-canonical-rollout-gate-and-bc-shims.md)
**Priority**: P1 (foundation for all enabled-mode work)
**Dependencies**: none
**Estimated prompt size**: ~400 lines
**Independent test**: Run `pytest tests/saas/test_rollout.py` plus a smoke-import check on the two BC shims; verify the existing `tests/conftest.py` autouse fixture still works unchanged.

**Goal**: Consolidate the duplicated `is_saas_sync_enabled()` implementations into a single canonical module at `src/specify_cli/saas/rollout.py`, expose it at the package root, and convert `tracker/feature_flags.py` and `sync/feature_flags.py` into thin re-export shims so existing callers keep working with no rename.

### Included subtasks

- [ ] T001 Create `src/specify_cli/saas/__init__.py` with rollout-symbol exports (WP01)
- [ ] T002 Create canonical `src/specify_cli/saas/rollout.py` (WP01)
- [ ] T003 Convert `src/specify_cli/tracker/feature_flags.py` to a re-export shim (WP01)
- [ ] T004 Convert `src/specify_cli/sync/feature_flags.py` to a re-export shim (WP01)
- [ ] T005 Write `tests/saas/test_rollout.py` (WP01)

### Implementation sketch

1. Create the new `saas/` package directory with `__init__.py` importing and re-exporting `is_saas_sync_enabled` and `saas_sync_disabled_message` from `specify_cli.saas.rollout`. Do **not** import `readiness` here — WP02 owns readiness and accesses are via the module path `specify_cli.saas.readiness`.
2. Move the canonical implementation into `rollout.py`, matching byte-for-byte the wording from `contracts/saas_rollout.md`.
3. Rewrite both `feature_flags.py` modules to be 3-to-5-line re-exports. Add a `# Retained as backwards-compatibility shim; canonical home is specify_cli.saas.rollout.` comment so future contributors know why.
4. Parametrize the new unit tests over every truthy/falsy env value listed in the contract.

### Parallel opportunities

- T003 and T004 are `[P]` — the two shim conversions are independent files.

### Risks

- The existing autouse fixture at `tests/conftest.py:57-60` imports `is_saas_sync_enabled` via one of the shim modules; if the shim rewrite forgets to preserve the symbol name, the entire test suite breaks. Mitigation: run the full test suite after the shim conversion, not just `tests/saas/`.
- The shims are imported by `src/specify_cli/cli/commands/__init__.py:37-40, 71-72` (see R-001 research). WP05 will switch that import to `specify_cli.saas.rollout`, but WP01 must preserve the shim-level import so the CLI still works between WP01 and WP05 landing.

---

## Work Package WP02 — HostedReadiness evaluator and test layers

**Prompt file**: [tasks/WP02-hosted-readiness-evaluator-and-tests.md](tasks/WP02-hosted-readiness-evaluator-and-tests.md)
**Priority**: P1
**Dependencies**: WP01
**Estimated prompt size**: ~500 lines
**Independent test**: `pytest tests/saas/test_readiness_unit.py tests/saas/test_readiness_integration.py` — all six `ReadinessState` members reached with stable wording; integration layer drives the real evaluator against `tmp_path` fixtures.

**Goal**: Introduce the shared `HostedReadiness` evaluator that commands call instead of ad hoc preflight checks. Deliver both a stubbed unit layer and a smaller integration layer exercising the real evaluator.

### Included subtasks

- [ ] T006 Create `src/specify_cli/saas/readiness.py` with `ReadinessState`, `ReadinessResult`, `evaluate_readiness` (WP02)
- [ ] T007 Implement the stable failure-message catalog per contract (WP02)
- [ ] T008 Implement check ordering, short-circuit, and exception→`HOST_UNREACHABLE` conversion (WP02)
- [ ] T009 Create `tests/saas/conftest.py` with rollout + auth/config/binding fixtures (WP02)
- [ ] T010 Write `tests/saas/test_readiness_unit.py` with stubbed probes (WP02)
- [ ] T011 Write `tests/saas/test_readiness_integration.py` with the real evaluator (WP02)

### Implementation sketch

1. `readiness.py` defines the `ReadinessState` `str`-enum with the six members in declaration order (which is also check order); the frozen `ReadinessResult` dataclass; and `evaluate_readiness()` with keyword-only arguments per `contracts/hosted_readiness.md`.
2. Each prerequisite probe is implemented as a separate module-level helper (`_probe_rollout`, `_probe_auth`, `_probe_host_config`, `_probe_reachability`, `_probe_mission_binding`) so unit tests can monkey-patch them individually.
3. The top-level evaluator wraps the probe dispatch in a try/except that converts **any** exception into `ReadinessState.HOST_UNREACHABLE` with `details["error"]` set — the evaluator never raises to callers (contract requirement).
4. `conftest.py` provides `rollout_enabled`, `rollout_disabled` monkeypatch fixtures plus factory fixtures that build tmp_path-backed auth, config, and binding state used by both unit and integration tests.
5. Unit tests stub the probe helpers; integration tests let them run against real fixture files plus a `http.server`-based local stub for the reachability probe (no real network).

### Parallel opportunities

- T010 and T011 are `[P]` (unit and integration tests are independent files once the evaluator and conftest exist).

### Risks

- Drift between stub-shaped and real-shaped fixtures. Mitigation: share the `_Fixtures` dataclass from conftest across both test files so a stub cannot diverge silently.
- Reachability stub server port conflicts in CI. Mitigation: bind to `127.0.0.1:0` and read the assigned port back.

---

## Work Package WP03 — BackgroundDaemonPolicy config extension

**Prompt file**: [tasks/WP03-background-daemon-policy-config.md](tasks/WP03-background-daemon-policy-config.md)
**Priority**: P2
**Dependencies**: none
**Estimated prompt size**: ~250 lines
**Independent test**: `pytest tests/sync/test_config_background_daemon.py` — missing-key default to AUTO, case-variants round-trip, unknown-value warns, empty string rejected.

**Goal**: Extend the existing `SyncConfig` dataclass with a new user-level TOML key `[sync].background_daemon = "auto" | "manual"` (default `"auto"`). This is the config surface that WP04 will consult to decide whether to auto-start the daemon on `REMOTE_REQUIRED` intent.

### Included subtasks

- [ ] T012 Add `BackgroundDaemonPolicy` enum and `background_daemon` field to `SyncConfig` (WP03)
- [ ] T013 Update TOML loader for case-insensitive parsing with warn+default and empty-string rejection (WP03)
- [ ] T014 Write `tests/sync/test_config_background_daemon.py` (WP03)

### Implementation sketch

1. Add the new enum to `src/specify_cli/sync/config.py` next to the existing dataclass definition (lines 12–70); wire `background_daemon: BackgroundDaemonPolicy = BackgroundDaemonPolicy.AUTO` into `SyncConfig`.
2. The loader path reads the raw value, `.casefold()`s it, matches against known members, warns to stderr on unknown (falling back to `AUTO`), and raises a typed config error on empty string.
3. The test module covers: missing key → AUTO; `"auto"`/`"AUTO"`/`"Auto"` → AUTO; `"manual"`/`"Manual"` → MANUAL; `"banana"` → one-line warning + AUTO; empty string → raises.

### Parallel opportunities

- None internal. This WP runs in parallel with WP01/WP02 because it touches a different file tree.

### Risks

- SyncConfig is loaded early in many code paths (daemon, dashboard, sync events). A typo in the loader rejects any existing config. Mitigation: regression-test that a config file **without** the new key still loads cleanly.

---

## Work Package WP04 — Intent-gated daemon and caller audit

**Prompt file**: [tasks/WP04-intent-gated-daemon-and-caller-audit.md](tasks/WP04-intent-gated-daemon-and-caller-audit.md)
**Priority**: P1
**Dependencies**: WP01, WP03
**Estimated prompt size**: ~550 lines
**Independent test**: `pytest tests/sync/test_daemon_intent_gate.py` — every row of the rollout × intent × policy decision matrix asserted; TypeError regression guard; audit-grep guard scans the repo for unauthorized `ensure_sync_daemon_running` call sites.

**Goal**: Convert `ensure_sync_daemon_running()` from unconditional auto-start to an intent-gated startup function governed by the new `DaemonIntent` enum and the `BackgroundDaemonPolicy` config from WP03. Update the three existing call sites to pass explicit intent. Ensure help and local-only commands never spawn the daemon on enabled machines.

### Included subtasks

- [ ] T015 Add `DaemonIntent` enum and `DaemonStartOutcome` dataclass to `src/specify_cli/sync/daemon.py` (WP04)
- [ ] T016 Refactor `ensure_sync_daemon_running()` for mandatory `intent=`, apply decision matrix, return `DaemonStartOutcome` (WP04)
- [ ] T017 Update `src/specify_cli/dashboard/server.py` caller to `intent=LOCAL_ONLY` (WP04)
- [ ] T018 Update `src/specify_cli/dashboard/handlers/api.py` callers (LOCAL_ONLY reads, REMOTE_REQUIRED sync-now) (WP04)
- [ ] T019 Update `src/specify_cli/sync/events.py` event-upload caller to `REMOTE_REQUIRED` (WP04)
- [ ] T020 Write `tests/sync/test_daemon_intent_gate.py` (decision matrix, TypeError guard, audit-grep guard) (WP04)

### Implementation sketch

1. Add the enum and the frozen dataclass at the top of `daemon.py`. `DaemonStartOutcome` includes `started`, `skipped_reason`, and `pid`.
2. Rewrite `ensure_sync_daemon_running()` to accept `*, intent: DaemonIntent, config: SyncConfig | None = None`. The function:
   - Returns `(started=False, skipped_reason="rollout_disabled")` if `is_saas_sync_enabled()` is `False`.
   - Returns `(started=False, skipped_reason="intent_local_only")` if intent is `LOCAL_ONLY`.
   - Returns `(started=False, skipped_reason="policy_manual")` if intent is `REMOTE_REQUIRED` and `config.background_daemon == MANUAL`.
   - Otherwise delegates to the existing start logic.
3. Update the three call sites per `contracts/background_daemon_policy.md`. Dashboard server startup → `LOCAL_ONLY`; dashboard read handlers → `LOCAL_ONLY`; dashboard sync-now handler → `REMOTE_REQUIRED`; `sync/events.py` upload path → `REMOTE_REQUIRED`.
4. The audit-grep guard in the test module walks `src/` and asserts that every `ensure_sync_daemon_running(` match appears in the contract's caller-allowlist. Any new caller must be added to both the allowlist and the matrix tests.

### Parallel opportunities

- T017, T018, T019 are `[P]` once T015/T016 land.

### Risks

- The dashboard currently relies on implicit daemon startup to populate status data. With `LOCAL_ONLY`, that implicit path disappears. Mitigation: dashboard should render daemon state from the on-disk state file (`DAEMON_STATE_FILE`) rather than from a live process handle, and the WP must verify that pattern holds before landing.
- `sync/events.py` may call the function from inside async contexts; ensure the new outcome return is handled synchronously (the existing code appears synchronous based on exploration).
- `REMOTE_REQUIRED` + `MANUAL` returns `started=False` and the caller must not crash. Dashboard handler callers log at INFO; CLI callers are handled by WP05.

---

## Work Package WP05 — Tracker CLI readiness wiring and dual-mode tests

**Prompt file**: [tasks/WP05-tracker-cli-readiness-wiring.md](tasks/WP05-tracker-cli-readiness-wiring.md)
**Priority**: P1
**Dependencies**: WP01, WP02, WP03, WP04
**Estimated prompt size**: ~600 lines
**Independent test**: `pytest tests/agent/cli/commands/test_tracker.py tests/agent/cli/commands/test_tracker_discover.py tests/agent/cli/commands/test_tracker_status.py` — parametrized over rollout-on and rollout-off modes; prerequisite-state matrix assertions; manual-mode surfacing verified.

**Goal**: Replace the generic `_require_enabled()` guard in the tracker CLI with per-command `evaluate_readiness()` calls that produce actionable, per-prerequisite failure messages. Ensure manual-mode policy prints the stable wording and exits 0. Parametrize existing tracker tests over both rollout modes.

### Included subtasks

- [ ] T021 Rewrite tracker callback in `src/specify_cli/cli/commands/tracker.py` to use per-command `evaluate_readiness()` (WP05)
- [ ] T022 Implement manual-mode CLI surfacing for `sync run`/`pull`/`push`/`publish` (WP05)
- [ ] T023 Update `src/specify_cli/cli/commands/__init__.py` conditional import to source from `specify_cli.saas.rollout` (WP05)
- [ ] T024 Parametrize `tests/agent/cli/commands/test_tracker.py` over rollout × prerequisite-state matrix (WP05)
- [ ] T025 Update `tests/agent/cli/commands/test_tracker_discover.py` to readiness-aware assertions (WP05)
- [ ] T026 Update `tests/agent/cli/commands/test_tracker_status.py` (readiness-aware + manual-mode behavior) (WP05)

### Implementation sketch

1. `tracker.py` — replace the `tracker_callback()`'s call to `_require_enabled()` with a helper that looks up the command name from the Typer context, consults a dispatch table for the correct `(require_mission_binding, probe_reachability)` flags per `contracts/hosted_readiness.md`, calls `evaluate_readiness()`, and either proceeds or exits with code 1 printing `result.message` + blank line + `result.next_action`.
2. `sync run`, `sync pull`, `sync push`, `sync publish` additionally wrap their actual daemon call in a try that catches `DaemonStartOutcome(skipped_reason="policy_manual")` and prints the stable manual-mode wording, exiting 0.
3. `cli/commands/__init__.py` keeps its conditional import pattern — only rename the source to `specify_cli.saas.rollout`. The BC shims from WP01 still work, but the canonical import prevents future drift.
4. Test parametrization uses `pytest.mark.parametrize("mode", [("rollout_disabled", False), ("rollout_enabled", True)])` fixtures from `tests/saas/conftest.py` (import from the shared conftest, or create a local conftest that imports through).
5. Byte-wise wording assertions from the contract table: every prerequisite failure is asserted via `assert result.stdout.startswith("No SaaS authentication token")` etc.

### Parallel opportunities

- T024, T025, T026 are `[P]` once T021–T023 land.

### Risks

- The conditional Typer registration in `cli/commands/__init__.py` is evaluated at module-import time, which means the env-var read happens once per process. Tests that flip the env var **after** the CLI module is imported will not see the change. Mitigation: test harness should construct a fresh Typer app per test, mirroring the existing pattern in `test_tracker.py:22-66`.
- The existing autouse fixture in `tests/conftest.py:57-60` sets the env var ON by default; the dual-mode parametrization must `monkeypatch.delenv(...)` inside the rollout-off case **before** importing the CLI module.
- Stable wording assertions are fragile against copy-edits. Use a shared `WORDING` constant in the contract/module so tests and implementation stay aligned.

---

## Work Package WP06 — ADR and documentation

**Prompt file**: [tasks/WP06-adr-and-documentation.md](tasks/WP06-adr-and-documentation.md)
**Priority**: P3
**Dependencies**: WP01, WP02, WP03, WP04
**Estimated prompt size**: ~250 lines
**Independent test**: `rg "saas-rollout-and-readiness" architecture/ docs/` returns the new ADR in the index; `pytest -q` still passes end-to-end.

**Goal**: Capture the rollout/readiness split, daemon-policy-as-config choice, tracker-remains-ungated rationale, and future migration paths in an architecture decision record. Update the architecture index. Optionally refresh user-facing docs if existing SaaS-sync pointers need updating (DIRECTIVE_003 — Decision Documentation Requirement).

### Included subtasks

- [ ] T027 Write `architecture/ADR-XXXX-saas-rollout-and-readiness.md` (WP06)
- [ ] T028 Update `architecture/README.md` index to reference the new ADR (WP06)
- [ ] T029 Refresh `docs/` cross-references if any existing SaaS-sync doc points at the old single gate (WP06)

### Implementation sketch

1. Inspect `architecture/README.md` for the next available ADR number; rename the placeholder. Follow the ADR template already used in that directory.
2. ADR sections: Context (the stealth rollout posture and why), Decision (split rollout-gate from readiness evaluator, config-driven daemon policy, tracker stays ungated), Consequences (BC shims live on, future project-level config layering is documented but deferred, `HostedReadiness` becomes the single fan-in point for any new prerequisite), Alternatives Considered (single gate with per-command overrides; adding rollout to tracker package — both rejected with reasons from research.md).
3. Update `architecture/README.md`'s index with one new row.
4. Grep `docs/` for `SPEC_KITTY_ENABLE_SAAS_SYNC` and any "coming soon" notes — if a user-facing doc implies the gate is a single yes/no for all readiness, add a pointer to the new ADR. Skip if no such doc exists (the subtask is conditional).

### Parallel opportunities

- None internal. Depends on the substantive WPs landing so the ADR accurately reports what shipped.

### Risks

- The ADR risks drifting from the shipped implementation if written before the preceding WPs are merged. Mitigation: schedule this WP last in its lane; reviewer must diff the ADR against the actual implementation before approving.

---

## MVP Scope Recommendation

**Minimum viable delivery = WP01 + WP02 + WP05.** Those three packages restore the stealth posture, ship the shared readiness abstraction, and plumb it through the tracker CLI with dual-mode tests — the three highest-priority user stories (US1, US2, US3) plus FR-004 and NFR-002.

**Strongly recommended to bundle with MVP**: WP03 + WP04 (intent-gated daemon + config policy) address FR-005, FR-006, and NFR-003. Without them, US4 is not satisfied and help/local-only commands can still spawn the daemon on enabled machines.

**Defer-safe**: WP06 (ADR + docs) — the code ships correct without it, but DIRECTIVE_003 requires the decision trail before acceptance, so it should land in the same release window.

## Parallelization Highlights

- **Lane A** (rollout+readiness): WP01 → WP02 (sequential; WP02 imports from WP01's package)
- **Lane B** (config+daemon): WP03 → WP04 (sequential; WP04 consumes WP03's new enum)
- **Lane C** (CLI integration): WP05 (depends on Lane A tip and Lane B tip — runs after both)
- **Lane D** (docs): WP06 (depends on Lanes A+B; can run concurrently with WP05 if an agent starts the ADR skeleton early and updates it from merged code)

In practice, Lane A and Lane B can run in parallel from day one, Lane C merges afterward, and Lane D closes the loop.

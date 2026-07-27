# Implementation Plan: Stealth-Gated SaaS Sync Hardening

**Branch**: `082-stealth-gated-saas-sync-hardening` | **Date**: 2026-04-11 | **Spec**: [spec.md](/Users/robert/spec-kitty-dev/linear2/spec-kitty/kitty-specs/082-stealth-gated-saas-sync-hardening/spec.md)
**Input**: Feature specification from `/kitty-specs/082-stealth-gated-saas-sync-hardening/spec.md`

## Branch Strategy

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: `true`
- **Summary**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main.

## Summary

This mission preserves the stealth rollout posture of the hosted SaaS/tracker surface in the `spec-kitty` CLI and hardens the *enabled-mode* experience inside that gate. The customer-facing default remains "fail closed": with no `SPEC_KITTY_ENABLE_SAAS_SYNC` environment variable, the hosted `tracker` Typer command group is hidden via conditional registration and any hosted code path refuses to start network activity. Inside enabled mode, ad hoc preflight checks are replaced by a single shared `HostedReadiness` evaluator that returns discrete prerequisite states (auth, host config, host reachability, mission binding) and emits actionable per-prerequisite failure messages. The background sync daemon is converted from "auto-start whenever a sync code path runs" to **intent-gated startup** governed by a new operator-facing config key `sync.background_daemon: auto | manual` (default `auto`) on the existing user-level `~/.spec-kitty/config.toml`. Test coverage is reorganized to exercise both rollout-disabled and rollout-enabled flows: unit tests may stub the readiness resolver, but a smaller integration layer must drive the real evaluator against auth/config/binding fixtures. **No rollout logic is added to the external `spec-kitty-tracker==0.3.0` package.**

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty CLI)
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, pytest-asyncio, mypy --strict, `spec-kitty-tracker==0.3.0` (external, ungated, must remain unmodified by this mission)
**Storage**: User-level config TOML at `~/.spec-kitty/config.toml`, already managed by the existing `SyncConfig` **class** (not a dataclass) at `src/specify_cli/sync/config.py:12-70`. `SyncConfig` uses on-demand getter/setter methods (`get_server_url` / `set_server_url`, `get_max_queue_size` / `set_max_queue_size`) backed by a private `_load()` → `toml.load` / `_save()` → `atomic_write` pattern. This mission adds a third method pair `get_background_daemon()` / `set_background_daemon()` mirroring that shape; no new persistence mechanism. **Note**: the authoritative SaaS host URL for the hosted surface is `SPEC_KITTY_SAAS_URL` (per decision D-5 in `src/specify_cli/auth/config.py`), not `SyncConfig.get_server_url()`. The two coexist in the current codebase for legacy reasons; this mission's readiness evaluator consults `auth.config.get_saas_base_url()` as the canonical source.
**Testing**: pytest with parametrized rollout-on/rollout-off modes; integration layer using real `HostedReadiness` against fixture auth/config/binding state
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: Single Python project (`src/specify_cli/`)
**Performance Goals**: Readiness evaluation must complete in < 200 ms for the local-prerequisite checks (auth presence, config presence, mission binding); the optional reachability probe is bounded to a single short HTTP HEAD with ≤ 2 s timeout
**Constraints**:
- Customer machines without the env var must observe **zero** new network activity, **zero** new background processes, and **no new visible commands** (NFR-001, NFR-003)
- Enabled-mode failures must always name the missing prerequisite (NFR-002)
- The external `spec-kitty-tracker` package must not be modified or re-released in this mission (C-002)
- The existing autouse fixture in `tests/conftest.py:57-60` (`_enable_saas_sync_feature_flag`) must continue to default tests to "gate on" so existing tracker tests stay green; the new dual-mode tests opt out explicitly via `monkeypatch.delenv()`
**Scale/Scope**:
- ~6 source files touched (1 new package `src/specify_cli/saas/`, 2 existing `feature_flags.py` collapsed to re-exports, `tracker.py` callback rewrite, `sync/config.py` gains one new method pair on the existing class, `sync/daemon.py` intent gate, audit of the single `ensure_sync_daemon_running()` call site in `sync/events.py`)
- ~4 new test modules + parametrization of 3 existing modules
- 1 new ADR documenting the rollout-gate + readiness-abstraction split

## External SDK Consumption Surface

The CLI imports the following symbols from the **external** `spec-kitty-tracker==0.3.0` dependency. **This mission does not modify any of these imports, call sites, or the pinned version.** They are listed here as a stability assertion so reviewers can confirm the rollout-gating work does not accidentally leak into the tracker SDK's public API (C-002).

| Importer (file:line) | Symbols |
|---|---|
| `src/specify_cli/tracker/factory.py:44` | `BeadsConnector`, `BeadsConnectorConfig`, `FPConnector`, `FPConnectorConfig` |
| `src/specify_cli/tracker/store.py:29` | `CanonicalIssue`, `CanonicalIssueType`, `CanonicalLink`, `CanonicalStatus`, `ExternalRef`, `LinkType`, `SyncCheckpoint` (all from `spec_kitty_tracker.models`) |
| `src/specify_cli/tracker/local_service.py:169` | `ExternalRef` (from `spec_kitty_tracker.models`) |
| `src/specify_cli/tracker/local_service.py:220` | `FieldOwner`, `OwnershipMode`, `OwnershipPolicy`, `SyncEngine` (from `spec_kitty_tracker`) |

The rollout gate is owned by the CLI and SaaS only. `spec-kitty-tracker` remains ungated and version-pinned by downstream consumers (C-002). No WP in this mission modifies the `spec-kitty-tracker` package or this import surface.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Charter Topic | Requirement | Plan Compliance |
|---|---|---|
| **Languages and frameworks** | Python 3.11+, typer, rich, ruamel.yaml, pytest, mypy --strict | ✅ No new dependencies; uses existing CLI stack |
| **Test coverage (90%+)** | New code requires ≥90% coverage and integration tests for CLI commands | ✅ New `saas/readiness.py` and `saas/rollout.py` will land with parametrized unit tests + an integration test layer that exercises the real evaluator. Tracker callback rewrite gets new CLI integration tests for both gate-on and gate-off modes. |
| **mypy --strict** | All new modules must pass mypy --strict | ✅ New `saas/` package will be fully typed; `HostedReadiness` returns a typed enum + dataclass, no `Any` |
| **CLI < 2 s for typical projects** | Readiness checks must not slow common commands | ✅ Local checks are O(1) file reads; the reachability probe is opt-in (only invoked when enabled-mode commands explicitly require it) and bounded to ≤ 2 s |
| **Cross-platform** | Linux/macOS/Windows | ✅ Pure Python, no platform-specific code |
| **DIRECTIVE_003 — Decision Documentation** | Material decisions must be captured | ✅ ADR `architecture/ADR-0XX-saas-rollout-and-readiness.md` will document why rollout gate and readiness are split into two abstractions, why daemon policy is a config key not a CLI flag, and why tracker stays ungated |
| **DIRECTIVE_010 — Specification Fidelity** | Implementation must remain faithful to spec | ✅ Plan derives every technical choice from the locked spec posture; deviations would require spec amendment |

**Charter Check Result (pre-Phase 0)**: ✅ **PASS** — no violations, no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```
/Users/robert/spec-kitty-dev/linear2/spec-kitty/kitty-specs/082-stealth-gated-saas-sync-hardening/
├── spec.md                 # Locked feature specification (input)
├── plan.md                 # This file
├── research.md             # Phase 0 output
├── data-model.md           # Phase 1 output
├── quickstart.md           # Phase 1 output
└── contracts/              # Phase 1 output
    ├── saas_rollout.md
    ├── hosted_readiness.md
    └── background_daemon_policy.md
```

### Source Code (repository root)

```
src/specify_cli/
├── saas/                            # NEW shared package — single source of truth for rollout + readiness
│   ├── __init__.py                  # Public API: is_saas_sync_enabled, evaluate_readiness, ReadinessState, ReadinessResult
│   ├── rollout.py                   # NEW canonical rollout helper (consolidates duplicated feature_flags.py)
│   └── readiness.py                 # NEW HostedReadiness evaluator
│
├── tracker/
│   └── feature_flags.py             # MODIFIED — becomes thin re-export of src/specify_cli/saas/rollout.py (BC shim)
│
├── sync/
│   ├── feature_flags.py             # MODIFIED — becomes thin re-export of src/specify_cli/saas/rollout.py (BC shim)
│   ├── config.py                    # MODIFIED — adds BackgroundDaemonPolicy + sync.background_daemon key
│   ├── daemon.py                    # MODIFIED — ensure_sync_daemon_running() becomes intent-gated
│   └── events.py                    # AUDITED — daemon call sites updated to pass intent
│
├── dashboard/
│   ├── server.py                    # AUDITED — daemon auto-start call sites updated to pass intent
│   └── handlers/api.py              # AUDITED — daemon auto-start call sites updated to pass intent
│
└── cli/commands/
    ├── __init__.py                  # MINIMAL — keeps existing conditional import; switches to saas.rollout import
    └── tracker.py                   # MODIFIED — replaces _require_enabled() with HostedReadiness call per command

architecture/
└── ADR-0XX-saas-rollout-and-readiness.md   # NEW ADR (DIRECTIVE_003)

tests/
├── saas/                                            # NEW test package
│   ├── test_rollout.py                              # Unit tests for is_saas_sync_enabled across env states
│   ├── test_readiness_unit.py                       # Unit tests with stubbed prerequisite probes
│   └── test_readiness_integration.py                # Integration tests against real auth/config/binding fixtures
├── sync/
│   ├── test_daemon_intent_gate.py                   # NEW — intent + policy matrix
│   └── test_config_background_daemon.py             # NEW — config schema parsing for sync.background_daemon
├── agent/cli/commands/
│   ├── test_tracker.py                              # MODIFIED — parametrized rollout-on/off; assert per-prerequisite messages
│   ├── test_tracker_discover.py                     # MODIFIED — readiness-aware
│   └── test_tracker_status.py                       # MODIFIED — readiness-aware
└── conftest.py                                      # UNCHANGED autouse default; new tests opt out via monkeypatch
```

**Structure Decision**: Single Python project under `src/specify_cli/`. The mission introduces **one new shared package** `src/specify_cli/saas/` that owns rollout + readiness, plus a single new config field on the existing `SyncConfig`. The two duplicated `feature_flags.py` modules become re-export shims so existing imports keep working without forcing every call site to rename in this mission. The `dashboard/` and `sync/events.py` daemon callers are audited (not rewritten) — they only change to pass an explicit `intent=...` argument.

## Phase Plan

### Phase 0 — Research

`research.md` resolves the following deliberately-deferred decisions and records the rationale:

1. **Where the new shared package lives** (`src/specify_cli/saas/` vs hanging it off existing `tracker/` or `sync/`).
2. **Readiness state taxonomy** — exact enum members and which prerequisite each represents.
3. **Reachability probe semantics** — should the integration evaluator make a network call, or should reachability remain a separate `READY_PENDING_REACHABILITY` state that downstream commands opt into?
4. **`sync.background_daemon` location** — user-level (`~/.spec-kitty/config.toml`) vs project-level (`.kittify/config.yaml`), and how a project override could later layer over the user default.
5. **Intent expression** — explicit boolean parameter on `ensure_sync_daemon_running(intent_remote: bool)` vs a typed `DaemonIntent` enum vs a per-command decorator.
6. **Test fixture strategy** — how to express "rollout off" in pytest given the existing autouse fixture, and how to share auth/config/binding fixtures between unit (stubbed) and integration (real) layers.

All six items are tractable from current code; none require external research.

### Phase 1 — Design & Contracts

`data-model.md` defines:
- `RolloutGate` (function-shaped) — `is_saas_sync_enabled() -> bool`
- `ReadinessState` enum — `ROLLOUT_DISABLED | MISSING_AUTH | MISSING_HOST_CONFIG | HOST_UNREACHABLE | MISSING_MISSION_BINDING | READY`
- `ReadinessResult` dataclass — `state: ReadinessState`, `message: str`, `next_action: str | None`, `details: Mapping[str, str]`
- `BackgroundDaemonPolicy` enum — `AUTO | MANUAL`
- `DaemonIntent` enum — `LOCAL_ONLY | REMOTE_REQUIRED`

`contracts/` records the API surface as Markdown contract docs (no runtime schema generation needed for an internal CLI module):
- `saas_rollout.md` — public function signature, env-var contract, BC shim semantics
- `hosted_readiness.md` — evaluator API, ordering of checks, failure-message contract, mission-binding integration
- `background_daemon_policy.md` — config key shape, default, intent gate behavior, audited call-site list

`quickstart.md` walks operators through:
1. Customer machine (no env var) → verify hidden surface and zero network activity
2. Internal tester machine (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`) → verify visible surface and per-prerequisite errors
3. Internal tester with `sync.background_daemon=manual` → verify daemon does not auto-start

Agent context refresh runs `spec-kitty agent context update` (or equivalent) at the end of Phase 1 to surface the new `saas/` package in CLAUDE.md.

## Complexity Tracking

*No charter violations. This section is intentionally empty.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(none)_ | _(none)_ |

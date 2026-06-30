# Implementation Plan: Safe Sync Daemon Orphan Cleanup

**Branch**: `fix/sync-daemon-orphan-cleanup` | **Date**: 2026-06-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/spec.md` · Source issue [#2261](https://github.com/Priivacy-ai/spec-kitty/issues/2261)

## Summary

Sync daemons accumulate across upgrades (18 observed on `9401–9418`, versions `3.2.2`–`3.2.4`) because the startup reaper (`reap_orphan_daemons`, `sync/owner.py:707-789`) requires the orphan's **executable identity** to match the foreground — old-version daemons fail that leg and are `skipped_out_of_scope`. The fix makes the **daemon-root scope marker** the primary kill authority and demotes executable/version mismatch to **stale-version evidence** (FR-008), unifies both cleanup surfaces behind a single pure **classification engine** that emits a `DaemonIdentityRecord` + `cleanup_class` (`safe_auto` / `operator_required` / `never_touch`), exposes that classification through `auth doctor [--json]`, reports exact `swept`/`skipped`/`failed` from `--reset [--force]`, lets superseded daemons self-retire, and locks the sync↔dashboard boundary with a live-subprocess regression matrix. Identity, kill-escalation, and the test harness largely **already exist** and are reused; net-new is `classification.py`, a `daemon_family` tag, a structured `skip_reason`, a `--force` flag, an idle-retirement constant, an ADR, and two test modules.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console rendering), psutil (process inspection + signal escalation), stdlib `http.server` (loopback daemon control plane), importlib.metadata (version)
**Storage**: Filesystem state only — sync daemon state file `_daemon_root()/sync-daemon` (4-line url/port/token/pid, `daemon.py:270-304`), `owner.json` (`<sync_root>/daemon/owner.json`, `owner.py:86-148`), dashboard `.kittify/.dashboard`. No database/schema changes (the queue SQLite is untouched).
**Testing**: pytest; new live-subprocess integration suites reusing `_DaemonHarness` (real loopback ports + real PIDs, version-spoofed via `SPEC_KITTY_CLI_VERSION`); unit tests for the pure classifier; serial `-n0` for real-port files; `ruff` + `mypy --strict` zero-issue.
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows). POSIX + Windows daemon roots already handled; real-socket tests `skipif(sys.platform == "win32")` mirroring existing suites.
**Project Type**: single (Python CLI package, `src/specify_cli`)
**Performance Goals**: A full `[9400,9450)` scan completes in well under ~1s in practice — a 50 ms TCP connect-check gates the 500 ms health probe so only actual listeners are probed; cleanup escalation is bounded (~1 s terminate + ~1 s kill per stubborn PID).
**Constraints**: sync cleanup strictly within `[9400,9450)`; dashboard within `[9237,9337)`; **0** cross-family signals; never kill on port-presence alone; `/api/health` stays loopback-only/unauthenticated; `owner.json` is never kill authority; `ruff` + `mypy --strict` clean.
**Scale/Scope**: tens of daemons per host (18 observed); 6 implementation concerns; ~1 new runtime module + edits to `daemon.py`/`owner.py`/`orphan_sweep.py` + `auth.py`/`_auth_doctor.py`, 2 new test modules, 1 ADR, 1 docs update.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — still passing.*

| Charter item | Assessment | Status |
|--------------|------------|--------|
| **DIRECTIVE_001** Architectural Integrity | Sync and dashboard lifecycles stay separate; cleanup unified only **within** the sync family; `daemon_family` made explicit (C-001/C-002). | PASS |
| **DIRECTIVE_024** Locality of Change | Change confined to `sync/` (+ a display-only edit in `auth doctor`); no sprawl into unrelated modules; dashboard touched by tests only. | PASS |
| **DIRECTIVE_003** Decision Documentation | Identity-contract change recorded in a new ADR (DD-05, C-005); 3 Decision Moments captured. | PASS |
| **DIRECTIVE_010** Specification Fidelity | Plan maps 1:1 to FR/NFR/C; deviations would be documented. | PASS |
| **DIRECTIVE_037** Living Documentation Sync | Operator remediation runbook + quickstart updated alongside code. | PASS |
| **DIR-008** No secrets exposure | Control-plane token stays redacted on `/api/health` (`redact_token`); unchanged. | PASS |
| **DIR-005/006/007** Tests, mypy --strict, docstrings | New branches/helpers get focused tests; `classify_candidate` is pure + typed + documented. | PASS |
| Sonar: complexity ≤15, repeated-literal constants, real fixes not suppression | Classifier extracted as a pure decision function (testable); `skip_reason`/`cleanup_class` as enums/constants; idle timeout a named constant. | PASS |

No violations → **Complexity Tracking** section intentionally empty.

> **DIR-012 (implement-phase reminder)**: when implementation begins, assign issue #2261 to the Human-in-Charge before/with the first WP. Not actioned during planning.

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-daemon-orphan-cleanup-01KWC2A3/
├── plan.md              # this file
├── research.md          # Phase 0 — root cause, resolved decisions, premortem
├── data-model.md        # Phase 1 — entities, enums, decision table, state machine
├── contracts/           # Phase 1 — classification, auth-doctor-json, health-payload
├── quickstart.md        # Phase 1 — operator + developer walkthrough
├── decisions/           # 3 resolved Decision Moments (DM-*)
└── tasks.md             # Phase 2 — created by /spec-kitty.tasks (NOT here)
```

### Source Code (repository root)

```
src/specify_cli/
├── sync/
│   ├── classification.py   # NEW — DaemonIdentityRecord, CleanupClass, SkipReason, classify_candidate() (pure)
│   ├── daemon.py           # EDIT — add daemon_family to /api/health; surface singleton_scope_id; idle-retirement constant
│   ├── owner.py            # EDIT — demote executable-identity skip to stale evidence (FR-008); feed classifier; ReapResult→records
│   └── orphan_sweep.py     # EDIT — build identity records per listener; emit cleanup_class; swept/skipped/failed
├── dashboard/
│   ├── lifecycle.py        # UNCHANGED behavior — covered by boundary regression (IC-05)
│   └── server.py           # UNCHANGED — DaemonIntent.LOCAL_ONLY regression-locked (C-003)
└── cli/commands/
    ├── auth.py             # EDIT — add --force; wire classification + reset_result
    └── _auth_doctor.py     # EDIT — render cleanup_class/reason; print swept/skipped/failed

tests/sync/
├── test_daemon_orphan_classification.py   # NEW — classifier unit rows + live version matrix (3.2.2/3.2.3/3.2.4)
├── test_daemon_cleanup_boundary.py        # NEW — cross-family + boundary-port matrix across 4 entrypoints
├── test_orphan_sweep.py                   # REUSE — _DaemonHarness, _spawn_daemon, port helpers
├── test_daemon_self_retirement.py         # EXTEND — superseded + idle-constant retirement
└── test_daemon_owner_record.py            # REUSE — _build_record fabricator

docs/
├── adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md  # NEW ADR (C-005)
└── (operator remediation runbook update — auth doctor → auth doctor --reset [--force])
```

**Structure Decision**: Single-project layout. All runtime change lives in the existing `src/specify_cli/sync/` package (locality, DIRECTIVE_024); the only edit outside it is display/flag wiring in `cli/commands/auth.py` + `_auth_doctor.py`. The classifier is a **new pure module** so its decision table is unit-testable without subprocesses. The dashboard package is read-only here except for regression tests that prove the boundary.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are architectural areas, **not** work packages. `/spec-kitty.tasks` slices these into WPs (one IC may become several WPs, or small ICs may merge). No WP IDs or sequencing language here.

### IC-01 — Daemon identity & classification engine

- **Purpose**: A single pure classifier turns a probed listener into a `DaemonIdentityRecord` + `cleanup_class`, with the daemon-root scope marker as primary kill authority and version/executable mismatch demoted to evidence.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-008.
- **Affected surfaces**: `sync/classification.py` (new); `sync/owner.py`, `sync/daemon.py`, `sync/orphan_sweep.py` (feed/probe).
- **Sequencing/depends-on**: none (foundational).
- **Risks**: getting the `safe_auto` bar exactly right (D-01 — require live self-report); not regressing the conservative reaper's existing safety for genuinely cross-root daemons.

### IC-02 — `auth doctor` visibility & reset reporting

- **Purpose**: Surface the classification through `auth doctor [--json]` (read-only) and report exact `swept`/`skipped`/`failed` from `--reset`.
- **Relevant requirements**: FR-004, FR-005, FR-009.
- **Affected surfaces**: `cli/commands/auth.py`, `cli/commands/_auth_doctor.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: `schema_version` 1→2 back-compat; keeping `auth doctor` read-only without `--reset`; human + JSON parity.

### IC-03 — Safe cleanup, `--force` gating & self-retirement

- **Purpose**: Startup auto-cleans `safe_auto` only and spawns no extra daemon; `--reset` cleans `safe_auto` and guards `operator_required` behind `--force`/confirmation; superseded/idle daemons self-retire via a named constant.
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-009, FR-010, FR-011; decision D-02.
- **Affected surfaces**: `sync/orphan_sweep.py`, `sync/owner.py`, `sync/daemon.py`.
- **Sequencing/depends-on**: IC-01 (and IC-02 for the `--force` surface).
- **Risks**: never killing the recorded singleton; `--force` semantics in non-interactive `--json`; idle-constant default (DD-03).

### IC-04 — Live-subprocess regression harness (version matrix)

- **Purpose**: Prove the behavior with real listeners/PIDs across versions `3.2.2`/`3.2.3`/`3.2.4`, same-scope stale, pre-marker, cross-`$HOME`, wedged, and third-party cases.
- **Relevant requirements**: NFR-004, NFR-006; AS-1..AS-5.
- **Affected surfaces**: `tests/sync/test_daemon_orphan_classification.py` (new), reusing `_DaemonHarness` + `SPEC_KITTY_CLI_VERSION` spoofing (DD-04).
- **Sequencing/depends-on**: IC-01, IC-02, IC-03.
- **Risks**: port collisions (use isolated sub-range + `-n0`); macOS `net_connections` `AccessDenied` (use harness port→PID map); win32 skips.

### IC-05 — Dashboard boundary regression matrix

- **Purpose**: Prove sync cleanup never touches dashboard/third-party listeners and vice-versa, across all four entrypoints (startup reaper, auth-doctor sweep, broad `cleanup_orphan_sync_daemons`, dashboard `_cleanup_orphaned_dashboards_in_range`), including first/last/just-outside boundary ports; confirm `DaemonIntent.LOCAL_ONLY` unchanged.
- **Relevant requirements**: NFR-001, NFR-002, NFR-003; C-002, C-003; AS-6, AS-7.
- **Affected surfaces**: `tests/sync/test_daemon_cleanup_boundary.py` (new); `dashboard/*` exercised read-only.
- **Sequencing/depends-on**: IC-01, IC-03.
- **Risks**: ensuring every entrypoint is covered; boundary ports `9400/9449` and `9237/9336` plus just-outside `9399/9450/9236/9337`.

### IC-06 — Decision record, docs & #1071 reconfirmation

- **Purpose**: ADR for the identity-contract change; operator remediation docs; automated #1071 same-`$HOME` reconfirmation, then close or re-scope #1071.
- **Relevant requirements**: C-005, C-006; FR-012, SC-006; DIRECTIVE_003/037.
- **Affected surfaces**: `docs/adr/3.x/…`, operator runbook; a #1071 regression test in the live harness.
- **Sequencing/depends-on**: IC-01..IC-05 (reconfirmation needs the behavior in place).
- **Risks**: faithfully reproducing #1071's scenario; keeping the ADR aligned with the shipped contract.

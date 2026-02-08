# Parity Matrix: Status Engine (2.x vs 0.1x)

**Feature**: 034-feature-status-state-model-remediation
**Generated**: 2026-02-08
**Branch context**: 2.x (status engine developed here, backport targets main/0.1x)

## Overview

This document tracks the functional parity between the canonical status engine
on the 2.x branch and what will be available on the 0.1x line (main branch)
after backport. The status engine was developed entirely on 2.x and must be
cherry-picked or backported to main.

## Module Parity Matrix

| Module | 2.x Status | 0.1x Backport Status | Notes |
|--------|-----------|---------------------|-------|
| `models.py` | Complete | Ready for backport | No 2.x-only dependencies. Pure dataclasses + StrEnum. |
| `transitions.py` | Complete | Ready for backport | No external dependencies. Pure state machine logic. |
| `reducer.py` | Complete | Ready for backport | Uses only stdlib (json, os, datetime). Deterministic algorithm. |
| `store.py` | Complete | Ready for backport | Uses only stdlib (json, pathlib). JSONL append-only log. |
| `phase.py` | Complete | Ready for backport | Contains `is_01x_branch()` and `MAX_PHASE_01X` cap. Already branch-aware. |
| `legacy_bridge.py` | Complete | Ready for backport | Depends on `specify_cli.frontmatter.FrontmatterManager`. Verify import path on main. |
| `emit.py` | Complete | Ready for backport | SaaS fan-out uses `try/except ImportError` for `sync.events`. Graceful no-op on 0.1x. |
| `validate.py` | Complete | Ready for backport | No 2.x-only dependencies. Pure validation logic. |
| `doctor.py` | Complete | Ready for backport | No 2.x-only dependencies. Health check framework. |
| `reconcile.py` | Complete | Ready for backport | Uses subprocess for git operations. No 2.x-only deps. |
| `migrate.py` | Complete | Ready for backport | Depends on `specify_cli.frontmatter.read_frontmatter`. Verify import path on main. |
| `__init__.py` | Complete | Ready for backport | Public API surface. Exports all modules. |

## Dependency Analysis

### Dependencies Present on Both Branches

| Dependency | Used By | Available on 0.1x? |
|-----------|---------|-------------------|
| `ulid` (python-ulid) | `emit.py`, `reconcile.py`, `migrate.py` | Needs to be added to pyproject.toml on main |
| `ruamel.yaml` | `phase.py` (config reading) | Already present on main |
| `specify_cli.frontmatter` | `legacy_bridge.py`, `migrate.py` | Already present on main |
| `rich` | `reconcile.py` (report formatting) | Already present on main |

### Dependencies Only on 2.x (Guarded)

| Dependency | Used By | Guard Mechanism |
|-----------|---------|-----------------|
| `specify_cli.sync.events` | `emit.py` `_saas_fan_out()` | `try/except ImportError` -- becomes no-op on 0.1x |

## Feature Behavior Differences

### Phase Capping (0.1x-specific behavior)

On 0.1x branches, `phase.py` caps the maximum phase at `MAX_PHASE_01X = 2`.
Since valid phases are (0, 1, 2) and the cap is at 2, this effectively means
all phases are available on 0.1x. The cap exists as a safety mechanism for
future phases (3+) that may require 2.x infrastructure.

Branch detection logic in `is_01x_branch()`:
- `main` -> 0.1x (True)
- `release/*` -> 0.1x (True)
- `2.x`, `2.*` -> NOT 0.1x (False)
- `034-*` (feature branches) -> NOT 0.1x (False)
- Git error/timeout -> defaults to False (not 0.1x)

### SaaS Fan-Out (2.x-only feature)

The `emit.py` module's `_saas_fan_out()` function attempts to import
`specify_cli.sync.events.emit_wp_status_changed`. On 0.1x where `sync/`
does not exist, this import fails silently via `except ImportError: pass`.

**Behavior on 0.1x**: SaaS telemetry is a no-op. Canonical event log and
snapshot materialization are unaffected.

**Behavior on 2.x**: SaaS telemetry is emitted if `sync.events` is available.
Failures never block canonical persistence (`except Exception` catch).

### Legacy Bridge (parity on both)

The legacy bridge (`legacy_bridge.py`) updates frontmatter views from the
canonical snapshot. This works identically on both branches since it only
depends on `specify_cli.frontmatter.FrontmatterManager` which exists on main.

## Parity Verification Tests

Tests that verify cross-branch parity are located in:
- `tests/specify_cli/status/test_parity.py`

These tests verify:
1. **Reducer determinism**: Same input events produce identical output (excluding `materialized_at` timestamp)
2. **SaaS no-op on 0.1x**: `_saas_fan_out` silently skips when `sync.events` is not importable
3. **Phase cap enforcement**: `resolve_phase()` caps at `MAX_PHASE_01X` when `is_01x_branch()` returns True
4. **No hard imports from sync**: All status modules import successfully without `sync/` package
5. **Event serialization parity**: JSON output from `materialize_to_json()` is byte-identical across runs

## Backport Checklist

See `backport-notes.md` in this directory for the full backport procedure.

### Pre-Backport Verification

- [ ] All status tests pass on 2.x: `pytest tests/specify_cli/status/ -x -q`
- [ ] Parity tests pass: `pytest tests/specify_cli/status/test_parity.py -x -q`
- [ ] No hard imports from `sync/` in any status module
- [ ] `ulid` dependency added to pyproject.toml on main branch
- [ ] `FrontmatterManager` import path matches main branch

### Post-Backport Verification

- [ ] All status tests pass on main: `pytest tests/specify_cli/status/ -x -q`
- [ ] `is_01x_branch()` returns True on main
- [ ] Phase capping works on main
- [ ] SaaS fan-out is no-op on main (no `sync/` package)
- [ ] Reducer produces identical output on both branches for same events

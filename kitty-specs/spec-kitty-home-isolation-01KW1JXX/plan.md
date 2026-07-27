# Implementation Plan: SPEC_KITTY_HOME State Isolation

**Branch**: `fix/spec-kitty-home-isolation` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/spec-kitty-home-isolation-01KW1JXX/spec.md`
**Source**: [GitHub issue #2171](https://github.com/Priivacy-ai/spec-kitty/issues/2171)

## Summary

`SPEC_KITTY_HOME` must become the single authoritative selector for **all** global
sync/auth/tracker/daemon state, not just runtime/Mission assets. The root cause is that
`specify_cli.paths.get_runtime_root()` — which already exists and already exposes a
`RuntimeRoot(base, …)` with derived `.auth_dir/.sync_dir/.daemon_dir/.tracker_dir`
properties — **does not read `SPEC_KITTY_HOME`**, and ~12 call sites independently
hand-roll `Path.home() / ".spec-kitty"`.

**Technical approach:** Fix the keystone first — make `get_runtime_root()` honor
`SPEC_KITTY_HOME` on all platforms (empty string = unset). Then reroute every global-state
call site through `get_runtime_root().base`, **preserving each site's existing child
suffix** so POSIX stays byte-identical when the variable is unset. On Windows, normalize
the surfaces that currently leak to `~/.spec-kitty` (sync config, queue, clock, tracker DB)
onto the platformdirs base used by the already-delegating surfaces (decision
`DM-01KW1KDHVGWZ0QERDMV1CRJ15S`). Add an architectural guard test so no future code can
re-scatter the literal, update the in-repo skill doc, and add a CHANGELOG entry.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, platformdirs, ruamel.yaml (all existing — **no new dependencies**)
**Storage**: Local-filesystem global state under the runtime state root — `config.toml`, SQLite queue + tracker DBs, `clock.json`, encrypted auth session store, daemon control/lock files
**Testing**: pytest (focused unit + CLI integration), `mypy --strict`, `ruff`; parallel run `-n auto --dist loadfile`, daemon/real-port tests serial `-n0`
**Target Platform**: Linux, macOS, Windows 10+
**Project Type**: single (CLI library — `src/specify_cli/`)
**Performance Goals**: No regression; path resolution is O(1) and pure (no I/O)
**Constraints**: Pure resolution (0 directories created as a side effect); POSIX byte-identical when env unset (NFR-001); Windows normalized to platformdirs base when unset (decision DM-01KW1KDHVGWZ0QERDMV1CRJ15S); no auto-migration of existing data (C-001); `mypy --strict` + `ruff` zero issues; ≥90% new-code coverage; complexity ≤15 per function
**Scale/Scope**: 1 keystone function + ~12 call sites across 10 modules + 1 architectural guard test + skill doc + CHANGELOG

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Relevant gates for this fix:

| Charter item | Status | Notes |
|--------------|--------|-------|
| **DIRECTIVE_001** Architectural Integrity | ✅ Pass | Fix *increases* integrity: collapses scattered path logic into one authoritative root. |
| **DIRECTIVE_003** Decision Documentation | ✅ Pass | Windows-normalization trade-off captured as decision `DM-01KW1KDHVGWZ0QERDMV1CRJ15S` + research.md. |
| **DIRECTIVE_010** Specification Fidelity | ✅ Pass | Every FR maps to an IC; acceptance criteria → tests. |
| **DIRECTIVE_024** Locality of Change | ✅ Pass | Surgical: one keystone + per-site reroute preserving suffixes; no broad rewrite. |
| **DIRECTIVE_037** Living Documentation Sync | ✅ Pass | IC-07 updates the in-repo SKILL.md + CHANGELOG alongside the code. |
| **DIR-006** mypy --strict | ✅ Pass | No type relaxation; new code fully annotated. |
| **DIR-010/011** ASCII-safe identifiers | ➖ N/A | No identifier/slug sanitization touched. |
| **DIR-008** No security issues | ✅ Pass | NFR-005: 0 credentials written/logged outside resolved root. |

No charter violations → Complexity Tracking table omitted.

## Project Structure

### Documentation (this mission)

```
kitty-specs/spec-kitty-home-isolation-01KW1JXX/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions + rationale
├── data-model.md        # Phase 1 — RuntimeRoot + state-surface map
├── quickstart.md        # Phase 1 — manual verification recipe
├── contracts/           # Phase 1 — path-resolution + env-var contracts
│   ├── runtime-state-root.md
│   └── state-surface-map.md
└── tasks.md             # Phase 2 — created by /spec-kitty.tasks (NOT here)
```

### Source Code (repository root)

```
src/specify_cli/
├── paths/
│   ├── __init__.py            # re-exports get_runtime_root, RuntimeRoot
│   └── windows_paths.py       # ★ KEYSTONE: get_runtime_root() + RuntimeRoot dataclass
├── sync/
│   ├── config.py              # SyncConfig.__init__ (config_dir/config_file)
│   ├── queue.py               # _spec_kitty_dir() → creds/auth/legacy+scoped queue/active scope
│   ├── daemon.py              # _sync_root(), _daemon_root(), SPEC_KITTY_DIR constant
│   └── clock.py               # LamportClock default + load()
├── auth/
│   ├── secure_storage/
│   │   ├── file_fallback.py   # default_store_dir() (POSIX auth)
│   │   └── windows_storage.py # WindowsFileStorage default (Windows auth)
│   └── token_manager.py       # _refresh_lock_path()
├── tracker/
│   ├── credentials.py         # _tracker_root()
│   └── store.py               # _spec_kitty_dir(), _trackers_dir()
└── state/
    ├── doctor.py              # global_sync root + per-surface checks
    └── contract.py            # StateRoot.GLOBAL_SYNC + STATE_SURFACES registry

tests/
├── kernel/test_paths.py, test_paths_unified_windows_root.py
├── paths/ (CLI + unit path tests — add SPEC_KITTY_HOME precedence cases here)
├── sync/, auth/, tracker/ (regression for each rerouted surface)
└── audit/test_no_legacy_path_literals.py        # ★ architectural guard (extend)
    architectural/test_real_home_isolation_guard.py
```

**Structure Decision**: Single-project CLI library. No new modules; the keystone lives in
the existing `src/specify_cli/paths/windows_paths.py`. Each affected module is edited
in-place to delegate to `get_runtime_root().base`. A regression guard is added/extended in
`tests/audit/test_no_legacy_path_literals.py`.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into
> executable WPs.

### IC-01 — Authoritative runtime state root honors SPEC_KITTY_HOME

- **Purpose**: Make `get_runtime_root()` read `SPEC_KITTY_HOME` (non-empty) and use it as
  `base` on all platforms; preserve current defaults when unset (POSIX `~/.spec-kitty`,
  Windows platformdirs). This is the keystone every other concern depends on.
- **Relevant requirements**: FR-011, FR-012, NFR-002 (pure resolution), NFR-003 (Windows precedence)
- **Affected surfaces**: `src/specify_cli/paths/windows_paths.py` (`get_runtime_root`, possibly `RuntimeRoot`)
- **Sequencing/depends-on**: none (foundation)
- **Risks**: Must use the same empty-string-is-falsy idiom as `get_kittify_home`; must not create directories; must keep `RuntimeRoot` frozen/pure.

### IC-02 — Sync state rerouting

- **Purpose**: Route sync config, event queues (legacy + scoped), active queue scope,
  daemon state/log/lock, and Lamport clock through the authoritative root, preserving each
  POSIX suffix. Convert the import-time `SPEC_KITTY_DIR` constant in `daemon.py` to a lazy
  function so the env var (and test monkeypatching) takes effect.
- **Relevant requirements**: FR-001, FR-004, FR-005, FR-006, FR-007, NFR-001
- **Affected surfaces**: `sync/config.py`, `sync/queue.py`, `sync/daemon.py`, `sync/clock.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: POSIX flat layout must be preserved (daemon root = `base`, NOT `base/daemon`); `_sync_root` POSIX already = `base/"sync"` (== `sync_dir`); the module-level constant is a known import-time-evaluation trap.

### IC-03 — Auth state rerouting

- **Purpose**: Route the encrypted auth session store (POSIX file fallback + Windows
  storage) and the token refresh lock through the authoritative root.
- **Relevant requirements**: FR-002, FR-003, NFR-005
- **Affected surfaces**: `auth/secure_storage/file_fallback.py`, `auth/secure_storage/windows_storage.py`, `auth/token_manager.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: `windows_storage.py` currently hardcodes `Path.home()/.spec-kitty/auth` — normalizing it to `auth_dir` is part of the Windows-normalization decision; verify no Windows test pins the old path.

### IC-04 — Tracker state rerouting

- **Purpose**: Route tracker credentials and tracker DB store through the authoritative
  root (single-root decision — C-003 / FR-008), preserving the POSIX flat suffixes
  (`base/credentials`, `base/trackers`).
- **Relevant requirements**: FR-008, C-003
- **Affected surfaces**: `tracker/credentials.py`, `tracker/store.py`
- **Sequencing/depends-on**: IC-01
- **Risks**: POSIX tracker creds root = `base` (flat) ≠ `RuntimeRoot.tracker_dir` (`base/tracker`); must keep the flat POSIX suffix to satisfy NFR-001.

### IC-05 — State reporting consistency (doctor + contract)

- **Purpose**: Make `state doctor` resolve and report the same root the runtime uses, and
  ensure `StateRoot.GLOBAL_SYNC` resolution reflects the authoritative root rather than a
  hardcoded `~/.spec-kitty`.
- **Relevant requirements**: FR-009, FR-010
- **Affected surfaces**: `state/doctor.py` (lines ~141, ~253), `state/contract.py` (resolution of GLOBAL_SYNC surfaces)
- **Sequencing/depends-on**: IC-01
- **Risks**: `contract.py` STATE_SURFACES are declarative patterns; the actual resolution in `doctor.py` is what must change — keep the surface registry as the single source of relative patterns.

### IC-06 — Regression guard + architectural enforcement

- **Purpose**: Prevent recurrence. Add/extend an architectural test asserting no
  global-state module hand-rolls `Path.home() / ".spec-kitty"`, plus the CLI integration
  test (distinct HOME + SPEC_KITTY_HOME → all state under SPEC_KITTY_HOME, default home
  clean) and focused per-surface default-path unit tests under both env conditions.
- **Relevant requirements**: FR-010, NFR-001, NFR-003, NFR-004, SC-001..SC-004
- **Affected surfaces**: `tests/audit/test_no_legacy_path_literals.py`, `tests/paths/…`, plus per-surface tests in `tests/sync|auth|tracker|kernel`
- **Sequencing/depends-on**: IC-01..IC-05 (guard asserts their completion)
- **Risks**: The guard must allow the keystone + the two asset-home modules (`.kittify`) and migration/fallback code; scope the allowlist precisely to avoid false positives.

### IC-07 — Documentation + changelog sync

- **Purpose**: Update the in-repo skill doc to describe true isolation with a verification
  command, and record the Windows-normalization behavior change in CHANGELOG.
- **Relevant requirements**: FR-013, DIRECTIVE_037, DIR-009
- **Affected surfaces**: `src/doctrine/skills/spk-team-upsun-cli-sync/SKILL.md`, `CHANGELOG.md`
- **Sequencing/depends-on**: IC-01..IC-05 (document the true behavior once code is correct)
- **Risks**: Terminology canon — run `tests/architectural/test_no_legacy_terminology.py` after prose edits; sibling `spec-kitty-saas` runbooks are explicitly out of scope (C-002).

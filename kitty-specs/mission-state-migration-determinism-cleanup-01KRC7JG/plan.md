# Implementation Plan: Mission-State Migration Determinism Cleanup

**Branch**: `main` (mission lives in `kitty-specs/mission-state-migration-determinism-cleanup-01KRC7JG/`)
**Date**: 2026-05-11
**Spec**: [spec.md](spec.md)

## Summary

Finish the public mission-state migration hardening that started with `migration/mission_state.py`. The new
mission_state path is already deterministic. The legacy `migration/rebuild_state.py` (reached from the WP13
runner and the lifecycle-normalization upgrade) still mints random ULIDs and stamps `datetime.now(UTC)` into
synthetic events, so two migration runs against the same input produce diverging files. The repair manifest
itself is missing fields that a reviewer needs to explain a migration commit: CLI version, command args,
generated deterministic IDs, and the file-classification policy. We also need a hard guarantee that no secret
can ride into the manifest via `command_args`. This mission delivers all three: deterministic rebuild,
expanded manifest, and a scrub helper with explicit coverage.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: stdlib only for the new helpers (`hashlib`, `importlib.metadata`, `warnings`, `re`,
`sys`); existing `packaging.version` already imported by `mission_state.py`.
**Storage**: Filesystem — `.kittify/migrations/mission-state/<run_id>.json` manifests and
`kitty-specs/<mission>/status.events.jsonl` event logs.
**Testing**: `pytest` (existing). New tests under `tests/specify_cli/migration/` (legacy path) and
`tests/migration/` (canonical path).
**Target Platform**: Same as spec-kitty — CPython 3.11+ on macOS/Linux.
**Project Type**: Single project (CLI library + tests).
**Performance Goals**: Determinism, not throughput. The rebuild path was already O(events) and stays that way.
**Constraints**: No new top-level dependency; no breaking change to existing manifest keys; deprecation
warning on legacy path must not break callers that filter warnings.
**Scale/Scope**: Three modules touched (`rebuild_state.py`, `mission_state.py`, the package `__init__` is
unchanged); two test modules grow; one helper added.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This mission is pure code hygiene — no new user-facing CLI surface, no new dependencies, no schema break.
Spec-kitty's project charter prioritizes deterministic, reviewable migrations; this work is squarely on that
line. No charter gate violations.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-state-migration-determinism-cleanup-01KRC7JG/
├── spec.md              # functional requirements
├── plan.md              # this file
├── tasks.md             # work-package outline (next phase)
└── tasks/               # per-WP markdown files
```

### Source Code (repository root)

```
src/specify_cli/migration/
├── mission_state.py       # canonical path — manifest expansion + scrubber live here
├── rebuild_state.py       # legacy path — deterministic IDs/timestamps + DeprecationWarning
└── __init__.py            # re-exports stay as-is

tests/
├── specify_cli/migration/
│   └── test_rebuild_state.py        # legacy-path determinism tests grow here
└── migration/
    └── test_mission_state_repair.py # manifest field + scrubber tests grow here
```

**Structure Decision**: Single Python project. We extend two existing source files and two existing test
files. No new packages.

## Phase 0 / Phase 1 / Phase 2 outline

- **Phase 0 (research):** Read `rebuild_state.py` end-to-end (already done while drafting spec); confirm two
  nondeterminism sources (ULID factory + `datetime.now`). Confirm callers: `runner.py:420`,
  `normalize_mission_lifecycle.py:20`, `__init__.py:33`. Confirm `mission_state.py`'s manifest writer is
  `RepairReport.to_dict`/`to_json` and that `repair_repo` is the single entry point.
- **Phase 1 (design):**
  - Legacy determinism: replace `_generate_ulid()` with `_deterministic_id(*parts)` that hashes the inputs
    via `hashlib.sha256` and renders the same Crockford alphabet `mission_state.deterministic_ulid` uses.
    Replace `datetime.now(UTC).isoformat()` with a fixed sentinel (`_MIGRATION_EPOCH`); keep the offset
    machinery so synthetic chains stay ordered.
  - Manifest expansion: extend `RepairReport` with `cli_version: str`, `command_args: list[str]`,
    `generated_ids: list[str]`, `policy: dict[str, list[str]]`. Populate them inside `repair_repo` before
    calling `RepairReport(...)`. Collect `generated_ids` by threading a sink through `_repair_mission` /
    `deterministic_ulid` callsites.
  - Scrubber: new module-private `_scrub_secret_args(argv: Sequence[str]) -> list[str]`. Regex set defined
    once at module load; helper iterates argv, redacting either whole-string values that match a token
    pattern or paired `--flag value` / `--flag=value` shapes for known secret flags.
- **Phase 2 (tasks):** see `tasks.md`. Three WPs as defined in the spec.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified.*

No violations. The cleanup reduces complexity (removes hidden nondeterminism, removes hidden secret-leak
risk) without introducing new abstractions.

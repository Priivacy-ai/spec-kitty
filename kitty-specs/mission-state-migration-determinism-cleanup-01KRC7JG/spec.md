# Mission-State Migration Determinism Cleanup

**Mission ID:** 01KRC7JG0A5AAJWES96G8YRNAZ
**Slug:** mission-state-migration-determinism-cleanup-01KRC7JG
**Priority:** P1
**Closes:** Priivacy-ai/spec-kitty#926, Priivacy-ai/spec-kitty#930

## Why

The mission-state audit, fix, and TeamSpace dry-run paths in `migration/mission_state.py`
are already deterministic and well-tested. Two related public migration surfaces remain
imperfect:

1. **`migration/rebuild_state.py`** is a legacy path that still mints fresh ULIDs and uses
   `datetime.now(UTC)` at call time. It is reachable from `migration/runner.py` (the WP13
   atomic runner) and `migration/normalize_mission_lifecycle.py`, both of which can be
   invoked as part of public upgrade chains (`spec-kitty migrate run`, the
   `m_3_2_0a4_normalize_mission_lifecycle` upgrade migration, the package `__init__` API).
   Two runs of the same migration against the same legacy state produce different
   `event_id` values and slightly different `at` timestamps — so a migration commit cannot
   be reproduced or audited byte-for-byte from the legacy entry points.

2. **The repair manifest** written by `repair_repo()` (`mission_state.py`) is missing
   fields that GitHub issue #930 explicitly asks for: the CLI version that produced the
   manifest, the command-line invocation, the deterministic IDs minted during the run,
   and the classification policy (which files were tracked, ignored, or treated as
   optional). Without these, a reviewer cannot fully explain a migration commit from the
   manifest alone.

3. **Secret-scrub guarantee.** The manifest now grows to include `command_args`. We must
   prove no secrets (bearer tokens, `Authorization` headers, JWT-looking strings,
   `--token <value>` argv patterns, `GITHUB_TOKEN`/`SPEC_KITTY_TOKEN`-style env values)
   can ride along.

## What

Three concrete deliverables:

### D1: Deterministic legacy rebuild path

Make `migration/rebuild_state.py` produce byte-identical output for the same inputs:

- Replace the random ULID factory with a deterministic ID minted from a stable seed
  (mission slug + WP code + from_lane + to_lane + "synthetic-index").
- Replace `datetime.now(UTC)` with an injected/deterministic timestamp source (either
  a `migration_timestamp` parameter on `rebuild_event_log()`, or — for synthetic events —
  a fixed sentinel timestamp such as `1970-01-01T00:00:00+00:00` plus a per-WP offset).
- Emit a `DeprecationWarning` at module entry pointing users at the canonical path
  (`specify_cli.migration.mission_state.repair_repo`).
- All callers (`runner.py`, `normalize_mission_lifecycle.py`, the package `__init__`
  re-exports) keep working.

### D2: Expanded repair manifest

Extend `RepairReport.to_dict()` so the manifest serialized by `repair_repo()` always
contains:

- `cli_version` — string, from `importlib.metadata.version("spec-kitty-cli")` with a
  graceful `"unknown"` fallback.
- `command_args` — list of strings, scrubbed copy of `sys.argv[1:]`; falls back to
  `[]` when invoked programmatically.
- `generated_ids` — sorted list of every deterministic ID minted during the run
  (currently the `run_id` and any per-mission deterministic ULIDs reachable from
  `mission_state.py`).
- `policy` — object with three sorted string arrays: `tracked` (mission files the
  repair walks and mutates), `ignored` (paths skipped by design, e.g. `__pycache__`,
  `.git`, `.worktrees`), `optional` (artifacts repaired only when present, e.g.
  `status.json`).

Existing fields stay; we add to the manifest, we do not break it.

### D3: Secret-scrub guarantee

Add a `_scrub_secret_args()` helper used by D2's `command_args`. It must redact:

- Long-form CLI flags whose value can be sensitive: `--token`, `--auth`,
  `--password`, `--secret`, `--api-key`, `--bearer` (in either `--flag VALUE` or
  `--flag=VALUE` form).
- Standalone bearer tokens, `Authorization: ...` headers, and JWT-looking strings
  (three base64url segments separated by dots, each ≥ 16 chars).
- GitHub-style `gh[pousr]_*` tokens of length ≥ 36.
- Slack/Bearer-style `xox[bpars]-...` tokens.

Scrubbed values are replaced with the literal string `"<redacted>"`. The helper has
its own unit tests against known patterns; we also verify the integrated manifest is
clean given a hostile `sys.argv`.

## How we know we're done

- `pytest tests/specify_cli/migration/test_rebuild_state.py` passes, and a new
  determinism test (run the rebuild twice against an immutable fixture, assert
  byte-identical `status.events.jsonl`) passes.
- `pytest tests/migration/test_mission_state_repair.py` still passes.
- New manifest-field tests assert all four new keys are present and populated.
- New scrub-coverage tests cover at least: `--token foo`, `--token=foo`,
  `--api-key bar`, `Authorization: Bearer xyz`, `ghp_AAAA…`, a JWT-shaped string.
- GitHub issues #926 and #930 can be closed with reference to this mission's PR.

## Scope guard

- Removing `rebuild_state.py` outright is out of scope for this mission; we deprecate
  + harden in place.
- New top-level CLI surfaces are out of scope; existing entry points (`doctor
  mission-state --fix`, the migration runner) just get the better manifest.
- Existing manifest field names and types are not changed.

## Functional Requirements

| ID    | Description |
|-------|-------------|
| FR-001 | `migration/rebuild_state.py` must produce byte-identical `status.events.jsonl` output for two consecutive runs against the same immutable input fixture, including all synthetic `event_id` values and `at` timestamps. |
| FR-002 | `migration/rebuild_state.py` must emit a `DeprecationWarning` at import time pointing users at `specify_cli.migration.mission_state.repair_repo` as the canonical, non-legacy entry point. |
| FR-003 | `migration/rebuild_state.py` must remain importable and callable from existing internal callers (`migration/runner.py`, `migration/normalize_mission_lifecycle.py`, `migration/__init__.py` re-exports) with no behavior change beyond determinism and the deprecation warning. |
| FR-004 | The repair manifest produced by `mission_state.repair_repo()` must include a top-level string `cli_version`, sourced from `importlib.metadata.version("spec-kitty-cli")` with a `"unknown"` fallback when the package metadata is missing. |
| FR-005 | The repair manifest must include a top-level list `command_args` containing the scrubbed copy of `sys.argv[1:]` (or `[]` when invoked programmatically with no argv). |
| FR-006 | The repair manifest must include a top-level sorted-list `generated_ids` containing every deterministic identifier minted during the repair run (at minimum the `run_id` and any per-mission deterministic ULIDs reachable from `mission_state.deterministic_ulid`). |
| FR-007 | The repair manifest must include a top-level object `policy` with three sorted string arrays: `tracked`, `ignored`, and `optional`, describing the file-classification policy applied by the repair. |
| FR-008 | A new `_scrub_secret_args()` helper must redact sensitive flag values, bearer tokens, `Authorization:` headers, JWT-looking strings, GitHub-style `gh[pousr]_` tokens of length ≥ 36, and Slack-style `xox[bpars]-` tokens, replacing each redacted span with the literal string `"<redacted>"`. |
| FR-009 | The expanded manifest must remain valid JSON, sort its top-level keys, and preserve all pre-existing keys (`schema_version`, `run_id`, `repo_head`, `target_missions`, `manifest_path`, `summary`, `missions`) without renaming or type changes. |
| FR-010 | Migration determinism and secret-scrub coverage must be enforced by unit tests under `tests/specify_cli/migration/` and `tests/migration/` so future regressions fail CI. |


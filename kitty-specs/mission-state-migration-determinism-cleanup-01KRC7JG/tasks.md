# Tasks: Mission-State Migration Determinism Cleanup

**Mission**: mission-state-migration-determinism-cleanup-01KRC7JG
**Branch**: main → main
**Generated**: 2026-05-11T19:20:00Z

---

## Subtask Index

| ID   | Description                                                                                                 | WP   | Parallel |
|------|-------------------------------------------------------------------------------------------------------------|------|----------|
| T001 | Add deterministic ID helper to `migration/rebuild_state.py` (sha256 seed -> 26-char Crockford ULID).         | WP01 | [D]      |
| T002 | Replace `_generate_ulid()` callsites in `rebuild_state.py` with the seeded helper.                           | WP01 | [D]      |
| T003 | Replace `datetime.now(UTC)` synthetic timestamp with a fixed `_MIGRATION_EPOCH` + per-WP/per-step offset.    | WP01 | [D]      |
| T004 | Emit `warnings.warn(..., DeprecationWarning, stacklevel=2)` at module entry pointing at `mission_state.repair_repo`. | WP01 | [D] |
| T005 | Add determinism test (`tests/specify_cli/migration/test_rebuild_state.py`): two runs against the same fixture produce byte-identical events. | WP01 | [D] |
| T006 | Add scrub helper `_scrub_secret_args()` in `migration/mission_state.py` (flag-value + token regex set + `<redacted>` placeholder). | WP02 | [D] |
| T007 | Add focused scrub-coverage tests in `tests/migration/test_mission_state_repair.py` covering `--token`, `--token=`, `--api-key`, `Authorization:` header, GitHub `ghp_…`, JWT shape, Slack `xox…`. | WP02 | [D] |
| T008 | Extend `RepairReport` dataclass with `cli_version`, `command_args`, `generated_ids`, `policy`; preserve all existing keys. | WP02 | [D] |
| T009 | Populate the four new fields inside `repair_repo()` (use `importlib.metadata.version("spec-kitty-cli")` with `"unknown"` fallback, scrubbed `sys.argv[1:]`, sorted ids, sorted policy lists). | WP02 | [D] |
| T010 | Thread a `generated_ids` sink through `_repair_mission` / `deterministic_ulid` callsites so every minted id lands in the manifest. | WP02 | [D] |
| T011 | Define the file-classification policy constants (`tracked` / `ignored` / `optional`) near `MANIFEST_ROOT` and reuse them in `repair_repo`. | WP02 | [D] |
| T012 | Add manifest-field tests in `tests/migration/test_mission_state_repair.py` asserting all four new keys exist, have the right types, and round-trip through `to_json`/JSON parse. | WP02 | [D] |
| T013 | Run `pytest tests/specify_cli/migration/test_rebuild_state.py tests/migration/test_mission_state_repair.py` and verify everything still passes. | WP02 | [D] |

## Work Packages

## WP01 — Deterministic Legacy Rebuild Path

**Depends on**: none

Tasks T001..T005. Make `migration/rebuild_state.py` deterministic and emit a
`DeprecationWarning` on import. Owns `src/specify_cli/migration/rebuild_state.py` and
`tests/specify_cli/migration/test_rebuild_state.py`.

## WP02 — Manifest Expansion and Secret-Scrub

**Depends on**: none (parallel-safe with WP01; touches a disjoint file set)

Tasks T006..T013. Add `_scrub_secret_args()`, extend `RepairReport` with `cli_version`,
`command_args`, `generated_ids`, `policy`, populate them in `repair_repo()`, and ship the
full test coverage. Owns `src/specify_cli/migration/mission_state.py` and
`tests/migration/test_mission_state_repair.py`.

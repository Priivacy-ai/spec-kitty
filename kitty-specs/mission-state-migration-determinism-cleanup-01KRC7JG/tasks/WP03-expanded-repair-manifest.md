---
work_package_id: WP03
title: Expanded Repair Manifest
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main; completed changes must merge back into main.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Manifest
assignee: ""
agent: ""
history:
- timestamp: "2026-05-11T19:20:00Z"
  agent: system
  action: Prompt generated for Mission 8 (migration determinism cleanup)
---

# Work Package Prompt: WP03 — Expanded Repair Manifest

## Why this WP exists

GitHub issue #930 asks the repair manifest to be sufficient for a reviewer to explain a
migration commit on its own. Today's manifest leaks the structured per-mission audit
evidence but is missing: which CLI version produced it, what command was invoked, which
deterministic IDs were minted, and which files the repair walked vs ignored vs treated as
optional. This WP adds those four fields without breaking the existing manifest shape, and
uses the WP02 scrubber to keep `command_args` secret-free.

## Files touched

- `src/specify_cli/migration/mission_state.py`
- `tests/migration/test_mission_state_repair.py`

## Tasks

- **T008** — Extend the `RepairReport` dataclass with four new fields:
  - `cli_version: str` (default `"unknown"`)
  - `command_args: list[str] = field(default_factory=list)`
  - `generated_ids: list[str] = field(default_factory=list)`
  - `policy: dict[str, list[str]] = field(default_factory=dict)`

  Update `RepairReport.to_dict()` to include these keys in the returned dict, preserving the
  existing `schema_version`, `run_id`, `repo_head`, `target_missions`, `manifest_path`,
  `summary`, and `missions` keys. Continue to sort top-level keys via
  `json.dumps(..., sort_keys=True)`.

- **T009** — In `repair_repo()`, just before constructing `RepairReport(...)`:
  - Resolve `cli_version` via
    `importlib.metadata.version("spec-kitty-cli")` wrapped in a `try/except
    PackageNotFoundError` returning `"unknown"`.
  - Resolve `command_args = _scrub_secret_args(sys.argv[1:])` using the helper added in WP02.
    Programmatic callers will typically pass through `[]`.
  - Build `generated_ids` from a sorted, de-duplicated list of every deterministic identifier
    produced during the run (see T010).
  - Build `policy` from the constants defined in T011.

- **T010** — Thread a `generated_ids: list[str]` sink through `_repair_mission` and any
  callsite of `deterministic_ulid` reachable from `repair_repo`. At minimum, `run_id` and any
  per-mission ULIDs minted during canonicalization must be appended. Keep the helper boring:
  a plain mutable list passed by reference, sorted+deduped at the top level before going into
  the manifest.

- **T011** — Define three module-level constants near `MANIFEST_ROOT`:
  - `_POLICY_TRACKED = ("kitty-specs/*/meta.json", "kitty-specs/*/status.events.jsonl",
    "kitty-specs/*/status.json", ".kittify/migrations/mission-state/*.json")`
  - `_POLICY_OPTIONAL = ("kitty-specs/*/status.json",)`
  - `_POLICY_IGNORED = (".git/", ".worktrees/", "__pycache__/", "*.pyc")`

  Build `policy = {"tracked": sorted(_POLICY_TRACKED), "optional":
  sorted(_POLICY_OPTIONAL), "ignored": sorted(_POLICY_IGNORED)}` inside `repair_repo`.

- **T012** — Add tests in `tests/migration/test_mission_state_repair.py` that:
  - Run `repair_repo` against a minimal fixture and parse the manifest JSON.
  - Assert all four new keys are present, types match, `policy` has all three sub-keys with
    sorted lists, `generated_ids` includes the `run_id`.
  - Assert no `command_args` entry leaks a secret (round-trip through scrubber).
  - Assert all pre-existing manifest keys are still present and unchanged in shape.

- **T013** — Run the full migration test suite locally:
  `pytest tests/specify_cli/migration/test_rebuild_state.py tests/migration/test_mission_state_repair.py`
  and confirm green.

## Acceptance

- `RepairReport` carries the four new fields.
- The manifest JSON contains them, sort-stable, JSON-valid.
- All existing manifest tests still pass.
- New manifest-field tests pass.
- Combined test run is green.

## Boundaries (do not touch)

- Do not change existing manifest field names or types.
- Do not modify `rebuild_state.py` (that's WP01).
- Do not re-implement the scrubber (that's WP02).

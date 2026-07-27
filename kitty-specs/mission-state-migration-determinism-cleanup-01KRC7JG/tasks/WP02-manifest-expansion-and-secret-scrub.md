---
work_package_id: WP02
title: Manifest Expansion and Secret-Scrub
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Manifest
assignee: ''
agent: ''
history:
- timestamp: '2026-05-11T19:20:00Z'
  agent: system
  action: Prompt generated for Mission 8 (migration determinism cleanup)
authoritative_surface: src/specify_cli/migration/mission_state.py
execution_mode: code_change
owned_files:
- src/specify_cli/migration/mission_state.py
- tests/migration/test_mission_state_repair.py
tags: []
---

# Work Package Prompt: WP02 — Manifest Expansion and Secret-Scrub

## Why this WP exists

GitHub issue #930 asks the repair manifest to be sufficient for a reviewer to explain a
migration commit on its own. Today's manifest leaks the structured per-mission audit
evidence but is missing: which CLI version produced it, what command was invoked, which
deterministic IDs were minted, and which files the repair walked vs ignored vs treated as
optional. The new `command_args` field must also be provably secret-free, so this WP
ships the scrub helper alongside the manifest expansion. Both live in `mission_state.py`
and both are tested via `test_mission_state_repair.py`, so they ship together to keep
ownership clean.

## Files touched

- `src/specify_cli/migration/mission_state.py`
- `tests/migration/test_mission_state_repair.py`

## Tasks

### Scrubber

- **T006** — Add a module-private `_scrub_secret_args(argv: Sequence[str]) -> list[str]` to
  `mission_state.py`. Behaviour:
  - For known sensitive long-form flags (`--token`, `--auth`, `--password`, `--secret`,
    `--api-key`, `--bearer`), accept either `--flag VALUE` (two argv slots) or `--flag=VALUE`
    (one argv slot) and replace the *value* portion with the literal `"<redacted>"`. The
    `--flag` name itself is preserved.
  - For standalone argv items, if the item matches any of these patterns, replace the whole
    item with `"<redacted>"`:
    - `ghp_…` / `gho_…` / `ghu_…` / `ghs_…` / `ghr_…` of length ≥ 36
    - Slack-style `xox[bpars]-…` with at least two `-`-separated segments
    - JWT shape: three base64url segments separated by `.`, each ≥ 16 chars
    - `Authorization: …` headers (case-insensitive, with optional `Bearer `/`Basic ` prefix)
    - Bare bearer tokens of the shape `Bearer <token>` where `<token>` is ≥ 16 chars
  - Items that don't match anything are returned unchanged.
  - The helper is **pure**: same input → same output, no side effects.
  - Define the regex set once at module load (compiled patterns).

- **T007** — Add scrub-coverage unit tests to `tests/migration/test_mission_state_repair.py`
  under a clearly-named test class or function group. Cover, at minimum, every bullet above
  plus a control case that proves a benign argv (`['doctor', 'mission-state', '--fix',
  '--json']`) passes through unchanged. Each redacted case must assert the literal
  `"<redacted>"` appears in place of the value.

### Manifest expansion

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
  - Resolve `command_args = _scrub_secret_args(sys.argv[1:])` using the helper added in T006.
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

- **T012** — Add manifest-field tests to `tests/migration/test_mission_state_repair.py`:
  - Run `repair_repo` against a minimal fixture and parse the manifest JSON.
  - Assert all four new keys are present, types match, `policy` has all three sub-keys with
    sorted lists, `generated_ids` includes the `run_id`.
  - Assert no `command_args` entry leaks a secret (round-trip through scrubber).
  - Assert all pre-existing manifest keys are still present and unchanged in shape.

### Verification

- **T013** — Run the full migration test suite locally:
  `pytest tests/specify_cli/migration/test_rebuild_state.py tests/migration/test_mission_state_repair.py`
  and confirm green.

## Acceptance

- `_scrub_secret_args` exists, is pure, and is reachable from inside `mission_state.py`.
- `RepairReport` carries the four new fields.
- The manifest JSON contains them, sort-stable, JSON-valid.
- All existing manifest tests still pass.
- New manifest-field and scrub-coverage tests pass.
- Combined test run is green.

## Boundaries (do not touch)

- Do not modify `rebuild_state.py` (that's WP01).
- Do not change existing manifest field names or types.
- Do not add new top-level CLI surfaces or new dependencies.

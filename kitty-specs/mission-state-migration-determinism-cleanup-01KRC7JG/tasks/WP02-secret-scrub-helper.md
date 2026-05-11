---
work_package_id: WP02
title: Secret-Scrub Helper and Coverage
dependencies: []
requirement_refs:
- FR-008
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main; completed changes must merge back into main.
subtasks:
- T006
- T007
phase: Phase 1 - Determinism
assignee: ""
agent: ""
history:
- timestamp: "2026-05-11T19:20:00Z"
  agent: system
  action: Prompt generated for Mission 8 (migration determinism cleanup)
---

# Work Package Prompt: WP02 — Secret-Scrub Helper and Coverage

## Why this WP exists

The next WP (WP03) extends the repair manifest with a `command_args` field carrying a scrubbed
copy of `sys.argv[1:]`. That field is only safe if we can prove no bearer token, JWT, GitHub
token, Slack token, `Authorization:` header, or sensitive flag value can leak through. This WP
delivers the scrub helper and its dedicated tests so WP03 can simply call it.

## Files touched

- `src/specify_cli/migration/mission_state.py` (add helper near `_ACTOR_SAFE` regexes)
- `tests/migration/test_mission_state_repair.py` (add scrub-coverage tests)

## Tasks

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
  (or a new sibling test module if cleaner — operator's choice). Cover, at minimum, every
  bullet above plus a control case that proves a benign argv (`['doctor', 'mission-state',
  '--fix', '--json']`) passes through unchanged. Each redacted case must assert the literal
  `"<redacted>"` appears in place of the value.

## Acceptance

- `_scrub_secret_args` exists, is pure, has type annotations, and is reachable from inside
  `mission_state.py` (no need to export publicly).
- Every documented pattern has a passing test.
- `pytest tests/migration/test_mission_state_repair.py` is green.

## Boundaries (do not touch)

- Do not modify `RepairReport` in this WP — that happens in WP03.
- Do not modify `rebuild_state.py` in this WP.
- Do not add new top-level CLI surfaces or new dependencies.

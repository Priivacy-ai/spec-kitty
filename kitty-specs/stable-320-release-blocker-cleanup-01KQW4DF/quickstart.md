# Quickstart: 3.2.0 Release Blocker Cleanup

**Mission**: `stable-320-release-blocker-cleanup-01KQW4DF`
**Audience**: Implementers and reviewers for this mission

---

## Verification Commands

All commands run from the `spec-kitty` repository root unless noted.

### Blocker 1 — Sync Diagnostics (#952)

```bash
# Regression tests
cd /Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty
uv run pytest tests/sync/test_final_sync_diagnostics.py -v

# E2E clean output test
uv run pytest tests/e2e/test_mission_create_clean_output.py -v

# Live smoke (requires hosted connectivity)
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty sync status --json
```

**What to look for in smoke output**:
- `sync status --json` stdout parses as valid JSON
- Any sync warnings appear on stderr only, in `sync_diagnostic severity=warning` format
- No red failure prefixes, no `Connection failed` text in stdout

### Blocker 2 — mark-status (#783)

```bash
# Regression tests
uv run pytest tests/git_ops/test_mark_status_pipe_table.py -v
uv run pytest tests/specify_cli/cli/commands/agent/ -k "mark_status" -v

# Live smoke (replace <mission> with an existing test mission)
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty agent tasks mark-status T001 \
  --status done --mission <mission> --json
```

**What to look for**:
- JSON output includes `results` array with per-ID entries
- Each entry has `id`, `outcome`, `format`, `message`
- `summary` counts match

### Blocker 3 — Cross-Repo E2E (#975)

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty-end-to-end-testing

# Unit tests for nested_env helper
uv run pytest tests/test_nested_env_helper.py -v

# Full E2E scenario
SPEC_KITTY_REPO=/Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
UV_CACHE_DIR=/private/tmp/spec-kitty-e2e-uv-cache \
uv run --python 3.11 python -m pytest scenarios/contract_drift_caught.py -v
```

**What to look for**:
- No `libpython` or `ensurepip` errors
- Test reports `PASSED` (not `ERROR` or `SKIPPED` for an env reason)
- Drift assertion fires correctly (scenario detects the drifted events package)

### Blocker 4 — merge --dry-run (#976)

```bash
# Regression tests
uv run pytest tests/merge/test_merge_preflight_mission_branch.py -v
uv run pytest tests/merge/ -v

# Live smoke (replace <mission> with a mission that has no kitty/mission-<slug> branch)
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty merge \
  --mission <mission> --dry-run --json
```

**What to look for in dry-run output when branch is missing**:
```json
{
  "ready": false,
  "blocker": "missing_mission_branch",
  "expected_branch": "kitty/mission-<slug>",
  "remediation": "git branch kitty/mission-<slug> <sha>"
}
```

### Full regression sweep

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty
uv run pytest \
  tests/sync/test_final_sync_diagnostics.py \
  tests/e2e/test_mission_create_clean_output.py \
  tests/git_ops/test_mark_status_pipe_table.py \
  tests/merge/ \
  -v
```

---

## Development Setup

```bash
# Install spec-kitty in editable mode
cd /Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty
uv pip install -e ".[dev]"

# Type check
uv run mypy --strict src/specify_cli/sync/diagnostics.py
uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py
uv run mypy --strict src/specify_cli/cli/commands/merge.py

# E2E repo setup
cd /Users/robert/spec-kitty-dev/spec-kitty-20260505-090055-4etGRd/spec-kitty-end-to-end-testing
uv pip install -e ".[dev]"
uv run mypy --strict support/nested_env.py
```

---

## Issue Closure Evidence

For each issue, capture the following before closing:

| Issue | Evidence needed |
|-------|----------------|
| #952 | `tests/sync/test_final_sync_diagnostics.py` all passing; smoke run log showing no red failure output |
| #783 | All 8 mark-status regression tests passing; live `--json` output showing per-ID results |
| #975 | `scenarios/contract_drift_caught.py` PASSED (not SKIPPED) on this macOS uv Python runner |
| #976 | `tests/merge/test_merge_preflight_mission_branch.py` all passing; dry-run `--json` showing `ready: false` with structured blocker |

Save evidence in `kitty-specs/stable-320-release-blocker-cleanup-01KQW4DF/smoke-evidence.md` before closing issues.

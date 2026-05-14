# Quickstart — Workflow Parity Fixes 988/989/991

## Verify the bugs (before the fix)

```bash
# #988 — next --json claimability
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty next \
  --mission <slug-of-implement-ready-mission> \
  --json
# Expect: mission_state=implement, planned_wps>=1, wp_id=null (bug)

# #989 — lightweight review on baseline-less modern mission
uv run spec-kitty review \
  --mission <slug-with-mission-id-and-no-baseline> \
  --mode lightweight
# Expect: clean pass with "Dead-code scan skipped" message (bug)

# #991 — merge --dry-run with stale rejected review-cycle artifact
SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run spec-kitty merge \
  --mission <slug-with-rejected-cycle-on-approved-wp> \
  --dry-run \
  --json
# Expect: exit 0, normal preview, no REJECTED_REVIEW_ARTIFACT_CONFLICT (bug)
```

## Verify the fixes (after the fix)

```bash
# #988 — next --json must serialize wp_id
uv run spec-kitty next --mission <slug> --json | jq '.wp_id, .selection_reason'
# Expect: a concrete WP id and selection_reason=null

# #989 — lightweight review must reject silently-skipped baseline
uv run spec-kitty review --mission <slug> --mode lightweight; echo $?
# Expect: non-zero exit, diagnostic code LIGHTWEIGHT_REVIEW_MISSING_BASELINE

# #991 — merge --dry-run must surface the consistency conflict
uv run spec-kitty merge --mission <slug> --dry-run --json | jq '.blockers // .errors'
# Expect: contains REJECTED_REVIEW_ARTIFACT_CONFLICT
```

## Targeted test suites

```bash
# All four pre-existing suites that must stay green:
uv run pytest \
  tests/integration/test_mission_review_contract_gate.py \
  tests/post_merge/test_review_artifact_consistency.py \
  tests/specify_cli/cli/commands/test_review.py \
  tests/specify_cli/cli/commands/review/test_mode_resolution.py \
  -q

# Focused suites touched by this mission:
uv run pytest \
  tests/specify_cli/cli/commands/test_merge.py \
  tests/specify_cli/cli/commands/test_review.py \
  tests/next/test_next_command_integration.py \
  -q
```

## Pre-PR checks

```bash
git diff --check
uv run mypy --strict src/specify_cli
uv run ruff check src tests
```

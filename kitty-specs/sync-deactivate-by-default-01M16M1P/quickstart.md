# Quickstart: verifying sync deactivation

## Default path (bare install) — must be quiet
```bash
# no SPEC_KITTY_ENABLE_SAAS_SYNC set
spec-kitty agent tasks status            # no daemon, no 'sync store is locked' warning
# run a lifecycle action and assert no traceback / no enqueue
```
Expected: exit 0, no daemon process, no events, no `project sync store is locked` / `Event routing failed` / body-outbox `RuntimeError`.

## Opt-in path — full sync restored
```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty ...   # registration, daemon, emission active
```

## Pre-review gate is independent
```bash
# gate runs by default even with sync off:
spec-kitty agent tasks move-task WP01 --to for_review        # gate executes
SPEC_KITTY_PRE_REVIEW_GATE_DISABLE=1 spec-kitty ... move-task # gate skipped, sync unaffected
```

## Test verification
```bash
# default-off: sync tests skip
PWHEADLESS=1 .venv/bin/python -m pytest tests/sync -q          # skipped, 0 failed
# opt-in parity (collection diff, no double run):
SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/python -m pytest tests/sync tests/specify_cli/sync --collect-only -q
# file-count census + completeness gate:
.venv/bin/python -m pytest tests/architectural -k "sync_census or collection_completeness" -q
```

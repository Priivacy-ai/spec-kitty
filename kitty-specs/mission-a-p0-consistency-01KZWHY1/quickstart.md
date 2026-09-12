# Quickstart — Mission A verification

Each fix is verified by turning its red-first reproduction green **via the
product fix only** (never by weakening the test), plus the mandatory guard tests.
Red-first repros live under `tests/regression/` and run only under `-m regression`.

## Run the four reproductions (red today; green as each fix lands)

```bash
PWHEADLESS=1 .venv/bin/python -m pytest tests/regression/ -m regression -q \
  -k "3320 or 3231 or 3334 or 3311"
```

## Per-fix loop

```bash
# IC-01 #3320 — retrospect --update
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/regression/test_issue_3320_retrospect_update_reports_stale_findings.py -q
# + new guard: emitted-event-payload matches persisted record (tests/cli/commands/)

# IC-02 #3231 — acceptance verdict
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/regression/test_issue_3231_scaffold_pending_poisons_acceptance.py -q
# + new guards: partial-authoring→pending, all-scaffold→pending (tests/acceptance/)

# IC-03 #3334 — REPLACED repro drives real MigrationRunner.upgrade()
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/regression/test_issue_3334_failed_upgrade_wedges_repair.py -q
# assert: schema_version stays 3 after failed upgrade; gate("plan") no SystemExit;
#         genuine pre-3.x still LEGACY + SystemExit(4)

# IC-04 #3311 — finalize provenance (run serially if it touches status daemon)
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/regression/test_issue_3311_finalize_rewrites_active_lanes.py -q
# + new guards: non-None-tip preservation; benign pre-execution re-finalize regenerates
```

## Gates before hand-off (per WP + aggregate)

```bash
ruff check .
PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q   # doctrine/prose guard
# Targeted suites for the touched modules (no full arch suite locally):
PWHEADLESS=1 .venv/bin/python -m pytest tests/acceptance/ tests/cli/commands/ \
  tests/specify_cli/compat/ tests/specify_cli/cli/commands/agent/ tests/upgrade/ -q
```

## Exit rule (per `tests/regression/README.md`)

When a reproduction turns green, move it to the functional suite matching the
module it exercises, drop `@pytest.mark.regression`, add the canonical
`unit`/`integration` marks, and update the docstring to say the defect is fixed
(keep the issue reference as history). #3334's repro is **replaced** (not merely
relocated) because the committed one pins the wrong contract (C-006).

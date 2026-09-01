# Quickstart — Validating Mission Completion Terminal State

End-to-end acceptance validation for the mission. All commands are black-box against the
canonical CLI (directive 036); none hand-edit the event log.

## Scenario A — canceled-with-provenance completes (SC-001, #2945 repro → green)

```bash
# In a scratch mission with WP01..WP03 approved and WP04 a replanned cancellation:
spec-kitty agent tasks move-task WP04 --to canceled \
  --note "Canceled by replan: scope absorbed by WP02's documentation fix."
spec-kitty accept --mission <handle> --json | jq '.canceled_wps, .blockers'
#   → canceled_wps: [{wp_id:"WP04", reason:"Canceled by replan…", actor, at}]
#   → blockers: []   (accept passes)
spec-kitty merge --mission <handle> --dry-run
#   → plans WP01..WP03; WP04 excluded from done/review assertions & order; audit retained
```

## Scenario B — canceled without operator provenance is blocked (SC-002)

```bash
spec-kitty agent tasks move-task WP04 --to canceled --force   # no --note
spec-kitty accept --mission <handle> --json | jq '.blockers'
#   → a structured blocker naming WP04 and "operator-authored cancellation provenance required"
#   → WP04 is NOT in canceled_wps
```

## Scenario C — non-terminal lane still blocks (FR-006) & gate integrity (SC-005)

```bash
# WP03 left in in_review, WP04 canceled-with-provenance:
spec-kitty accept --mission <handle> --json | jq '.blockers'
#   → WP03 blocker present; acceptance-matrix / issue-matrix verdict gates still evaluated
```

## Scenario D — dependency on a canceled WP does not strand the dependent (SC-005/FR-009)

```bash
# WP05 depends on WP04; cancel WP04 with provenance:
spec-kitty agent tasks move-task WP04 --to canceled --note "replan"
spec-kitty agent tasks status --mission <handle> --json | jq '.wps[] | select(.wp_id=="WP05")'
#   → WP05 is claimable (dependency resolved), can reach an acceptable ending
```

## Scenario E — authoring-time warning is advisory (FR-007/FR-008, SC-003)

```bash
# Author a decomposition containing a post-integration-only WP:
spec-kitty agent mission finalize-tasks --mission <handle>
#   → warning naming the WP + matched phrase; finalize still succeeds (advisory)
# Ordinary all-code decomposition → no warning (negative corpus).
```

## Regression gate (NFR-001/SC-004)

```bash
# Baseline commit: a59460ec15
PWHEADLESS=1 pytest \
  tests/status/test_transitions.py tests/status/test_reducer.py \
  tests/specify_cli/test_canonical_acceptance.py \
  tests/specify_cli/test_acceptance_regressions.py \
  tests/specify_cli/cli/commands/agent/test_finalize_canceled_work_packages.py \
  -n0 -q
ruff check . && mypy src/specify_cli/status_lanes.py src/specify_cli/acceptance src/specify_cli/merge
```
Classify any red per the baseline-red gotcha (known-P0 reds are not this mission's).

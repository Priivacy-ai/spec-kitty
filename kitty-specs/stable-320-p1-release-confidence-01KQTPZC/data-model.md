# Data Model: Stable 3.2.0 P1 Release Confidence

## Task Board Progress

Represents the values displayed by `spec-kitty agent tasks status`.

Fields:

- `total_wps`: count of WPs included in status.
- `done_count`: count of WPs in the `done` lane.
- `done_percentage`: `done_count / total_wps * 100`, or `0` when `total_wps` is zero.
- `weighted_percentage`: existing lane-weighted progress from `compute_weighted_progress(...)`.
- `ready_count`: count of WPs considered ready or complete if implementation chooses a ready label.
- `progress_label`: human-readable label that states whether the value is done progress, weighted progress, or ready progress.
- `per_lane_counts`: counts by canonical lane.

Invariants:

- A done-only numerator must not be displayed beside a weighted or ready percentage without an explicit label.
- Empty boards return zero progress and do not divide by zero.
- JSON output remains parseable.
- If a field is weighted, its name or label must say weighted, readiness, or an equivalent explicit term.

## Work Package Lane

Canonical lane state loaded from `status.events.jsonl` and rendered into the task board.

Relevant values:

- `planned`
- `claimed`
- `in_progress`
- `for_review`
- `in_review`
- `approved`
- `done`
- `blocked`
- `canceled`

State contribution:

- `done` contributes to done progress.
- `approved` contributes to weighted/ready progress but not done progress.
- `blocked` and `canceled` do not represent forward progress.

## Dependency Drift Evidence

Represents the comparison between lockfile resolution and the installed environment used by review or release gates.

Fields:

- `package`: package name, initially `spec-kitty-events`.
- `lockfile_version`: version resolved in `uv.lock`.
- `installed_version`: version from the active environment package metadata.
- `constraint`: dependency constraint from `pyproject.toml`.
- `status`: `match`, `mismatch`, or `not_checked`.
- `remediation`: operator command, preferably `uv sync --extra test --extra lint`.

Invariants:

- A mismatch must fail the guard when release/review evidence depends on that environment.
- The guard must not loosen dependency constraints as remediation.
- `spec-kitty-tracker` is included only if verification proves the same risk exists and scope stays small.

## Workflow Smoke Result

Represents a fresh lifecycle smoke outcome.

Fields:

- `mode`: `local-only` or `saas-enabled`.
- `commands_run`: ordered command list.
- `requires_saas_sync_flag`: boolean.
- `sync_flag_applied`: boolean for each hosted/sync command path.
- `result`: `pass`, `fail-fixed`, `fail-blocker`, or `fail-deferred-with-issue`.
- `evidence_path`: local artifact or linked issue/PR evidence.

Invariants:

- Local-only smoke must not require hosted auth, tracker, SaaS, or sync.
- SaaS-enabled smoke must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on hosted auth, tracker, SaaS, or sync command paths.
- Any failure must have an issue, a narrow fix, or an explicit stable-release blocker decision.

## Release Evidence Record

Represents the final acceptance packet for this mission.

Fields:

- `issue_966_result`
- `issue_848_result`
- `local_smoke_result`
- `saas_smoke_result`
- `ruff_status`
- `issue_971_decision`
- `p2_p3_deferrals`
- `blocking_decisions`

Invariants:

- #971 is always explicitly included or deferred.
- #869 remains stale unless a fresh repro appears.
- Prior P0 issues #967, #904, #968, and #964 are not scheduled without a fresh regression.

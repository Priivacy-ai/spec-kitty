# Release Evidence

Evidence collected for `stable-320-p1-release-confidence-01KQTPZC` on
2026-05-05. This mission targets stable 3.2.0 P1 release confidence around
#966, #848, fresh workflow smoke coverage, and release-scope deferrals.

## #966 Task Board Progress Semantics

Status: ready to close after merge.

WP01 commit: `acc3a50f feat(WP01): clarify task status progress semantics`
on `kitty/mission-stable-320-p1-release-confidence-01KQTPZC-lane-a`.

Implemented semantics:

- `done_count` remains done-only.
- `done_percentage` reports done-only completion.
- `progress_percentage` remains the backward-compatible weighted readiness
  percentage.
- JSON adds `progress_semantics: "weighted_readiness"` and
  `weighted_percentage` so consumers can distinguish completion from readiness.
- Human status output separates `Done progress` from `Weighted readiness`, so
  approved-only boards no longer render ambiguous text like `Progress: 0/2
  (80.0%)`.

Focused verification:

- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run pytest tests/specify_cli/status tests/specify_cli/agent_utils/test_status.py tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py -q`
  passed: 292 tests.
- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run ruff check src/specify_cli/status/progress.py src/specify_cli/agent_utils/status.py src/specify_cli/cli/commands/agent/tasks.py tests/specify_cli/status/test_progress.py tests/specify_cli/agent_utils/test_status.py tests/specify_cli/cli/commands/agent/test_tasks_status_progress.py`
  passed.
- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run mypy --strict src/specify_cli/status/progress.py`
  passed.
- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run spec-kitty agent tasks status --mission stable-320-p1-release-confidence-01KQTPZC --json`
  showed `progress_semantics`, `weighted_percentage`, `done_count`, and
  `done_percentage`.

Coverage includes approved-only, done-only, mixed approved/done, and empty
states through focused progress/status regression tests.

## #848 Dependency Drift Gate

Status: ready to close after merge.

WP02 commit: `44a181dc feat(WP02): add installed drift guard` on
`kitty/mission-stable-320-p1-release-confidence-01KQTPZC-lane-b`.

Implemented guard:

- `scripts/release/check_shared_package_drift.py --check-installed` now compares
  active installed shared-package metadata with `uv.lock`.
- The check covers `spec-kitty-events` and `spec-kitty-tracker`.
- Release/readiness workflows invoke the installed drift guard.
- A mismatch tells operators to run `uv sync --extra test --extra lint`.
- Workflow path filters include `uv.lock` so lockfile-only drift is checked.

Version evidence:

- Installed `spec-kitty-events`: `4.1.0`.
- `uv.lock` `spec-kitty-events`: `4.1.0`.
- Constraint: `spec-kitty-events>=4.0.0,<5.0.0`.
- Installed `spec-kitty-tracker`: `0.4.3`.
- `uv.lock` `spec-kitty-tracker`: `0.4.3`.

Focused verification:

- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv lock --check` passed.
- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run python scripts/release/check_shared_package_drift.py --check-installed`
  passed and printed both installed and lockfile shared-package versions.
- `UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run pytest tests/release -q`
  passed: 75 passed, 7 skipped.

## Fresh Workflow Smoke

Source: `smoke-evidence.md`.

Local-only lifecycle:

- Result: passed with bounded disposable-branch setup.
- Covered setup, specify, plan, tasks finalization, implement, review,
  approval, PR-ready dry-run, and merge.
- No hosted auth, tracker, SaaS, or sync dependency was used in the local path.

SaaS-enabled lifecycle:

- Result: lifecycle passed with bounded sync-drain limitation.
- Covered the same setup/specify/plan/tasks/implement/review/approval/PR-ready
  dry-run/merge shape where current CLI surfaces allow it.
- Every hosted auth, SaaS, or sync command in the evidence used
  `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- Auth/status probes are recorded only as prerequisites, not as standalone proof.
- Hosted drain proof was unavailable because the local daemon reported
  `sync.final_sync_lock_unavailable`, WebSocket offline, and auth-refresh
  contention. Commands completed and events queued; this is not marked as a
  stable-release blocker.

## Final Gate

`UV_CACHE_DIR=/private/tmp/spec-kitty-uv-cache uv run ruff check src tests`
passed on 2026-05-05.

## #971 Strict Mypy Decision

Status: deferred, not included in this mission.

WP01 ran strict mypy only for the changed `status/progress.py` surface. The
broader strict mypy gate tracked by #971 remains out of scope for this P1
release-confidence mission and is recorded in `deferrals.md`.

## Residual Risks

- SaaS sync drain did not prove server-side delivery during WP03 because the
  local daemon/auth state was contended and WebSocket was offline.
- The broad WP01 suggested command
  `uv run pytest tests/specify_cli/status tests/specify_cli/cli/commands/agent -q`
  had 399 passed and 2 failures in unrelated wrapper-delegation tests caused by
  running implement-wrapper tests from inside a lane worktree. Focused WP01
  status/progress coverage passed.
- WP01 and WP02 source commits are approved on lane branches and become part of
  the release candidate after `spec-kitty merge`.

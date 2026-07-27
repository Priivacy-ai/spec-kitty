# Fresh Workflow Smoke Evidence

WP03 ran two disposable lifecycle smokes for Spec Kitty CLI `3.2.0a10` on
2026-05-05. The version was confirmed from the mission repo with
`uv run spec-kitty --version`, which printed
`spec-kitty-cli version 3.2.0a10`. Workspaces were created outside the mission
artifact directory:

- Local-only: `/private/tmp/spec-kitty-smoke-20260505T0053/local-smoke`
- SaaS-enabled: `/private/tmp/spec-kitty-smoke-20260505T0053/saas-smoke`

## Summary

| Smoke | Result | Notes |
| --- | --- | --- |
| Local-only lifecycle | Passed with bounded branch setup | The lifecycle reached setup, specify, plan, tasks finalization, implement, review, approved, and merge. The first merge attempt failed because the disposable scaffold path did not create `kitty/mission-local-smoke-mission-01KQTT1A`; after creating that expected mission branch, merge passed. |
| SaaS-enabled lifecycle | Passed with bounded sync-drain limitation | The same lifecycle shape reached merge with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on hosted/sync-capable commands. Hosted prerequisites showed authenticated user state and enabled SaaS sync, but final sync drain reported lock/auth-refresh contention and WebSocket offline. Events remained queued for the daemon. |

No smoke failure is being treated as a stable-release blocker. The local merge
branch setup is a disposable-workspace setup prerequisite, not a product
lifecycle failure. The SaaS sync limitation is bounded to the local daemon/auth
refresh state on this workstation; lifecycle commands completed and queued
events, while hosted drain proof remains unavailable in this run.

## Local-Only Lifecycle

Local-only commands deliberately avoided hosted auth, tracker, SaaS, and sync
surfaces.

| Step | Command | Exit | Evidence |
| --- | --- | ---: | --- |
| Version | `uv run spec-kitty --version` | 0 | `spec-kitty-cli version 3.2.0a10` |
| Setup | `git init -b main`; `.venv/bin/spec-kitty init --ai codex --non-interactive` | 0 | Project ready; Codex command skills installed. |
| Specify | `.venv/bin/spec-kitty specify local-smoke-mission --mission-type software-dev --json` | 0 | Created `local-smoke-mission-01KQTT1A`. |
| Plan prerequisite | Populate and commit substantive `spec.md` | 0 | `docs: add smoke specification` committed. |
| Plan | `.venv/bin/spec-kitty plan --mission local-smoke-mission-01KQTT1A --json` | 0 after substantive plan was supplied | Plan surface accepted a substantive plan. A no-change rerun emitted `Failed to commit plan`, which was not a lifecycle blocker. |
| Tasks | Create bounded `tasks.md` and `tasks/WP01-artifact-smoke.md`; `.venv/bin/spec-kitty agent mission finalize-tasks --mission local-smoke-mission-01KQTT1A --json` | 0 | Finalized 1 WP, computed `lane-planning`, commit `56e788c`. |
| Implement | `.venv/bin/spec-kitty agent action implement WP01 --mission local-smoke-mission-01KQTT1A --agent codex:gpt-5:python-pedro:implementer` | 0 | Claimed WP01 in repo root planning lane. |
| Implementation artifact | Commit `kitty-specs/local-smoke-mission-01KQTT1A/smoke-output.md` | 0 | Commit `1b740a1`. |
| Review handoff | `.venv/bin/spec-kitty agent tasks move-task WP01 --to for_review --mission local-smoke-mission-01KQTT1A --note "Ready for review: smoke artifact created"` | 0 | WP01 moved to `for_review`; `mark-status T001` was skipped because the bounded generated `tasks.md` had no checkbox task IDs. |
| Review | `.venv/bin/spec-kitty agent action review WP01 --mission local-smoke-mission-01KQTT1A --agent codex:gpt-5:python-pedro:reviewer` | 0 | Review prompt generated. |
| Approval | `.venv/bin/spec-kitty agent tasks move-task WP01 --to approved --mission local-smoke-mission-01KQTT1A --note "Review passed: smoke artifact exists"` | 0 | WP01 moved to `approved`. |
| PR-ready preview | `.venv/bin/spec-kitty merge --mission local-smoke-mission-01KQTT1A --dry-run --json` | 0 | Would assign mission number 1 and merge `lane-planning`. |
| Merge | `git branch kitty/mission-local-smoke-mission-01KQTT1A`; `.venv/bin/spec-kitty merge --mission local-smoke-mission-01KQTT1A` | 0 | Merged mission into `main`, commit `0456e80`; stale assertion check found no likely-stale assertions. |

## SaaS-Enabled Lifecycle

Every hosted auth, SaaS, or sync command below was run with
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

### Prerequisite Probes

These probes establish hosted readiness only; they are not counted as lifecycle
proof by themselves.

| Probe | Command | Exit | Evidence |
| --- | --- | ---: | --- |
| Auth status | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty auth status` | 0 | Authenticated as `robert@spec-kitty.ai`; access token expired, refresh token valid for 86 days. |
| Sync status | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty sync status` | 0 | SaaS sync enabled, daemon running at `127.0.0.1:9416`, server `https://spec-kitty-dev.fly.dev`, WebSocket offline, queue depth 84,352/100,000. |

### Mirrored Lifecycle

| Local lifecycle step | SaaS-enabled command | Exit | Hosted/sync evidence |
| --- | --- | ---: | --- |
| Setup | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty init --ai codex --non-interactive` | 0 | Project ready; generated SaaS project metadata in `.kittify/config.yaml`. |
| Specify | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty specify saas-smoke-mission --mission-type software-dev --json` | 0 | Created `saas-smoke-mission-01KQTT62`; final sync warned `sync.final_sync_lock_unavailable`, events queued for daemon. |
| Plan | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty plan --mission saas-smoke-mission-01KQTT62 --json` | 0 | Accepted substantive plan; final sync lock unavailable warning repeated. |
| Tasks | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty agent mission finalize-tasks --mission saas-smoke-mission-01KQTT62 --json` | 0 | Finalized 1 WP, computed `lane-planning`, committed dossier snapshot; final sync lock unavailable warning repeated. |
| Implement | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty agent action implement WP01 --mission saas-smoke-mission-01KQTT62 --agent codex:gpt-5:python-pedro:implementer` | 0 | Claimed WP01; final sync lock unavailable warning repeated. |
| Review handoff | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty agent tasks move-task WP01 --to for_review --mission saas-smoke-mission-01KQTT62 --note "Ready for review: SaaS smoke artifact created"` | 0 | WP01 moved to `for_review`; final sync lock unavailable warning repeated after committing generated sync config. |
| Review | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty agent action review WP01 --mission saas-smoke-mission-01KQTT62 --agent codex:gpt-5:python-pedro:reviewer` | 0 | Review prompt generated; final sync lock unavailable warning repeated. |
| Approval | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty agent tasks move-task WP01 --to approved --mission saas-smoke-mission-01KQTT62 --note "Review passed: SaaS smoke artifact exists"` | 0 | WP01 moved to `approved`; final sync lock unavailable warning repeated. |
| PR-ready preview | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty merge --mission saas-smoke-mission-01KQTT62 --dry-run --json` | 0 | Would assign mission number 1 and merge `lane-planning`. |
| Merge | `git branch kitty/mission-saas-smoke-mission-01KQTT62`; `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty merge --mission saas-smoke-mission-01KQTT62` | 0 | Merged mission into `main`, commit `2d5d67d`; stale assertion check found no likely-stale assertions; final sync lock unavailable warning repeated. |
| Hosted drain check | `SPEC_KITTY_ENABLE_SAAS_SYNC=1 .venv/bin/spec-kitty sync status --check` | 0 due `|| true` capture wrapper; probe reported error | Ping failed: `Authentication probe failed: Another spec-kitty process is refreshing the auth session; retry in a moment.` Queue depth increased to 84,374; WebSocket remained offline. |

## Failure And Limitation Handling

- `mark-status T001` failed in both disposable missions because the bounded
  smoke `tasks.md` did not contain checkbox task IDs. This did not block the
  lifecycle because WP lane transitions and merge succeeded.
- The first local merge failed before creating the disposable mission branch.
  Creating the expected `kitty/mission-*` branch allowed the same merge command
  to pass. This is recorded as disposable setup behavior, not a stable blocker.
- SaaS final sync did not drain during the run. The commands queued events and
  completed, but `sync status --check` reported local auth-refresh contention
  and WebSocket offline. This is a bounded hosted-sync limitation for this
  workstation run. It does not claim tracker rollout gating exists and does not
  use status/help probes as standalone proof of SaaS lifecycle success.

## Artifacts

No long raw logs were committed. The disposable repositories remain under
`/private/tmp/spec-kitty-smoke-20260505T0053/` for local inspection during this
session.

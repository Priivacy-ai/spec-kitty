---
title: 'Known Current Friction Points'
description: 'A time-stamped, fast-drifting list of current repo and tooling friction points a maintainer or agent hits mid-mission; re-verify against the tracker before trusting specifics.'
doc_status: active
updated: '2026-07-24'
type: reference
related:
- docs/development/pr-landing.md
- docs/development/onboarding-run.md
- docs/development/testing-flakiness.md
- docs/development/testing-parallel.md
- docs/development/red-main-and-release-readiness.md
- docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md
---
# Known Current Friction Points

> **This page is deliberately time-sensitive and drifts fast.** It captures
> repo and tooling friction that a maintainer — or an agent acting in a
> maintainer capacity — is likely to hit while running a mission *today*. It is
> **not** durable doctrine: specific issue numbers, version gates, and toggles
> change as the codebase moves. Always re-verify against the authoritative
> sources before trusting a specific number:
> [`CLAUDE.md`](../../CLAUDE.md) (its "Test-run baseline-red gotcha" note),
> [ADR 2026-07-17-1](../adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md),
> and the issue tracker.

**Snapshot date: 2026-07-24 · Spec Kitty 3.2.x.** Proof that this list drifts:
`#2772` was a known-red P0 when this note was first drafted and has since been
closed — so the "known reds" below are already a different set than a month ago.

## The friction points

- **`main` may be legitimately RED.** Honest P0 reproductions are left red on
  purpose ([ADR 2026-07-17-1](../adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md));
  currently open examples: **#2736**, **#1834**. Before "fixing" any red,
  **attribute** it — reproduce on `upstream/main` / the merge-base. Never
  green-wash a `@pytest.mark.regression` red; that erases a deliberate
  release-blocker signal.
- **CI-environment false reds that pass locally:** auth
  (`logged_out_on_connected_teamspace`) and the sync toggles
  (`SPEC_KITTY_SYNC_MINIMAL_IMPORT` / `SPEC_KITTY_SYNC_DISABLE`, which also skip
  the pre-review gate). Config, not your diff.
- **Stale-install false reds.** Commands that shell out to `spec-kitty` (e.g.
  the `merge-driver-*` commands) only reflect your working tree after
  `pip install -e .` / `uv pip install -e .`. Re-install after every rebase.
- **Real-port / daemon tests are not HOME-isolated** (ports 9400–9449). Run them
  serially with `-n0`. Leaked daemons from a prior run squat those ports and fail
  singleton/reaping tests (`test_issue_1071_*`) with a "got 2 ports" assertion —
  that is environmental, not your change. Check `ss -ltnp | grep 94` if a daemon
  test flaps.
- **In a lane or clone, a bare `python` / `pytest` imports the PRIMARY `src`, not
  your lane.** Always `uv run <cmd>`.
- **CI-only gates that pass locally then fail ~40 minutes later:** the
  terminology guard, the architectural shards
  (`integration-tests-core-misc (architectural)`, `arch-adversarial`),
  `canonical-producer-lint` (CP001 fires on a hand-rolled event dict with
  `event_type`+`payload` keys — build via `spec_kitty_events.lifecycle.*`
  instead), and `docs-freshness`. Run `tests/architectural/`, the terminology
  guard, and `PYTHONPATH=. python scripts/docs/check_docs_freshness.py --ci`
  locally on the **rebased** tip before declaring a branch green.
- **The status daemon can auto-commit your staged files** with the *previous*
  mission's commit message. Commit promptly; do not leave a dirty index while it
  runs.
- **No `git stash` in lane worktrees** — the stash stack is shared across
  worktrees, so a `pop` can steal a sibling lane's work-in-progress.
- **`move-task` can hang on sync-daemon fan-out.** Background it and set
  `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`.
- **After `finalize-tasks`, verify the issue-matrix / coordination state.** 3.2.6
  made the PRIMARY scaffolder idempotent; the coord/merge reset path is not fully
  verified.
- **Docs scripts need `PYTHONPATH=.`**, and `build_cli_reference.py` defaults to
  the *wrong* output path — pass `--output docs/api/cli-commands.md
  --agent-output docs/api/agent-subcommands.md` explicitly.
- **Shared-package boundary:** anchor new runtime code in
  `src/runtime/next/_internal_runtime/`; `src/specify_cli/next/` is a shim
  removed in 3.3.0. Consume events / tracker only via `spec_kitty_events.*` /
  `spec_kitty_tracker.*`.

## Maintaining this page

When you hit a new mid-mission friction point — or when one above stops being
true (a known-red P0 closes, a toggle is retired, a version gate passes) —
update this page and bump the snapshot date in the same change. Keep entries
short and actionable; deep rationale belongs in the linked runbooks, not here.

## See also

- [Landing contributor PRs](pr-landing.md) — the maintainer landing runbook.
- [Onboarding run](onboarding-run.md) — the mission-run priming prompt that
  points here.
- [Test-flakiness handling policy](testing-flakiness.md) — the never-retry-to-green rule.
- [Red main and release readiness](red-main-and-release-readiness.md).

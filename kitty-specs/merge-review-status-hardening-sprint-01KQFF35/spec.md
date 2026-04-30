# Merge Abort, Review, and Status Hardening Sprint

**Mission ID**: 01KQFF35BPH2H8971KR0TEY8ST
**Mission Type**: software-dev
**Status**: Specifying
**Created**: 2026-04-30

## Purpose

Fix two confirmed bugs and add five targeted enhancements to the spec-kitty CLI.
All seven were observed or witnessed firsthand during mission
`auth-tranche-2-5-cli-contract-consumption-01KQEJZK` (PR #902).

The bugs leave operators stuck with orphaned lock files and silently inconsistent
review artifacts. The enhancements close systematic gaps in review quality, error
message usability, linting discipline, status-board visibility, and post-merge
lifecycle governance.

## Background

After a squash merge crashed mid-run, operators discovered that
`spec-kitty merge --abort` did not clean up the runtime lock file, requiring a
manual `rm` to unblock the next merge attempt. Separately, a force-approval of
a work package left its review artifact showing `verdict: rejected` with no
warning — the inconsistency was only caught by a manual audit.

Five additional improvements were identified in the same session:
lane guard error messages gave no hint that planning artifacts were correctly
present on the planning branch; the WP review checklist had no explicit check for
error-path test reachability; BLE001 suppressions in security-critical modules
lacked justification comments; stalled reviewer agents were invisible in the
status board; and there was no structured CLI gate between merge and release.

## Primary Actors

- **Orchestrator agent** — drives `spec-kitty merge`, `move-task`, and
  `spec-kitty next`; the primary person or agent affected by bugs #903 and #904
- **Reviewer agent** — runs WP review flows and is affected by issue #906
- **Developer / operator** — reads status output, lane guard errors, and
  mission review reports; affected by issues #905, #907, #908, #909

## Scope

### In scope

- `spec-kitty merge --abort` cleanup behaviour (#903)
- Validation and warning when force-approving a WP with a rejected verdict (#904)
- Lane guard error message improvement to name the planning branch (#905)
- WP review DoD template text addition for error-path test reachability (#906)
- BLE001 suppression audit and justification in `auth/` and `cli/commands/` (#907)
- `spec-kitty review --mission <slug>` command (MVP scope only) (#908)
- Stalled-reviewer detection in `spec-kitty agent tasks status` and `spec-kitty next` (#909)

### Out of scope

- Changes to the merge execution logic (only the `--abort` cleanup path changes)
- Auto-updating review artifact verdicts on force-approve (Option B from #904 context dump)
- Custom ruff rules or pre-commit hooks for BLE001 (Option B from #907); only
  per-file-ignores + inline justification comments are in scope
- Any SaaS or remote-sync integration for the mission review command
- Changes to any agent-generated copies under `.claude/commands/`,
  `.amazonq/prompts/`, or any other agent directory

## User Scenarios and Testing

### Scenario 1 — Clean abort after a crashed merge

An orchestrator agent runs `spec-kitty merge` for a feature. The process
crashes mid-run. The agent runs `spec-kitty merge --abort`. The abort succeeds
with exit code 0, the lock file is gone, the merge-state JSON is gone, and any
in-progress git merge is aborted. Running `spec-kitty merge --abort` a second
time also exits 0 with no error.

### Scenario 2 — Force-approve blocked by stale rejected verdict

An orchestrator agent runs `move-task WP05 --to approved --force`. The most
recent review-cycle artifact for WP05 contains `verdict: rejected`. The command
prints a warning naming the artifact file and the verdict, then exits non-zero.
The WP remains in its current lane. Running the same command with
`--skip-review-artifact-check` bypasses the warning and succeeds.

### Scenario 3 — Status board warns on stale approved WP

A WP is in `done` lane but its most recent review-cycle artifact still shows
`verdict: rejected`. Running `spec-kitty agent tasks status` displays a warning
next to that WP.

### Scenario 4 — Lane guard names the planning branch

A reviewer agent is on a lane branch and tries to commit a change under
`kitty-specs/`. The lane guard error message names the planning branch and
provides a `git show <planning-branch>:kitty-specs/` command to verify the file
exists there.

### Scenario 5 — WP review rejects untested error path

A reviewer follows the updated WP review checklist. The checklist now includes
an explicit step requiring that each error-path test is verified to fail when
the implementation fix is deleted. A test that only validates the exception
handler's structure is flagged as insufficient.

### Scenario 6 — Mission review command runs cleanly

An operator runs `spec-kitty review --mission merge-review-status-hardening-sprint-01KQFF35`.
All WPs are in `done`. No new public symbols are unreferenced. No unjustified
BLE001 suppressions are found. The command writes
`kitty-specs/<slug>/mission-review-report.md` with `verdict: pass` and exits 0.

### Scenario 7 — Stalled reviewer surfaced in status

A WP has been in `in_review` with no status event for 45 minutes (above the
30-minute default threshold). Running `spec-kitty agent tasks status` shows
`⚠ STALLED — no move-task in 45m` next to that WP. Running
`spec-kitty next --agent claude` surfaces it as an actionable item with the two
intervention commands.

## Functional Requirements

| ID | Description | Status |
|----|-------------|--------|
| FR-001 | `spec-kitty merge --abort` removes `.kittify/runtime/merge/__global_merge__/lock` when it exists | Accepted |
| FR-002 | `spec-kitty merge --abort` removes `.kittify/merge-state.json` when it exists | Accepted |
| FR-003 | `spec-kitty merge --abort` aborts any in-progress git merge (equivalent to `git merge --abort` when git is in a merging state) | Accepted |
| FR-004 | Every step of `spec-kitty merge --abort` is idempotent — the command exits 0 whether or not each artifact was present | Accepted |
| FR-005 | `move-task <WP> --to approved --force` checks the most recent `review-cycle-N.md` for that WP; if `verdict: rejected` is found, the command prints a named warning and exits non-zero | Accepted |
| FR-006 | `move-task <WP> --to approved --force --skip-review-artifact-check` bypasses the rejected-verdict check and proceeds | Accepted |
| FR-007 | `move-task <WP> --to done --force` applies the same rejected-verdict check as FR-005 | Accepted |
| FR-008 | `spec-kitty agent tasks status` emits a per-WP warning when a WP in `approved` or `done` lane has a most-recent `review-cycle-N.md` with `verdict: rejected` | Accepted |
| FR-009 | The verdict field in `review-cycle-N.md` is validated against the enumerated set: `approved`, `approved_after_orchestrator_fix`, `arbiter_override`, `rejected` | Accepted |
| FR-010 | The lane guard error message names the `planning_base_branch` and includes a `git show <planning-branch>:kitty-specs/` command example | Accepted |
| FR-011 | The WP review checklist template in the software-dev mission command-templates includes a "deletion test" item under error-path test coverage | Accepted |
| FR-012 | All `# noqa: BLE001` suppressions in `src/specify_cli/auth/` and `src/specify_cli/cli/commands/` either have an inline justification comment or are removed and replaced with explicit exception propagation | Accepted |
| FR-013 | `spec-kitty review --mission <slug>` verifies all WPs for the named mission are in `done` lane; exits non-zero with a list of non-done WPs if not | Accepted |
| FR-014 | `spec-kitty review --mission <slug>` checks for new public functions and classes introduced in the mission diff that have no non-test callers in `src/`; flags each one | Accepted |
| FR-015 | `spec-kitty review --mission <slug>` checks for `# noqa: BLE001` suppressions in `src/specify_cli/auth/` and `src/specify_cli/cli/commands/` that lack inline justification text; flags each one | Accepted |
| FR-016 | `spec-kitty review --mission <slug>` writes `kitty-specs/<slug>/mission-review-report.md` containing `verdict` (`pass` / `pass_with_notes` / `fail`), `reviewed_at` (ISO timestamp), and `findings` count | Accepted |
| FR-017 | The kanban status board displays `⚠ STALLED — no move-task in Xm` next to any WP in `in_review` lane whose most recent status event is older than the stall threshold (default 30 minutes) | Accepted |
| FR-018 | `spec-kitty next --agent <name>` surfaces stalled `in_review` WPs as actionable items with the two intervention commands (force-approve and reject-with-feedback) | Accepted |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | All new CLI commands (FR-013 through FR-016) have at least one integration test | 100% of new commands covered | Accepted |
| NFR-002 | Line coverage for all new and modified source files | ≥90% | Accepted |
| NFR-003 | The stall detection threshold is operator-configurable via `.kittify/config.yaml` under `review.stall_threshold_minutes` | Default 30; any positive integer accepted | Accepted |
| NFR-004 | `spec-kitty merge --abort` completes in under 2 seconds regardless of filesystem state | ≤2 seconds wall time | Accepted |
| NFR-005 | `spec-kitty review --mission` completes in under 10 seconds for a mission with fewer than 20 WPs and a diff of fewer than 5,000 lines | ≤10 seconds | Accepted |

## Constraints

| ID | Description | Status |
|----|-------------|--------|
| C-001 | Template changes must be made to `src/specify_cli/missions/*/command-templates/` only — generated agent copies under `.claude/commands/`, `.amazonq/prompts/`, and other agent directories must not be edited | Accepted |
| C-002 | Status events in `status.events.jsonl` are append-only; no existing event lines may be mutated by any code in this mission | Accepted |
| C-003 | `mission_id` (ULID) is canonical identity in all new code; `mission_number` is display-only and must not be used for lookup, locking, or routing | Accepted |
| C-004 | All modified Python files must pass `mypy --strict` with zero errors | Accepted |
| C-005 | The stall detection for FR-017 and FR-018 is read-only; no new state is written to disk as part of the stall check | Accepted |
| C-006 | The `--skip-review-artifact-check` bypass flag from FR-006 must be documented in the CLI `--help` output | Accepted |

## Key Entities

| Entity | Description |
|--------|-------------|
| Lock file | `.kittify/runtime/merge/__global_merge__/lock` — mutex that prevents concurrent merges |
| Merge-state JSON | `.kittify/merge-state.json` — resumable merge progress record |
| Review-cycle artifact | `kitty-specs/<slug>/tasks/<WP-dir>/review-cycle-N.md` — frontmatter-bearing review outcome file; `verdict` is the key field |
| Status event log | `kitty-specs/<slug>/status.events.jsonl` — append-only record of all WP lane transitions |
| Mission review report | `kitty-specs/<slug>/mission-review-report.md` — output of `spec-kitty review --mission` |
| Planning base branch | The main-line branch that holds all planning artifacts; named in lane guard errors |
| Stall threshold | Operator-configurable duration (default 30 min) after which an `in_review` WP with no recent event is flagged |

## Success Criteria

- Operators can recover from a crashed merge by running `spec-kitty merge --abort` without manual filesystem cleanup, 100% of the time
- Force-approving a WP with a rejected verdict is blocked by default; zero silent inconsistencies reach the `done` lane
- Lane guard errors contain enough context that a reviewer can locate planning artifacts in one additional command without asking for help
- Every WP review checklist includes an explicit error-path reachability check, reducing the class of "tests pass but implementation is untested" bugs reaching review
- All `# noqa: BLE001` suppressions in auth and CLI command code carry an inline justification, making security audits faster
- Operators have a single CLI command to confirm a merged mission is clean before cutting a release
- Stalled review agents are surfaced within the first `spec-kitty agent tasks status` or `spec-kitty next` invocation after the stall threshold is crossed

## Assumptions

- The lock file constant `__global_merge__` is already defined somewhere in `src/specify_cli/merge/` (likely `executor.py`) and does not need to be changed
- The `baseline_merge_commit` field in `meta.json` is populated for all missions created after the mission identity migration (083); missions without it will produce a warning from the review command rather than a hard failure
- The `review.stall_threshold_minutes` config key does not currently exist in `.kittify/config.yaml`; it will be added as an optional key with a default of 30
- Option A (warn + block on force-approve) is chosen for FR-005 rather than Option B (auto-update verdict); this preserves human oversight
- Option A (per-file-ignores + inline comments) is chosen for FR-012 rather than a custom ruff rule; this is sufficient for the documented use case and avoids plugin complexity

## Open Questions

None — all decisions resolved during discovery.

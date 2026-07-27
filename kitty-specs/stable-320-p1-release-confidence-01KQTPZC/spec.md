# Stable 3.2.0 P1 Release Confidence

**Mission ID**: `01KQTPZCNQT0M1G3P1YFN2SE86`
**Mission slug**: `stable-320-p1-release-confidence-01KQTPZC`
**Mission type**: `software-dev`
**Status**: Draft
**Target branch**: `main`
**Planning/base branch**: `main`
**Created**: 2026-05-05
**Input source**: `../start-here.md`
**Scoped issues**: #966, #848

---

## Primary Intent

Prepare the Spec Kitty CLI for stable `3.2.0` by closing the remaining high-confidence P1 release-readiness gaps after PR #972, without reopening closed P0 blockers or expanding into broad hygiene work.

PR #972 already closed the prior P0 blockers #967, #904, #968, and #964. Those issues must not be scheduled again unless the mission produces a fresh current regression. Issue #869 is stale because `uv run ruff check src tests` passes on current `main`; it should remain out of scope unless a fresh repro appears.

This mission covers three release-readiness outcomes:

- #966: task-board progress semantics must be internally consistent.
- #848: installed dependency versions must be verified against the lockfile, or current gates must be proven sufficient to close the issue with evidence.
- Fresh end-to-end workflow smoke must run once local-only and once with SaaS sync enabled where hosted, tracker, auth, or sync paths are touched.

The mission must also record whether #971, the strict mypy gate failure reported from #972 evidence, is included or deferred. By default, #971 is a known follow-up and not part of this P1 tranche unless explicitly pulled into scope by plan review.

## User Scenarios & Testing

### Primary actors

| Actor | Description |
|---|---|
| CLI operator | Runs Spec Kitty mission, status, review, merge, and smoke commands while preparing a stable release. |
| Agent orchestrator | Reads task-board and workflow status to decide whether WPs are ready, done, blocked, or still pending. |
| Release maintainer | Needs trustworthy evidence that the prerelease line is stable enough to cut `3.2.0`. |
| Reviewer | Checks whether dependency environment evidence and workflow smoke results are strong enough to close or defer release issues. |

### Scenario 1 - Approved work is not reported with contradictory progress

**Given** all WPs are approved and none are done, **when** the operator runs task status, **then** the displayed numerator, denominator, percentage, and label describe the same concept instead of showing a done-only numerator beside a ready-work percentage.

### Scenario 2 - Done, approved, mixed, and empty boards stay consistent

**Given** a task board has all done WPs, all approved WPs, mixed approved and done WPs, or no completed progress, **when** human-readable or touched machine-readable status output is rendered, **then** every progress value remains parseable and internally consistent.

### Scenario 3 - Dependency drift is verified before release evidence is trusted

**Given** review or release evidence can be misleading when the installed environment differs from `uv.lock`, **when** the mission evaluates #848, **then** it first determines whether current CI or review gates already detect drift for `spec-kitty-events` and records evidence for closure or implements a focused guard.

### Scenario 4 - Operators receive a clear remediation path for dependency drift

**Given** an installed critical Spec Kitty package version does not match the resolved lockfile, **when** the guard or verification path reports the mismatch, **then** the operator sees the mismatched package and a remediation command that returns the environment to the locked dependency set.

### Scenario 5 - Full workflow smoke passes locally

**Given** the current prerelease line after PR #972, **when** the operator runs a fresh local-only Spec Kitty lifecycle smoke, **then** the smoke covers setup, specify, plan, tasks, implement/review or a bounded equivalent fixture path, merge, and PR-ready evidence without requiring hosted auth, tracker, or sync.

### Scenario 6 - Full workflow smoke passes with SaaS sync enabled where required

**Given** this computer's testing rule requires SaaS sync for hosted, tracker, auth, or sync paths, **when** the operator runs the SaaS-enabled smoke, **then** every command touching those paths sets `SPEC_KITTY_ENABLE_SAAS_SYNC=1` and the evidence names the hosted/sync coverage achieved.

### Scenario 7 - Release evidence distinguishes included work from deferrals

**Given** P2/P3 issues and #971 are known but not automatically in scope, **when** the mission reaches acceptance, **then** release evidence clearly identifies what was fixed, what was verified, what was deferred, and whether any smoke failure blocks stable `3.2.0`.

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Task-board progress output must use consistent numerator, denominator, percentage, and labels across approved, done, mixed, and empty states. | Draft |
| FR-002 | If task progress uses a done-only numerator, the percentage must also be done-only; if the percentage includes approved or ready work, the label must explicitly name readiness, such as `ready`, `approved`, or an equivalent unambiguous term. | Draft |
| FR-003 | Regression coverage must include all WPs approved with none done, all WPs done, mixed approved and done, and no progress. | Draft |
| FR-004 | Any JSON or other machine-readable status output touched by the progress change must remain parseable and internally consistent with the human-readable semantics. | Draft |
| FR-005 | The mission must verify whether current CI or review automation already catches installed-vs-lock drift for `spec-kitty-events`. | Draft |
| FR-006 | If current gates fully cover #848, the mission must produce evidence suitable for closing #848 without code changes. | Draft |
| FR-007 | If current gates do not fully cover #848, the mission must add or harden a focused automated guard or review command that detects installed-vs-lock drift before release or review evidence relies on the environment. | Draft |
| FR-008 | Dependency drift verification must include `spec-kitty-events`; it may include `spec-kitty-tracker` only if the same drift risk is present and the added scope remains small. | Draft |
| FR-009 | Any dependency drift failure must name the mismatched package, installed version, lockfile version, and an operator remediation path using the repo convention around `uv sync --extra test --extra lint`. | Draft |
| FR-010 | The mission must run and document one fresh local-only end-to-end workflow smoke on the current prerelease line. | Draft |
| FR-011 | The mission must run and document one fresh SaaS-enabled end-to-end workflow smoke with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on every hosted auth, tracker, SaaS, or sync command path. | Draft |
| FR-012 | Each smoke must cover init or project setup, specify, plan, tasks, implement/review or a bounded equivalent fixture path, merge, and PR creation or PR-ready branch evidence. | Draft |
| FR-013 | Any smoke failure must result in a linked GitHub issue, a narrow fix inside this mission, or an explicit stable-release blocker decision. | Draft |
| FR-014 | The mission must explicitly record #971 as included or deferred; it must not leave the strict mypy gate ambiguous. | Draft |
| FR-015 | Final release evidence must include current `uv run ruff check src tests` status. | Draft |

## Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-001 | Each included issue or smoke path must have focused evidence that a reviewer can inspect without reconstructing the mission history. | Draft |
| NFR-002 | Default tests must be local and deterministic; hosted auth, tracker, SaaS, or sync tests require `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this computer. | Draft |
| NFR-003 | The change set must stay small enough for release stabilization, preferring focused fixes, verification scripts, and documentation over broad refactors. | Draft |
| NFR-004 | The mission must not degrade PR #972 guarantees around status boundedness, review verdict consistency, checklist retirement, or generated skill frontmatter. | Draft |
| NFR-005 | If #971 is included, final evidence must include `uv run mypy --strict src/specify_cli src/charter src/doctrine`; if deferred, final evidence must link #971 and explain why it remains outside this mission. | Draft |
| NFR-006 | New or changed status output must stay understandable to humans and stable for automation that consumes JSON or machine-readable forms. | Draft |
| NFR-007 | New code must satisfy the project charter expectations for focused pytest coverage and strict type quality where applicable to touched files. | Draft |

## Constraints

| ID | Requirement | Status |
|---|---|---|
| C-001 | Implementation scope is limited to #966, #848, fresh local and SaaS-enabled workflow smoke evidence, and release evidence/deferral recording. | Draft |
| C-002 | Prior P0 issues #967, #904, #968, and #964 must not be scheduled unless a current regression is reproduced. | Draft |
| C-003 | Issue #869 must not be scheduled unless a fresh repro appears, because current `uv run ruff check src tests` passes on `main`. | Draft |
| C-004 | Issue #971 must remain a separate WP only if explicitly included; otherwise it must be documented as a known open release-gate follow-up. | Draft |
| C-005 | P2 issues #662, #630, #629, and #631 must be deferred unless P1 work directly touches the same files and the fix is small. | Draft |
| C-006 | P3 issues #771, #726, #728, #729, #644, #740, #323, #306, #303, #317, and #973 must be deferred unless a current repro blocks stable release. | Draft |
| C-007 | The mission must not loosen the dependency constraint in `pyproject.toml` as a substitute for detecting environment drift. | Draft |
| C-008 | The canonical product term is Mission; new active-system language must not introduce or preserve legacy domain-object aliases. | Draft |

## Key Entities

| Entity | Definition |
|---|---|
| Mission | The canonical unit of Spec Kitty work moving through specify, plan, tasks, implement, review, accept, and merge. |
| Work Package (WP) | A planned task package whose lane, approval, and done state contribute to release readiness. |
| Task board progress | Human-readable and machine-readable status that communicates WP readiness and completion. |
| Done progress | Progress based only on WPs that have reached the done lane. |
| Ready progress | Progress that includes approved WPs or other ready-for-completion states and must be labeled as readiness. |
| Lockfile drift | A mismatch between the installed package version used by release evidence and the version resolved in `uv.lock`. |
| Local-only smoke | A full workflow smoke that avoids hosted auth, tracker, SaaS, and sync dependencies. |
| SaaS-enabled smoke | A full workflow smoke where hosted, tracker, auth, or sync paths run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. |
| Release evidence | The collected command outputs, issue decisions, deferrals, and smoke results needed to judge stable `3.2.0` readiness. |

## Success Criteria

| ID | Criterion |
|---|---|
| SC-001 | For approved-only boards, task status no longer shows a contradictory value such as `0/6` beside `80%` unless the label makes the distinction explicit and intentional. |
| SC-002 | Approved-only, done-only, mixed, and empty progress states each have passing regression coverage. |
| SC-003 | Any touched machine-readable status output can be parsed and its progress fields agree with the documented semantics. |
| SC-004 | #848 is either closed with current-gate evidence or protected by a focused drift guard that catches a `spec-kitty-events` installed-vs-lock mismatch. |
| SC-005 | Dependency drift diagnostics include a clear remediation command based on `uv sync --extra test --extra lint`. |
| SC-006 | A fresh local-only workflow smoke completes or produces a documented issue, fix, or stable-release blocker decision. |
| SC-007 | A fresh SaaS-enabled workflow smoke completes with required `SPEC_KITTY_ENABLE_SAAS_SYNC=1` coverage or produces a documented issue, fix, or stable-release blocker decision. |
| SC-008 | Final evidence includes `uv run ruff check src tests` status and an explicit included/deferred decision for #971. |

## Assumptions

- The user-provided `../start-here.md` brief is authoritative discovery input for this mission.
- The intended branch contract is `main` for current branch, planning/base branch, and final merge target.
- `software-dev` is the correct mission type.
- PR #972 closed #967, #904, #968, and #964 unless this mission finds a fresh regression.
- The current observation that `spec-kitty-events` resolves to `4.1.0` in a fresh `uv run` environment is evidence to verify, not a substitute for the #848 gate decision.
- #971 is deferred by default unless plan review explicitly pulls strict mypy cleanup into this mission as a separate WP.

## Suggested Work Packages

### WP01 Task Board Progress Semantics (#966)

Locate progress/readiness calculation and rendering for `spec-kitty agent tasks status`. Decide and implement consistent done-vs-ready wording, then add focused regression coverage for approved-only, done-only, mixed, empty, and touched JSON or machine-readable output.

### WP02 Dependency Drift Gate (#848)

Inspect CI and review gates for installed-vs-lock coverage. If coverage is sufficient, write closure evidence for #848. If not, add a focused guard for `spec-kitty-events` lock/install drift and document operator remediation.

### WP03 Fresh End-To-End Smoke

Run a local-only full workflow smoke and a SaaS-enabled full workflow smoke. The SaaS-enabled path must use `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on every hosted auth, tracker, SaaS, or sync command path.

### WP04 Release Evidence And Deferrals

Compile release evidence for #966, #848, both smoke runs, current ruff status, #971 included/deferred status, and P2/P3 deferrals.

## Verification Guidance

Start from these commands and adjust only with justification based on touched files:

```bash
uv run ruff check src tests
uv run pytest tests/status tests/specify_cli/cli/commands/agent -q
uv run pytest tests/contract tests/review tests/post_merge -q
```

For fresh smoke evidence, the mission plan must write the exact command sequence based on current CLI surfaces:

```bash
# Local-only smoke: no hosted auth, tracker, SaaS, or sync dependency.

# SaaS-enabled smoke: every hosted auth, tracker, SaaS, or sync command must use:
SPEC_KITTY_ENABLE_SAAS_SYNC=1 <spec-kitty command>
```

If #971 is included, final evidence must also include:

```bash
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

# 3.x ADRs

Architectural Decision Records for the 3.x track (starting 3.0.0, released 2026-03-30).

## Naming

- `YYYY-MM-DD-N-descriptive-title-with-dashes.md` where `N` is `1, 2, 3, …` per ADR landed on a given date.

## Source of Truth

This folder is canonical for 3.x decisions. Back-compat symlinks at the old
`architecture/2.x/adr/<filename>` paths point here so legacy references (in
CHANGELOG entries, test snapshots, etc.) continue to resolve.

## Status Conventions

- `Accepted` means the decision remains current policy.
- `Superseded` means a newer ADR replaced the decision; keep the file for history, but do not implement from it.
- `Deprecated` means the direction is in active retirement and should not receive new work.

## Template

Use the shared template at [`../../adr-template.md`](../../adr-template.md).

## Index

| Date | Title |
|---|---|
| 2026-04-03 | [Execution lanes own worktrees and mission branches](2026-04-03-1-execution-lanes-own-worktrees-and-mission-branches.md) |
| 2026-04-03 | [Review approval and integration completion are distinct](2026-04-03-2-review-approval-and-integration-completion-are-distinct.md) |
| 2026-04-03 | [Feature acceptance runs on the integrated mission branch](2026-04-03-3-feature-acceptance-runs-on-the-integrated-mission-branch.md) |
| 2026-04-04 | [Tracker binding context is discovered, not user-supplied](2026-04-04-1-tracker-binding-context-is-discovered-not-user-supplied.md) |
| 2026-04-04 | [Mission type, mission, and mission run terminology boundary](2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md) |
| 2026-04-06 | [WP state pattern for lane behavior](2026-04-06-1-wp-state-pattern-for-lane-behavior.md) |
| 2026-04-07 | [Global slash command installation](2026-04-07-1-global-slash-command-installation.md) |
| 2026-04-09 | [Mission identity uses ULID, not sequential prefix](2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md) |
| 2026-04-09 | [CLI SaaS auth is browser-mediated OAuth, not password](2026-04-09-2-cli-saas-auth-is-browser-mediated-oauth-not-password.md) |
| 2026-04-11 | [SaaS rollout and readiness](2026-04-11-1-saas-rollout-and-readiness.md) |
| 2026-04-15 | [Explicit empty charter selections remain empty](2026-04-15-2-explicit-empty-charter-selections-remain-empty.md) |
| 2026-04-19 | [CLI auth uses encrypted file-only session storage](2026-04-19-1-cli-auth-uses-encrypted-file-only-session-storage.md) |
| 2026-04-19 | [Ticket delivery is CLI plumbing; specification is LLM content](2026-04-19-2-ticket-delivery-is-cli-plumbing-specification-is-llm-content.md) |
| 2026-04-20 | [Mutation testing as a local-only quality gate](2026-04-20-1-mutation-testing-as-local-only-quality-gate.md) |
| 2026-04-21 | [Private teamspace and repository sharing boundary](2026-04-21-1-private-teamspace-and-repository-sharing-boundary.md) |
| 2026-04-25 | [Shared package boundary cutover](2026-04-25-1-shared-package-boundary.md) |
| 2026-04-26 | [Contract pinning resolved version](2026-04-26-1-contract-pinning-resolved-version.md) |
| 2026-04-26 | [Auth transport boundary](2026-04-26-2-auth-transport-boundary.md) |
| 2026-04-26 | [E2E hard gate](2026-04-26-3-e2e-hard-gate.md) |
| 2026-04-27 | [Retrospective gate shared module](2026-04-27-1-retrospective-gate-shared-module.md) |
| 2026-05-01 | [Atomic work-package start lifecycle](2026-05-01-1-atomic-work-package-start-lifecycle.md) |
| 2026-05-10 | [Deterministic historical mission-state repair](2026-05-10-1-deterministic-historical-mission-state-repair.md) |
| 2026-05-14 | [Stale-lane auto-rebase classifier policy](2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md) |
| 2026-05-16 | [Doctrine layer merge semantics](2026-05-16-1-doctrine-layer-merge-semantics.md) |

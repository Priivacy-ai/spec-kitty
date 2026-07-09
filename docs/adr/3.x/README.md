# 3.x ADRs

Architectural Decision Records for the 3.x track (starting 3.0.0, released 2026-03-30).

## Naming

- `YYYY-MM-DD-N-descriptive-title-with-dashes.md` where `N` is `1, 2, 3, …` per ADR landed on a given date.

After adding an ADR file, run `python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<your-adr>.md`
to update the page-inventory lockfile and add the row to the index table below.

## Source of Truth

This folder is canonical for 3.x decisions. The `architecture/` tree was removed
by the Common Docs structural move (PR #2225); existing references using the old
`architecture/2.x/adr/<filename>` paths will need updating to `docs/adr/3.x/`.

## Status Conventions

- `Accepted` means the decision remains current policy.
- `Superseded` means a newer ADR replaced the decision; keep the file for history, but do not implement from it.
- `Deprecated` means the direction is in active retirement and should not receive new work.

## Template

Use the shared template at [`docs/architecture/adr-template.md`](../../architecture/adr-template.md).

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
| 2026-05-19 | [Retrospective default-on policy architecture](2026-05-19-1-retrospective-default-policy-architecture.md) |
| 2026-05-24 | [Charter freshness UX contract](2026-05-24-1-charter-freshness-ux-contract.md) |
| 2026-05-24 | [Pack augmentation vocabulary — `overrides` and `enhances` as declarative fields](2026-05-24-2-pack-augmentation-vocabulary.md) |
| 2026-05-24 | [`shipped` → `built-in` vocabulary cutover for doctrine layer label](2026-05-24-3-shipped-to-built-in-cutover.md) |
| 2026-06-02 | [Pi agent is skill-only: no prompt templates, invoker deferred](2026-06-02-1-pi-agent-skill-only-support.md) |
| 2026-06-02 | [Letta agent is skill-only: no slash-command templates, invoker and session model deferred](2026-06-02-2-letta-agent-skill-only-support.md) |
| 2026-06-03 | [Execution-state domain model](2026-06-03-1-execution-state-domain-model.md) |
| 2026-06-03 | [ExecutionContext owner and CommitTarget atomicity](2026-06-03-2-executioncontext-owner-and-committarget.md) |
| 2026-06-03 | [Effector/Actor model](2026-06-03-3-effector-actor-model.md) |
| 2026-06-05 | [Merge publish-layer boundary](2026-06-05-1-merge-publish-layer-boundary.md) |
| 2026-06-06 | [Plan concerns to work package traceability](2026-06-06-1-plan-concerns-to-work-package-traceability.md) |
| 2026-06-07 | [Execution-state canonical surface (`mission_runtime`)](2026-06-07-1-execution-state-canonical-surface.md) |
| 2026-06-07 | [Session presence: multi-harness architecture](2026-06-07-1-session-presence-multi-harness-architecture.md) |
| 2026-06-07 | [WP lane FSM, the `genesis` lane, and the finalize event-log clobber fix](2026-06-07-1-wp-lane-fsm-genesis-and-finalize-clobber.md) |
| 2026-06-11 | [Op as a first-class execution artifact (Mission ⟷ Op ⟷ ad-hoc)](2026-06-11-1-op-as-first-class-execution-artifact.md) |
| 2026-06-15 | [Marketplace descriptor vs publish](2026-06-15-1-marketplace-descriptor-vs-publish.md) |
| 2026-06-19 | [A materialized-but-empty coordination worktree hard-fails — no silent primary fallback](2026-06-19-1-coord-empty-surface-fallback.md) |
| 2026-06-21 | [Protected-branch configuration is a standalone boundary-resolved value, not a nested context sub-object](2026-06-21-1-protected-branch-config-boundary-resolved-value.md) |
| 2026-06-22 | [MissionTopology SSOT — store the mission shape, resolve it once](2026-06-22-1-mission-topology-ssot.md) |
| 2026-06-24 | [Kind- and topology-aware artifact placement — one partition, read/write symmetry](2026-06-24-1-kind-and-topology-aware-artifact-placement.md) |
| 2026-06-24 | [Write-branch resolution anchors `meta.json` on the PRIMARY surface (write-surface twin)](2026-06-24-2-write-branch-resolution-primary-anchor.md) |
| 2026-06-25 | [Terminal-artifact durable home + topology-aware teardown contract](2026-06-25-1-terminal-artifact-durable-home-teardown.md) |
| 2026-06-26 | [Single-authority seam + call-site gate for resolution boundaries (Phase 1)](2026-06-26-1-single-authority-seam-and-call-site-gate.md) |
| 2026-07-01 | [No legacy-compat branches in resolvers — require canonical identity, migrate legacy](2026-07-01-1-no-legacy-compat-branches-in-resolvers.md) |
| 2026-07-08 | [MissionResolver Port — One Walk Trunk, Shell-Side DI, No Shared Container](2026-07-08-1-mission-resolver-port.md) |

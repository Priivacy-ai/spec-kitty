# TeamSpace Mission-State History Repair Coordination

## Overview

Before TeamSpace public launch, every active Spec Kitty repository must have
its historical mission-state data audited, deterministically repaired, and
dry-run validated against the current event contract. This mission coordinates
running the `doctor mission-state` pipeline across `spec-kitty`,
`spec-kitty-saas`, and `spec-kitty-events`, landing a standalone repair commit
per repo, and closing issue #979.

## Goals

- Achieve zero TeamSpace blockers across all selected active repositories before
  public launch.
- Produce a deterministic, reviewable repair manifest for each repo.
- Validate all repair output against `spec-kitty-events==5.0.0` before any
  PR is raised.
- Close `spec-kitty#979` with evidence and reassess `spec-kitty#920`.

## Non-Goals

- **NG-1**: This mission does not implement new CLI features. All required
  repair tooling (PR #1017, merged 2026-05-11) is already shipped.
- **NG-2**: This mission does not backfill historical missions in
  `spec-kitty-runtime` unless the runtime audit reveals TeamSpace blockers
  (decision deferred to WP01 scope confirmation).
- **NG-3**: This mission does not perform live TeamSpace imports; dry-run
  validation is the terminal step.
- **NG-4**: This mission does not rewrite existing valid canonical IDs.

## Decisions

- **D-1**: Target branch for all repair commits is `main` in each repo, via a
  dedicated `repair/teamspace-mission-state-history` branch per repo.
- **D-2**: `spec-kitty-runtime` is included only if its audit reveals
  `missions_with_teamspace_blockers > 0`; the side-log classifier (PR #19)
  is already merged and runtime repair is likely unnecessary.
- **D-3**: PR #1017 ("Close mission-state migration readiness gaps") must be
  merged before running `--fix`; it is confirmed merged as of 2026-05-11.
- **D-4**: Repair is executed with `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on this
  machine for any command that touches SaaS, tracker, sync, or TeamSpace
  behavior.

## Assumptions

- `spec-kitty doctor mission-state` (audit/fix/teamspace-dry-run) is
  available and functional on the installed version (v3.2.0rc4).
- Contributors are available to pause `kitty-specs/` edits during the repair
  window per WP01 coordination.
- `spec-kitty-events==5.0.0` is the required package version for envelope
  validation; the CLI will validate against this at dry-run time.

## Actors

- **Release operator** (primary): runs the audit, repair, and dry-run
  commands; reviews manifests; raises repair PRs.
- **Contributors** (secondary): pause `kitty-specs/` edits during the repair
  window; review repair PRs.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The operator can run `spec-kitty doctor mission-state --audit --json` in each target repo and receive a machine-readable JSON report containing: total missions, missions with TeamSpace blockers, blocker counts by code, and unexpected non-repairable errors. | Approved |
| FR-002 | The audit report from FR-001 is saved as `../<repo>.before.audit.json` relative to each repo's parent directory before any repair is run. | Approved |
| FR-003 | The operator can run `spec-kitty doctor mission-state --fix` in each target repo and have it produce a migration manifest under `.kittify/migrations/mission-state/`. | Approved |
| FR-004 | The repair manifest includes: repo HEAD commit hash, checksums of affected files, row transformation counts, quarantine counts, and validation results. | Approved |
| FR-005 | Existing valid canonical IDs are not rewritten by `--fix`. | Approved |
| FR-006 | Generated IDs in the repair output are deterministic from documented seed material (same repo state → same repair output in any clone). | Approved |
| FR-007 | Legacy `feature_slug`, `feature_number`, `mission_key`, `legacy_aggregate_id`, and `work_package_id` shapes are removed from TeamSpace-bound historical status rows. | Approved |
| FR-008 | Any quarantined rows are listed explicitly and reviewable before the repair PR is raised. | Approved |
| FR-009 | The operator can run `spec-kitty doctor mission-state --audit --json` post-repair and obtain `missions_with_teamspace_blockers == 0` and `teamspace_blockers == 0` for each repo. | Approved |
| FR-010 | The operator can run `spec-kitty doctor mission-state --teamspace-dry-run --json` post-repair and have TeamSpace dry-run succeed (no validation errors) for each repo. | Approved |
| FR-011 | Dry-run output envelopes validate against `spec-kitty-events==5.0.0` (no schema violations). | Approved |
| FR-012 | Runtime side logs in dry-run output are reported as skipped side logs, not status transitions. | Approved |
| FR-013 | Each repaired repo has exactly one standalone repair commit on a branch named `repair/teamspace-mission-state-history`. | Approved |
| FR-014 | The repair PR body for each repo includes: baseline audit summary, post-repair audit summary, dry-run command and result, manifest path, and links to `spec-kitty#979` and `spec-kitty#920`. | Approved |
| FR-015 | Post-merge: re-run audits from fresh clean checkouts of each repo; confirm zero TeamSpace blockers in each. | Approved |
| FR-016 | `spec-kitty#979` is closed with a comment containing the full evidence table from FR-015. | Approved |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Audit command completes within a reasonable time per repo. | < 5 minutes per repo for a repo with ≤ 300 missions | Approved |
| NFR-002 | Repair is idempotent: running `--fix` twice on the same repo produces the same output without creating duplicate artifacts or erroring. | Zero duplicates, zero errors on second run | Approved |
| NFR-003 | Post-repair audit confirms zero TeamSpace blockers across all selected active repos. | `missions_with_teamspace_blockers == 0` in every repo | Approved |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Repair must be run from a clean git working tree for relevant paths (no dirty `kitty-specs/` or `.kittify/migrations/` paths), unless `--allow-dirty` is explicitly passed. | Approved |
| C-002 | No random IDs or wall-clock timestamps in deterministic repair output. | Approved |
| C-003 | No broad `git add -A` in the repair commit; only repair-affected paths are staged. | Approved |
| C-004 | PR #1017 must be merged before `--fix` is run. Confirmed merged 2026-05-11. | Approved |
| C-005 | All commands on this machine that touch SaaS, tracker, sync, hosted auth, or live TeamSpace sync behavior must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. | Approved |
| C-006 | `spec-kitty-runtime` is included in the repair scope only if its baseline audit reveals TeamSpace blockers. | Approved |

## Success Criteria

1. Every selected active repo (`spec-kitty`, `spec-kitty-saas`, `spec-kitty-events`) has a merged repair commit on `repair/teamspace-mission-state-history`.
2. Fresh clean-checkout audits of each repo show `missions_with_teamspace_blockers == 0`.
3. TeamSpace dry-run passes (no validation errors) in every selected repo.
4. Migration manifests exist, were reviewed, and are referenced in each repair PR.
5. `spec-kitty#979` is closed with evidence comment.
6. `spec-kitty#920` parent epic has been re-assessed and its child checklist updated.

## User Scenarios & Testing

### Primary scenario: end-to-end repair in spec-kitty repo
1. Operator pulls `main` in `spec-kitty` (with PR #1017 merged).
2. Operator runs baseline audit, saves JSON report.
3. Operator runs `--fix`; reviews manifest under `.kittify/migrations/mission-state/`.
4. Operator runs post-repair audit; confirms zero blockers.
5. Operator runs dry-run; confirms envelopes pass validation.
6. Operator commits repair artifacts on a `repair/teamspace-mission-state-history` branch and raises a PR.
7. PR is reviewed and merged.
8. Operator re-runs audit from a fresh clean checkout; confirms zero blockers remain.

### Edge case: quarantine
- If `--fix` quarantines one or more rows, the operator reviews the quarantine list before raising the PR. Quarantine must be explicit and documented in the PR body.

### Edge case: spec-kitty-runtime inclusion
- If `spec-kitty-runtime` baseline audit shows `missions_with_teamspace_blockers > 0`, it is added to the repair scope and the same WP02–WP05 cycle is run for it.

## Domain Language

| Canonical term | Definition | Avoid |
|----------------|------------|-------|
| TeamSpace blocker | A condition in historical mission-state data that would prevent successful TeamSpace import | "blocker" (ambiguous), "error" |
| Mission-state repair | The deterministic process of auditing and fixing legacy status rows via `doctor mission-state --fix` | "migration", "cleanup" |
| Dry-run | Running `doctor mission-state --teamspace-dry-run` to synthesize and validate TeamSpace envelopes without network I/O | "preview", "test import" |
| Repair manifest | The file written to `.kittify/migrations/mission-state/` containing checksums, row counts, and validation results | "migration manifest", "audit log" |

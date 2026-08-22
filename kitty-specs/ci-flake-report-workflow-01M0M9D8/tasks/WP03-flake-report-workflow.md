---
work_package_id: WP03
title: Flake-report CI workflow (weekly + on-demand, artifact delta lineage, retention)
dependencies:
- WP02
requirement_refs:
- FR-006
- FR-007
- FR-014
- NFR-002
- C-001
- C-002
- C-004
- C-006
planning_base_branch: qa/test-hardening
merge_target_branch: qa/test-hardening
branch_strategy: Planning artifacts for this mission were generated on qa/test-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into qa/test-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
history: []
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/
create_intent:
- .github/workflows/ci-flake-report.yml
execution_mode: code_change
owned_files:
- .github/workflows/ci-flake-report.yml
tags: []
tracker_refs: []
---

# WP03 — Flake-report CI workflow

**Capability A** · profile: implementer-ivan · deps: WP02 · refs: FR-006, FR-007, FR-014, NFR-002, C-001, C-002, C-004, C-006

## Objective

Add `.github/workflows/ci-flake-report.yml` — a **weekly** (`schedule` cron) + **on-demand** (`workflow_dispatch`) job that runs `flake_report.py`, retrieves the prior state artifact for the incremental delta, and uploads the findings. Non-gating, artifacts-only.

## Subtasks

- **T010 — Triggers + auth (FR-007/C-004).** `schedule: cron` (weekly, non-colliding slot) + `workflow_dispatch` (optional `--workflow`/`--since` inputs). `permissions: { actions: read, contents: read }`. `GH_TOKEN: ${{ github.token }}`. Mirror repo idioms (checkout@v6, setup-uv, `uv python install 3.11`, `blacksmith-4vcpu-ubuntu-2404`).
- **T011 — Delta lineage (FR-007/C-006).** Retrieve prior `state.json` by a **stable artifact name** independent of the workflow display name (`gh run download` from the last successful run, keyed on that stable name); schema-validate; on missing/corrupt → 30-day fallback (label lost_baseline). Never regress the cursor on manual dispatch backfill.
- **T012 — Upload (FR-006).** `actions/upload-artifact@v7` with `retention-days: 90`; upload `metrics.json`/`durations.json`/`report.md`/`state.json`. No commit, no docs changes.

## Constraints

- **C-002:** must NOT be a required status check; never in branch-protection contexts.
- Keep it off the PR path (no `pull_request` trigger).

## Done when

Workflow validates (yaml + `workflow_dispatch` dry sense-check), produces the four artifacts on a manual dispatch, and reads its own prior artifact for the delta on a second run.

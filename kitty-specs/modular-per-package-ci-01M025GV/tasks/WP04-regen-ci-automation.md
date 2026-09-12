---
work_package_id: WP04
title: Trust-tiered regen CI automation
dependencies:
- WP02
requirement_refs:
- FR-009
- FR-010
- FR-011
- NFR-003
- C-003
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
phase: Phase 2 - Automation
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: .github/workflows/regen-assets.yml
create_intent:
- .github/workflows/regen-assets.yml
- tests/architectural/test_regen_assets_workflow.py
execution_mode: code_change
owned_files:
- .github/workflows/regen-assets.yml
- tests/architectural/test_regen_assets_workflow.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Trust-tiered regen CI automation

**Implements**: FR-009, FR-010, FR-011; NFR-003; C-003. IC-04. **Depends on WP02** (the tool must exist).

## Goal

Wire `spec-kitty regen` into CI with three trust tiers, modeled on `all-contributors-normalize.yml`.

## Scope

- NEW `.github/workflows/regen-assets.yml`:
  - **Same-repo push / `workflow_dispatch`**: run `spec-kitty regen`, and if the tree is dirty, commit back with
    bot identity (`github-actions[bot]`) and `permissions: contents: write` — copy the guard + push block from
    `all-contributors-normalize.yml:18`, `:63-74`.
  - **Fork PR** (`head.repo.full_name != github.repository`): run `spec-kitty regen --check` only; fail with the
    followable message; never attempt a push (C-003).
  - **`regen` label on a fork PR**: privileged `pull_request_target` job that regenerates and pushes into the
    fork branch via a least-privilege maintainer PAT — running ONLY base-repo tooling over PR data (never
    PR-supplied code). Ship this path **disabled/guarded** until the NFR-003 security sign-off is recorded.
- Reuse the in-repo fork-detection idioms (`ci-quality.yml:4247` `IS_FORK_PR`, `:4254` `IS_CANONICAL_REPO`).

## ATDD / red-first (C-008)

- **T001 (RED first)**: a workflow-lint / structural test (in `tests/architectural/`) asserting the same-repo
  guard is present and the fork path is check-only (no push step reachable on fork PRs). RED if absent.
- **T002**: assert the PAT-push job is gated behind the `regen` label AND a canonical-repo/enabled flag, and
  fails closed when the PAT secret is absent (edge case in spec.md).
- **T003**: assert `pull_request_target` runs base-repo tooling only (no checkout-and-execute of PR head code).

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/architectural/ -k "workflow or regen or fork" -q
# Manual: trigger workflow_dispatch on a same-repo branch with stale fixtures; open a fork PR to observe check-only.
```

## Acceptance (SC-006)

- Same-repo drift auto-commits; fork PR drift fails check-only with the exact command; labeled run pushes into
  the fork branch after the NFR-003 sign-off. Security review recorded before the PAT path is enabled.

## Security note (NFR-003)

The PAT-push path is the mission's one privileged surface. It MUST: use `pull_request_target` with trusted
base-repo tooling only; never execute PR-supplied code; use a least-privilege PAT; and remain disabled until a
security review sign-off is recorded on the PR. Call out remaining security-review work explicitly in the PR body.

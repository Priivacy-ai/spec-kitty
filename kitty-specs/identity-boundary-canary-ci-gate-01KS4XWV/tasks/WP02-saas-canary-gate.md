---
work_package_id: WP02
title: spec-kitty-saas canary-gate workflow + README section (cross-repo manifest)
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- FR-009
- FR-010
- NFR-003
- NFR-004
- NFR-005
- C-001
- C-002
- C-003
- C-004
- C-008
planning_base_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
merge_target_branch: kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-identity-boundary-canary-ci-gate-01KS4XWV unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
history:
- at: '2026-05-21T09:34:00Z'
  actor: claude
  action: created
authoritative_surface: kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-saas.md
execution_mode: planning_artifact
mission_slug: identity-boundary-canary-ci-gate-01KS4XWV
owned_files:
- kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-saas.md
priority: P1
status: planned
tags: []
---

# WP02 — spec-kitty-saas: canary-gate workflow + README section (cross-repo)

## Objective

Land a CI workflow + README section in `spec-kitty-saas` gating PRs on the
identity-boundary canary against deployed-dev. This WP owns a manifest in
THIS repo describing the workflow + README content and capturing the PR
URL once opened.

## Coordination

- Coexists with concurrent mission #258 (`sunset-carve-out-constants-01KS4XTA`).
- Disjoint file scope: this WP owns `.github/workflows/canary-gate.yml`
  (distinct from #258's `sunset-check.yml`) and an additive README section.
- Use a dedicated worktree to avoid `git checkout` races:
  ```bash
  git -C /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas \
      worktree add ../spec-kitty-saas-canary-gate origin/main
  ```

## Acceptance

In `spec-kitty-saas`:

- `.github/workflows/canary-gate.yml` with job `canary-gate`, pinned e2e
  SHA `03e4d3c04fcdf641cd564badfbc87bb19a2a0982`, fail-closed missing-secret
  guard, 15-minute timeout. Targets `https://spec-kitty-dev.fly.dev`.
- README has `## Identity-boundary canary CI gate` section.

In this repo:

- `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/spec-kitty-saas.md`
  exists with the canonical YAML, README section text, PR URL, and head SHA.

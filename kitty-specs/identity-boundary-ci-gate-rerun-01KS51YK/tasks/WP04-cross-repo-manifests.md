---
work_package_id: WP04
title: Cross-repo manifests in mission directory
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-005
- FR-006
- C-007
- C-008
planning_base_branch: mission/identity-boundary-ci-gate-rerun
merge_target_branch: mission/identity-boundary-ci-gate-rerun
branch_strategy: Planning artifacts for this mission were generated on mission/identity-boundary-ci-gate-rerun. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/identity-boundary-ci-gate-rerun unless the human explicitly redirects the landing branch.
created_at: '2026-05-21T10:50:00+00:00'
subtasks:
- T013
agent: "claude"
history: []
agent_profile: curator-carla
authoritative_surface: kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/
execution_mode: planning_artifact
owned_files:
- kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty.md
- kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty-events.md
- kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty-saas.md
role: implementer
tags:
- planning-artifact
- cross-repo
- documentation
shell_pid: "85723"
---

## ⚡ Do This First: Load Agent Profile

Before reading the rest of this WP, load the curator profile so you adopt the right identity and boundaries:

- Run the `/ad-hoc-profile-load` skill with profile `curator-carla` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/built-in/curator-carla.agent.yaml`.
- After load, restate your identity, governance scope, and boundaries in one short paragraph before continuing.

## Objective

Document — in this repo's mission directory — what landed in each of the three sibling repos. The manifests reference the live PR URLs that WP01-03 produced, and they cite the exact required-check name a repo admin must register on `main` post-merge.

## Context

- WP01 opened a PR in `Priivacy-ai/spec-kitty` on lane branch `mission/identity-boundary-ci-gate-rerun`.
- WP02 opened a PR in `Priivacy-ai/spec-kitty-events` on lane branch `mission/identity-boundary-ci-gate-events-rerun`.
- WP03 opened a PR in `Priivacy-ai/spec-kitty-saas` on lane branch `mission/identity-boundary-ci-gate-saas-rerun`.
- The exact required-check names are in `contracts/check-names.md`. Manifests reference them, do not redefine them.

## Subtasks

### T013: Author three cross-repo manifests

**Steps**:
1. For each repo, create a manifest at
   `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/<repo>.md`.

   **Template** (use for each):

   ```markdown
   # Cross-Repo Manifest: <repo>

   **Repo**: `Priivacy-ai/<repo>`
   **Lane branch**: `<branch>`
   **PR**: #<num> — <url>
   **Required-check name** (register post-merge): `<name>` (see `../contracts/check-names.md`)

   ## Files landed

   | Path | Status | LOC delta |
   |------|--------|-----------|
   | `.github/workflows/<file>.yml` | NEW | +<n> |
   | `README.md` | MODIFIED | +<n>/-0 |

   ## Admin action required (post-merge)

   1. Open https://github.com/Priivacy-ai/<repo>/settings/branches
   2. Edit the rule for `main`
   3. Under "Require status checks to pass before merging", add the exact name `<name>`
   4. Save

   ## Verification (post-admin-action)

   Open any trivial follow-up PR; confirm the `<name>` check runs and the
   merge button greys out while it's pending. A red check should block
   merge.
   ```

2. Fill in `<branch>`, `<num>`, `<url>`, `<name>`, `<file>`, `<n>` from the
   actual results of WP01-03.
3. Commit on `mission/identity-boundary-ci-gate-rerun`:
   ```bash
   git add kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/
   git commit -m "WP04: cross-repo manifests for identity-boundary-ci-gate-rerun"
   ```

## Files

- `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty.md` — NEW, ~30 lines
- `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty-events.md` — NEW, ~30 lines
- `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/spec-kitty-saas.md` — NEW, ~30 lines

## Validation

- [ ] Three manifest files exist.
- [ ] Each cites the actual PR URL (not `TBD`).
- [ ] Each cites the required-check name verbatim from `contracts/check-names.md`.
- [ ] Each cites the admin URL for the repo's branch-protection settings.
- [ ] No edits to files outside `kitty-specs/identity-boundary-ci-gate-rerun-01KS51YK/cross-repo-manifests/`.

## Edge cases / risks

- **WP01-03 not yet merged at WP04 time**: that's expected. The
  manifests reference PR URLs, not merged commits.
- **PR numbers unknown**: WP04 strictly depends on WP01-03 reaching
  `done` (with PR opened). The implement-review loop enforces the
  dependency.

## Definition of Done

- All three manifests created and committed.
- Each PR URL is live (not `TBD`).
- WP moves to `for_review` via `spec-kitty next`.

## Reviewer guidance

Reviewer checks:
- Three files exist.
- PR URLs resolve (manual click-through).
- Required-check names match `contracts/check-names.md` character-for-character.
- No drift into other parts of the mission directory.

## Activity Log

- 2026-05-21T11:06:54Z – claude – shell_pid=85723 – Started implementation via action command
- 2026-05-21T11:07:39Z – claude – shell_pid=85723 – Three manifests created with live PR URLs (#1267/#36/#264)

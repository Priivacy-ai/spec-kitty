# Implementation Plan: Identity Boundary Canary CI Gate

**Mission**: identity-boundary-canary-ci-gate-01KS4XWV
**Date**: 2026-05-21
**Spec**: [spec.md](spec.md)
**Tracking issue**: [Priivacy-ai/spec-kitty#1247](https://github.com/Priivacy-ai/specs-kitty/issues/1247)

## Summary

Add three GitHub Actions workflows (one per repo) and three README sections
(one per repo) that pin the identity-boundary canary as a required CI check.
The workflows in `spec-kitty-saas` and `spec-kitty-events` clone
`spec-kitty-end-to-end-testing` at SHA
`03e4d3c04fcdf641cd564badfbc87bb19a2a0982` and run, respectively, the
canary script in `--single` mode and the harness identity-boundary unit
tests. The workflow in `spec-kitty` runs the existing drift-detector test
class as a dedicated, named job. Each PR carries an "Action required from
repo admin" block instructing a human admin to add the job's status check
to the branch-protection rule.

## Technical Context

**Language/Version**: YAML for GitHub Actions workflows; Markdown for
README sections. No Python, TypeScript, or shell-script changes. The
canary script (Bash) is referenced as-is.
**Primary Dependencies**:
- `actions/checkout@v6` (sibling repo clone at pinned SHA).
- `astral-sh/setup-uv@v3` (uv runtime for events + saas workflows).
- `actions/setup-python@v5` (for spec-kitty workflow if not piggybacking
  on existing setup).
- Existing pinned tooling already declared in each repo's `pyproject.toml`
  / `uv.lock`.
**Storage**: N/A — workflows are stateless per run.
**Testing**:
- `spec-kitty` job runs `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v`.
- `spec-kitty-events` job runs `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/` against the pinned e2e checkout.
- `spec-kitty-saas` job runs `./scripts/run-sync-identity-boundary-canary.sh --single --yes` against the pinned e2e checkout, targeting `https://spec-kitty-dev.fly.dev`.
**Target Platform**: GitHub-hosted `ubuntu-latest` runners.
**Project Type**: Multi-repo infrastructure intervention (single mission
spans three GitHub repositories).
**Performance Goals**: See NFRs (5/10/15 minutes wall-clock).
**Constraints**: See spec C-001..C-010. Most-binding: no script changes,
no branch-protection mutation, no SaaS DB writes, no direct pushes to
main, `unset GITHUB_TOKEN` before any `gh` write.
**Scale/Scope**: Three new workflow files, three README sections, no
production code touched.

## Charter Check

- **DIR-001..DIR-013**: The mission is infrastructure-only; no producer
  code is added, so DIR-rules about hand-rolled events / direct-ingress
  patterns are trivially satisfied (no events are emitted from
  workflows). Workflows do not call into spec_kitty_events.
- **Shared Package Boundary**: Workflows do not introduce new imports;
  internal runtime is untouched.
- **Branch and Release Strategy**: All changes land via PR to `main`; no
  direct pushes. Release versioning is unaffected.
- **Code Quality**: New YAML files conform to actionlint conventions
  (named jobs, pinned action versions, explicit shells, concurrency
  blocks). README additions follow the existing repo's heading style.
- **CI and Branch Protection**: Workflows are added but not required-on-the-fly.
  The PR body provides the admin instruction for the protection-rule update.
- **`unset GITHUB_TOKEN`** before any `gh` write — enforced in mission
  ceremony for all PRs.

**Verdict**: Charter Check passes. No violations require Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/
├── plan.md              # This file
├── spec.md              # Specification (committed)
├── checklists/
│   └── requirements.md  # Spec quality checklist (committed)
├── tasks.md             # Phase 2 (created by /spec-kitty.tasks)
└── tasks/
    ├── WP01.md          # spec-kitty workflow + README
    ├── WP02.md          # spec-kitty-saas workflow + README
    ├── WP03.md          # spec-kitty-events workflow + README
    └── WP04.md          # PR-body admin-action documentation
```

### Source Code (across three repositories)

```
# Repo: spec-kitty (this worktree)
.github/workflows/canary-gate.yml      # NEW — drift-detector required-check job
README.md                               # ADDITIVE — "Identity-boundary canary CI gate" section

# Repo: spec-kitty-saas (cross-repo, dedicated worktree)
.github/workflows/canary-gate.yml      # NEW — clones e2e at pinned SHA, runs canary --single
README.md                               # ADDITIVE — "Identity-boundary canary CI gate" section

# Repo: spec-kitty-events (cross-repo)
.github/workflows/cross-repo-harness-tests.yml  # NEW — clones e2e at pinned SHA, runs unit tests
README.md                               # ADDITIVE — "Identity-boundary canary CI gate" section
```

**Structure Decision**: Multi-repo. Each WP touches exactly one repo. The
mission's spec.md is the single source of truth across all three; lane
branches are coordinated by WP. WP04 produces no code — it is a
PR-body-content artifact applied at PR creation time.

## Architecture: workflow contracts

### spec-kitty `canary-gate.yml`

- Trigger: `pull_request` against `main` and `push` to `main`.
- Job name: `drift-detector`.
- Steps: checkout @v6 → setup-python → install via `uv sync` (or pip
  install) → run `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v`.
- Permissions: `contents: read` only.
- Concurrency: `ci-canary-gate-${{ github.ref }}` with `cancel-in-progress: true`.
- Timeout: 5 minutes.

### spec-kitty-saas `canary-gate.yml`

- Trigger: `pull_request` against `main`.
- Job name: `canary-gate`.
- Steps:
  1. Checkout this repo (current PR commit).
  2. Checkout `Priivacy-ai/spec-kitty-end-to-end-testing` at SHA
     `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` into `./e2e`.
  3. Setup Python + uv.
  4. `uv sync` inside `./e2e`.
  5. Export `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_E2E_TRUSTED_RUNNER=1`,
     and canary-only credentials from `secrets.SPEC_KITTY_SAAS_CANARY_USERNAME`
     / `secrets.SPEC_KITTY_SAAS_CANARY_PASSWORD` (or a single
     `secrets.SPEC_KITTY_SAAS_CANARY_TOKEN` — the workflow will be written
     to support both, prefer token when present), plus
     `SPEC_KITTY_SAAS_BASE_URL=https://spec-kitty-dev.fly.dev`.
  6. Run `./scripts/run-sync-identity-boundary-canary.sh --single --yes`
     from inside `./e2e`.
  7. Fail closed if any required secret is absent (explicit guard step
     `if: ${{ secrets.SPEC_KITTY_SAAS_CANARY_USERNAME == '' && secrets.SPEC_KITTY_SAAS_CANARY_TOKEN == '' }}`
     → `echo` + `exit 1`).
- Permissions: `contents: read` only.
- Concurrency: `canary-gate-${{ github.ref }}` with `cancel-in-progress: true`.
- Timeout: 15 minutes.

### spec-kitty-events `cross-repo-harness-tests.yml`

- Trigger: `pull_request` against `main` and `push` to `main`.
- Job name: `harness-unit-tests`.
- Steps:
  1. Checkout this repo.
  2. Checkout `Priivacy-ai/spec-kitty-end-to-end-testing` at SHA
     `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` into `./e2e`.
  3. Setup Python + uv.
  4. `uv sync` inside `./e2e`.
  5. From `./e2e`, run `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/ -v`.
  6. To enable local-to-this-PR override of `spec_kitty_events`: install
     this repo's source via `uv pip install -e ../` so the harness runs
     against the PR's events code, not the events pinned by e2e's lockfile.
     (This is the key invariant — a PR that breaks the envelope shape must
     surface as a harness failure under the PR's events code.)
- Permissions: `contents: read` only.
- Concurrency: `harness-unit-tests-${{ github.ref }}` with `cancel-in-progress: true`.
- Timeout: 10 minutes.

## README contract (all three repos)

Section heading: `## Identity-boundary canary CI gate`.

Content outline (~80–120 lines per repo, repo-specific text):

1. What the gate protects (one sentence pointing at #1247 and e2e#41).
2. Which workflow / job name implements it (so admins can find the
   protection-rule entry to add).
3. The pinned e2e SHA, and *why* it's pinned (drift-resistance).
4. The exact procedure for updating the pinned SHA when intentional
   contract changes ship:
   - Land the contract change in e2e first.
   - Update the workflow's `ref:` and the README's pinned SHA in the same PR.
   - Confirm the gate is green on the bump PR before merging.
5. Required repo secrets (saas only) and how to rotate them.
6. Local reproduction command (so a contributor can simulate the CI gate
   before pushing).

## Cross-repo execution strategy

- **spec-kitty (this worktree)**: WP01 lands on the existing worktree's
  lane branch and gets pushed/PRed normally.
- **spec-kitty-saas**: WP02 uses
  `git -C /Users/.../spec-kitty-saas worktree add ../spec-kitty-saas-canary-gate origin/main`
  to avoid colliding with the concurrent mission #258's checkout. All
  edits, the commit, and the push happen inside that worktree. The
  worktree is removed at mission close (Phase 10).
- **spec-kitty-events**: WP03 cd's into the canonical path; no other
  concurrent mission is in that repo, so no worktree is required. (If
  the canonical path is on a branch other than `main`, switch to `main`
  cleanly first.)
- **WP04**: documentation-only artifact assembled into each of the three
  PR bodies at create time.

## Test strategy

- **Static**: each new workflow YAML is rendered via `actionlint` locally
  (if available) or by inspection against the existing workflows' patterns.
- **Dynamic (CI dry-run)**: opening the three PRs is itself the
  end-to-end test. The mission's PR-body checklist instructs the reviewer
  to wait for the new job to attempt to run on the same PR that introduces
  it and confirm pass/fail behavior.
- **Negative case (out of scope for this mission, mentioned in README)**:
  a follow-up "synthetic violation" PR per repo proves the gate fires
  red on a deliberately broken canary — explicitly listed in
  `ci-start-here.md` as "open a synthetic test PR on each repo and
  confirm the gate fires"; that follow-up is post-merge and not part of
  this mission's ship-list.

## Risk mitigation

- **Cross-repo clone latency**: pinned-SHA checkout adds ~10–30s; well
  within budgets.
- **Secret missing on first PR**: guard step fails fast with a named
  error; README documents the secret names. Repo admin adds the secret;
  re-run.
- **Events-package version mismatch**: WP03's `uv pip install -e ../`
  step ensures the PR's events source is what the harness exercises, not
  whatever was pinned in e2e's lockfile.
- **Concurrent #258 in spec-kitty-saas**: dedicated worktree avoids `git
  checkout` races; file-scope is disjoint (workflows vs. `apps/sync/`).
- **Concurrent #1248 in spec-kitty**: separate worktrees; file-scope is
  disjoint (`.github/workflows/canary-gate.yml` vs. AST lint rule under
  `src/`). README additions go in different sections.

## Complexity Tracking

No charter violations identified. Complexity Tracking section intentionally
empty.

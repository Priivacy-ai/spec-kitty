# Specification: Identity Boundary Canary CI Gate

**Mission ID**: 01KS4XWVCK38CJF5F6MDEXX0M3
**Slug**: identity-boundary-canary-ci-gate-01KS4XWV
**Mission Type**: software-dev
**Created**: 2026-05-21
**Target branch**: main
**Tracking issue**: [Priivacy-ai/spec-kitty#1247](https://github.com/Priivacy-ai/spec-kitty/issues/1247)

## Purpose (Stakeholder TLDR)

Make the identity-boundary canary a required CI check across three repositories
(`spec-kitty`, `spec-kitty-saas`, `spec-kitty-events`) so the next PR that
silently breaks the canary fails CI instead of reaching production.

## Context

The 4-run identity-boundary canary protocol that closed
`spec-kitty-end-to-end-testing#41` runs only on demand, locally. Nothing keeps
it green tomorrow — the next PR to any of the three producer / consumer repos
can break it silently and we only notice on the next manual run.

This mission pins three CI gates, one per repo, plus README documentation for
each, plus PR-body documentation of the branch-protection rule a human admin
must apply (since the GitHub token in CI cannot mutate branch protection on
its own under our scope).

## Scope

### In scope

- New workflow file in `spec-kitty/.github/workflows/canary-gate.yml` that
  runs the existing `tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition`
  test (and any future drift-detector tests) as a dedicated, named job so it
  can be marked a required check independently of the broader `ci-quality`
  matrix.
- README section in `spec-kitty/README.md` explaining the gate, what it
  protects, and how to update the pinned `spec-kitty-end-to-end-testing` SHA
  when intentional contract changes ship.
- New workflow file in `spec-kitty-saas/.github/workflows/canary-gate.yml`
  that checks out `spec-kitty-end-to-end-testing` at a pinned SHA and runs
  `./scripts/run-sync-identity-boundary-canary.sh --single --yes` against the
  `deployed-dev` target using canary-only credentials supplied via repo
  secrets.
- README section in `spec-kitty-saas/README.md` explaining the gate, the
  required secrets, the staging target, and the pinned-SHA update procedure.
- New workflow file in
  `spec-kitty-events/.github/workflows/cross-repo-harness-tests.yml` that
  checks out `spec-kitty-end-to-end-testing` at a pinned SHA and runs
  `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/`.
- README section in `spec-kitty-events/README.md` explaining the gate and the
  pinned-SHA update procedure.
- PR-body documentation in each PR identifying the exact required-status
  check name a repo admin must add to the branch-protection rule for `main`.

### Out of scope

- Changing the canary script itself (`run-sync-identity-boundary-canary.sh`).
- Mutating branch-protection rules from CI or the mission (admin-only action).
- Cron-side execution of the canary (tracked separately in
  `spec-kitty-end-to-end-testing#61`).
- Any Python / TypeScript source-code changes. This mission is workflow YAML
  and README markdown only.

## Domain Language

| Canonical term | Meaning | Avoid |
|---|---|---|
| Identity-boundary canary | The 4-run sync identity-boundary protocol from `spec-kitty-end-to-end-testing` that exercises the SaaS strict gate against deployed-dev. | "the canary" (ambiguous), "sync test" |
| Required check | A GitHub branch-protection status-check entry that blocks merge until green. | "blocking test" |
| Pinned e2e SHA | The exact commit of `spec-kitty-end-to-end-testing` referenced by a downstream workflow. | "main of e2e", "latest e2e" |
| Deployed-dev | The `spec-kitty-dev.fly.dev` SaaS instance. | "staging", "dev SaaS" |
| Canary-only credentials | Service-account credentials with scope limited to the canary's needs, stored in repo secrets. | "test credentials" |

Pinned e2e SHA for this mission: `03e4d3c04fcdf641cd564badfbc87bb19a2a0982`
(HEAD of `Priivacy-ai/spec-kitty-end-to-end-testing` main at mission start).

## User Scenarios

### Primary scenario: contributor opens a PR that would break the canary

- **Actor**: Contributor opening a PR against `main` of any of the three repos.
- **Trigger**: `git push` followed by `gh pr create`.
- **Happy path**: The repo's `canary-gate` (or
  `cross-repo-harness-tests`) workflow runs the pinned check; it passes; the
  required-check status goes green; the PR is mergeable.
- **Failure path**: The required check goes red; the PR is blocked from
  merging until the contributor either fixes the underlying contract drift
  or, with reviewer sign-off, updates the pinned SHA in the workflow and
  the README's update procedure.
- **Always-true rule**: Once branch protection is configured, a red required
  check blocks merge regardless of approvals.

### Secondary scenario: intentional contract change in spec-kitty-events

- **Actor**: Events maintainer landing a deliberate envelope-shape change.
- **Trigger**: The change lands in `spec-kitty-end-to-end-testing` first,
  bumping the harness to match.
- **Happy path**: The maintainer follows the README's "updating the pinned
  e2e SHA" procedure: open a PR that bumps the SHA in
  `cross-repo-harness-tests.yml` and the README, confirm the gate goes green
  against the new SHA, merge.
- **Exception**: If the SHA bump alone is insufficient (the events change
  also needs SaaS-side updates), the failure path makes the dependency
  visible: events PR is blocked, the operator opens the SaaS PR first.

### Edge case: cron-side canary failure vs CI gate

- These are independent. The CI gate fires on every PR. The cron canary
  (e2e#61) fires on a schedule against deployed-dev. The mission contract
  for this work is the CI gate only.

## Functional Requirements

| ID | Description | Status |
|---|---|---|
| FR-001 | `spec-kitty` repository SHALL have a dedicated workflow file at `.github/workflows/canary-gate.yml` that runs `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` on `pull_request` against `main` and on `push` to `main`. | new |
| FR-002 | The `spec-kitty` workflow job SHALL be named `drift-detector` (or another stable, documented name) so a repo admin can register it as a required status check. | new |
| FR-003 | `spec-kitty-saas` repository SHALL have a workflow file at `.github/workflows/canary-gate.yml` that on `pull_request` against `main` checks out `Priivacy-ai/spec-kitty-end-to-end-testing` at the pinned SHA, installs its dependencies via `uv`, exports the canary's required environment (`SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_E2E_TRUSTED_RUNNER=1`), and runs `./scripts/run-sync-identity-boundary-canary.sh --single --yes`. | new |
| FR-004 | The `spec-kitty-saas` workflow SHALL pull canary-only service-account credentials from repo secrets and inject them into the canary script's environment; the workflow SHALL NOT print credentials, and SHALL fail closed if a required secret is missing. | new |
| FR-005 | The `spec-kitty-saas` workflow's canary target SHALL be deployed-dev (`spec-kitty-dev.fly.dev`); it SHALL NOT spin up an ephemeral Fly app per-PR. | new |
| FR-006 | The `spec-kitty-saas` workflow job SHALL be named `canary-gate` (or another stable, documented name) so a repo admin can register it as a required status check. | new |
| FR-007 | `spec-kitty-events` repository SHALL have a workflow file at `.github/workflows/cross-repo-harness-tests.yml` that on `pull_request` against `main` checks out `Priivacy-ai/spec-kitty-end-to-end-testing` at the pinned SHA, installs its dependencies via `uv`, and runs `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/`. | new |
| FR-008 | The `spec-kitty-events` workflow job SHALL be named `harness-unit-tests` (or another stable, documented name) so a repo admin can register it as a required status check. | new |
| FR-009 | Each of the three workflows SHALL pin `spec-kitty-end-to-end-testing` to the exact SHA `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` (HEAD of main at mission start), using `actions/checkout@v6` with `ref: <sha>` and `repository: Priivacy-ai/spec-kitty-end-to-end-testing`. | new |
| FR-010 | Each of the three repos SHALL have a new README section titled "Identity-boundary canary CI gate" (or equivalent stable heading) that explains: which workflow runs the gate, what it protects, the pinned e2e SHA, and the procedure for updating the pinned SHA when intentional contract changes ship. | new |
| FR-011 | Each PR body SHALL include an "Action required from repo admin" section naming the exact required-status-check string to add to the branch-protection rule for `main` in that repo. | new |

## Non-Functional Requirements

| ID | Description | Status |
|---|---|---|
| NFR-001 | The `spec-kitty` `canary-gate` job SHALL complete in under 5 minutes wall-clock on a default `ubuntu-latest` runner (existing test runtime is well under one minute; budget allows for venv install). | new |
| NFR-002 | The `spec-kitty-events` `harness-unit-tests` job SHALL complete in under 10 minutes wall-clock on a default `ubuntu-latest` runner. | new |
| NFR-003 | The `spec-kitty-saas` `canary-gate` job SHALL complete in under 15 minutes wall-clock against deployed-dev. The canary's own 4-run protocol takes a few minutes; the single-run CI variant must stay within this envelope. | new |
| NFR-004 | All three workflows SHALL be idempotent and re-runnable: a re-run on the same SHA against the same target produces the same pass/fail result modulo deployed-dev availability. | new |
| NFR-005 | Workflows SHALL be configured with `concurrency` groups keyed on `${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true` to avoid stacking redundant runs on rapid pushes. | new |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | The mission SHALL NOT modify `run-sync-identity-boundary-canary.sh` itself. | binding |
| C-002 | The mission SHALL NOT mutate any branch-protection rule from CI or from the mission. Branch protection changes are explicitly out-of-scope, documented in PR bodies for a human admin. | binding |
| C-003 | The mission SHALL NOT mutate any SaaS database, queue, or readiness counter. | binding |
| C-004 | The mission SHALL NOT change ingress limits. | binding |
| C-005 | All `gh` writes performed during the mission SHALL be prefixed with `unset GITHUB_TOKEN` so the keyring token (broader scope) is used instead of the limited env token. | binding |
| C-006 | The mission SHALL NOT push directly to `main` in any repo. All changes land via PR. The mission SHALL NOT merge any PR it opens. | binding |
| C-007 | The mission SHALL NOT introduce hand-rolled event dicts. (Trivially satisfied: this mission produces no event-emitting code.) | binding |
| C-008 | In `spec-kitty-saas`, the mission SHALL touch only `.github/workflows/canary-gate.yml` (new file) and `README.md` (additive section). It SHALL NOT touch `apps/sync/*` or any source code, which is concurrently owned by mission `sunset-carve-out-constants-01KS4XTA` (issue #258). To avoid `git checkout` races with that mission's worktree, this mission SHALL use a dedicated `git worktree add` off `origin/main` in spec-kitty-saas. | binding |
| C-009 | In `spec-kitty`, the mission SHALL touch only `.github/workflows/canary-gate.yml` (new file) and `README.md` (additive section). It SHALL NOT modify `ci-quality.yml` or any existing workflow. (Concurrent same-repo mission for AST lint, issue #1248, is in a separate worktree with its own scope.) | binding |
| C-010 | The mission SHALL produce its retrospective via `spec-kitty retrospect create` after PRs are opened. | binding |

## Success Criteria

- A contributor opening a PR against any of the three repos triggers the
  appropriate `canary-gate` or `cross-repo-harness-tests` job within 30
  seconds of `git push`.
- A deliberately broken canary (e.g. envelope-shape change in events) causes
  the corresponding repo's required check to go red; the PR is blocked from
  merging once the repo admin completes the documented branch-protection
  step.
- A green main on all three repos demonstrates the canary protocol is
  preserved end-to-end at PR time, without requiring a manual canary run.
- Each repo's README provides a self-contained procedure an unfamiliar
  contributor can follow to bump the pinned e2e SHA.
- The mission opens three PRs (one per repo), none merged, each with a clear
  "Action required from repo admin" block in its body.

## Key Entities

- **`canary-gate.yml`** (spec-kitty, spec-kitty-saas) — GitHub Actions
  workflow file; required-check producer.
- **`cross-repo-harness-tests.yml`** (spec-kitty-events) — GitHub Actions
  workflow file; required-check producer.
- **README "Identity-boundary canary CI gate" section** (one per repo) —
  Operator documentation for the gate and the pinned-SHA update procedure.
- **Pinned e2e SHA** — `03e4d3c04fcdf641cd564badfbc87bb19a2a0982`.

## Assumptions

- The `Priivacy-ai/spec-kitty-end-to-end-testing` repository is publicly
  cloneable from GitHub Actions runners under the standard `GITHUB_TOKEN`
  ambient identity (it is a sibling repo in the same org and `actions/checkout`
  to a public org repo works without extra credentials; if private,
  `secrets.GH_E2E_READ_TOKEN` would be required and that addition is in
  scope of FR-004's secret-management surface).
- The `deployed-dev` SaaS instance at `spec-kitty-dev.fly.dev` is reachable
  from default GitHub-hosted runner IP ranges (it is today; the cron mission
  e2e#61 has the same assumption).
- A repo admin will, post-merge of each PR, add the gate as a required check
  in the branch-protection rule. The mission's deliverable is the workflow
  file + the explicit admin instruction in the PR body, not the protection
  rule change itself.
- The canary script supports the `--single --yes` invocation pattern used
  by the saas workflow (confirmed: the script's header documents both flags).
- The pinned e2e SHA contains `tests/unit/identity_boundary/` and
  `tests/identity_boundary/unit/` (confirmed via `find` at mission start).

## Dependencies

- `Priivacy-ai/spec-kitty-end-to-end-testing` at SHA
  `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` for the canary script and the
  identity-boundary unit tests.
- `actions/checkout@v6`, `astral-sh/setup-uv@v3` (or current equivalent) for
  the three workflows.
- Repo secrets (existing in `spec-kitty-saas` org config or to be added by
  admin) for canary-only credentials: at minimum
  `SPEC_KITTY_SAAS_CANARY_USERNAME`, `SPEC_KITTY_SAAS_CANARY_PASSWORD`, or
  equivalent token. The workflow names these symbolically and documents the
  expected secret names in the README; provisioning the actual secret values
  is a human admin action.

## Risks

- **Canary flakes against deployed-dev**: The deployed-dev target may be
  intermittently unavailable. Mitigation: NFR-003's 15-minute budget plus
  workflow-level `timeout-minutes` set conservatively; the gate is allowed
  to be retried by the contributor (`gh pr checks --watch` pattern), and
  README documents the retry guidance.
- **Pinned SHA goes stale**: An events contract change in e2e that is *not*
  reflected in the pinned SHA could keep CI green while production drifts.
  Mitigation: the cron canary (e2e#61) catches that case independently;
  documented in each README.
- **Required-check name drift**: If we later rename the workflow job, the
  branch-protection rule silently stops enforcing. Mitigation: FR-002 / FR-006 /
  FR-008 lock in stable job names; README documents the names.

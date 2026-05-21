# Cross-repo manifest: spec-kitty-saas

This manifest documents the WP02 deliverable that ships in the
`Priivacy-ai/spec-kitty-saas` sibling repo. It exists in this mission
directory so the mission's audit trail is self-contained; the
authoritative copies of the files described below live in
spec-kitty-saas's PR.

## Repo

`Priivacy-ai/spec-kitty-saas`

## Lane branch

`mission/identity-boundary-canary-ci-gate-saas`

## Worktree used

`/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-saas-canary-gate`
(dedicated worktree off `origin/main` to avoid `git checkout` races
with concurrent mission `sunset-carve-out-constants-01KS4XTA` / issue #258).

## Lane head commit

`0da0674a` (filled in at commit time; verify in the spec-kitty-saas PR)

## PR URL

To be filled in once the PR is opened.

## Files shipped

### `.github/workflows/canary-gate.yml`

- Triggers: `pull_request` against `main`, `workflow_dispatch`.
- Job: `canary-gate` on `ubuntu-latest`, 15-minute timeout.
- Concurrency: `canary-gate-${{ github.ref }}` with `cancel-in-progress: true`.
- Permissions: `contents: read` only.
- Steps:
  1. Checkout this repo into `saas/`.
  2. Checkout `Priivacy-ai/spec-kitty-end-to-end-testing` at SHA
     `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` into `e2e/`.
  3. Set up uv.
  4. `uv sync` inside `e2e/`.
  5. Guard step: fail-closed if both `SPEC_KITTY_SAAS_CANARY_TOKEN`
     and (`SPEC_KITTY_SAAS_CANARY_USERNAME` + `SPEC_KITTY_SAAS_CANARY_PASSWORD`)
     are absent.
  6. Run `./scripts/run-sync-identity-boundary-canary.sh --single --yes`
     inside `e2e/` with env:
     - `SPEC_KITTY_ENABLE_SAAS_SYNC: '1'`
     - `SPEC_KITTY_E2E_TRUSTED_RUNNER: '1'`
     - `SPEC_KITTY_SAAS_BASE_URL: 'https://spec-kitty-dev.fly.dev'`
     - Credentials from repo secrets.

### `README.md` — appended section

- Heading: `## Identity-boundary canary CI gate`.
- Names the job `canary-gate` for branch-protection registration.
- Documents required secrets, pinned e2e SHA, update procedure, and
  sibling-repo gates.

## Required repo admin actions (post-merge)

1. Add Actions secrets at
   https://github.com/Priivacy-ai/spec-kitty-saas/settings/secrets/actions:
   - `SPEC_KITTY_SAAS_CANARY_TOKEN` (preferred), OR
   - `SPEC_KITTY_SAAS_CANARY_USERNAME` + `SPEC_KITTY_SAAS_CANARY_PASSWORD`.
2. Register `canary-gate` as a required status check on the branch
   protection rule for `main` at
   https://github.com/Priivacy-ai/spec-kitty-saas/settings/branches.

## Coordination notes

- File-scope disjoint from concurrent mission #258
  (`sunset-carve-out-constants-01KS4XTA`), which owns `apps/sync/*` and
  `.github/workflows/sunset-check.yml`. This WP owns
  `.github/workflows/canary-gate.yml` (distinct filename) and an
  additive README section.
- Worktree should be removed at mission close (Phase 10) via
  `git -C /Users/.../spec-kitty-saas worktree remove ../spec-kitty-saas-canary-gate`.

# Cross-repo manifest: spec-kitty-events

This manifest documents the WP03 deliverable that ships in the
`Priivacy-ai/spec-kitty-events` sibling repo. The authoritative copies
live in spec-kitty-events's PR.

## Repo

`Priivacy-ai/spec-kitty-events`

## Lane branch

`mission/identity-boundary-canary-ci-gate-events`

## Worktree used

Canonical spec-kitty-events checkout at
`/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-events`
(no concurrent mission in this repo; no dedicated worktree needed).

## Lane head commit

`0505506` (filled at commit time; verify in the spec-kitty-events PR)

## PR URL

To be filled in once the PR is opened.

## Files shipped

### `.github/workflows/cross-repo-harness-tests.yml`

- Triggers: `pull_request` against `main`, `push` to `main`, `workflow_dispatch`.
- Job: `harness-unit-tests` on `ubuntu-latest`, 10-minute timeout.
- Concurrency: `harness-unit-tests-${{ github.ref }}` with `cancel-in-progress: true`.
- Permissions: `contents: read` only.
- Steps:
  1. Checkout this repo into `events/`.
  2. Checkout `Priivacy-ai/spec-kitty-end-to-end-testing` at SHA
     `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` into `e2e/`.
  3. Set up uv.
  4. `uv sync` inside `e2e/`.
  5. `uv pip install -e ../events` from inside `e2e/` (key invariant:
     harness runs against PR's events source).
  6. `uv run pytest tests/unit/identity_boundary/ tests/identity_boundary/unit/ -v --tb=short`
     from inside `e2e/`.

### `README.md` — appended section

- Heading: `## Identity-boundary canary CI gate`.
- Names the job `harness-unit-tests` for branch-protection registration.
- Documents the editable-install invariant, pinned e2e SHA, update
  procedure, and sibling-repo gates.

## Required repo admin actions (post-merge)

1. Register `harness-unit-tests` as a required status check on the
   branch protection rule for `main` at
   https://github.com/Priivacy-ai/spec-kitty-events/settings/branches.

## Coordination notes

- No concurrent mission in this repo; no file-scope conflicts.

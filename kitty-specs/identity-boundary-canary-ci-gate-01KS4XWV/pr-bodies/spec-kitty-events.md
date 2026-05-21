## Summary

Adds the spec-kitty-events side of a three-repo CI gate that pins the
identity-boundary canary protocol (closed
[`spec-kitty-end-to-end-testing#41`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41))
as a required check on every PR. This PR adds:

- A new workflow
  `.github/workflows/cross-repo-harness-tests.yml` that on every PR
  against `main` (and on push to main) clones
  [`Priivacy-ai/spec-kitty-end-to-end-testing`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing)
  at the pinned SHA `03e4d3c04fcdf641cd564badfbc87bb19a2a0982`,
  installs **this PR's events source** as editable into the e2e env
  via `uv pip install -e ../events`, and runs the harness's identity-
  boundary unit tests. The job is named `harness-unit-tests`.
- A README section explaining the gate, the editable-install
  invariant, the pinned-SHA update procedure, and the sibling-repo gates.

The editable-install step is the key invariant: the harness must
exercise the PR's events code, not whatever e2e's lockfile pinned, so
an envelope-shape regression introduced by the PR surfaces here before
the SaaS strict gate sees it in production.

## Evidence

- Mission (in spec-kitty):
  [`kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/`](https://github.com/Priivacy-ai/spec-kitty/tree/main/kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV)
- Pinned e2e tests:
  [`spec-kitty-end-to-end-testing/tests/unit/identity_boundary/`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/tree/03e4d3c04fcdf641cd564badfbc87bb19a2a0982/tests/unit/identity_boundary)
  and
  [`tests/identity_boundary/unit/`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/tree/03e4d3c04fcdf641cd564badfbc87bb19a2a0982/tests/identity_boundary/unit).

## Action required from repo admin

After this PR merges, a repo admin must register the new check as
required on the branch-protection rule for `main`:

1. Open https://github.com/Priivacy-ai/spec-kitty-events/settings/branches
2. Edit the rule for `main`.
3. Under "Require status checks to pass before merging", click "Add
   status check" and add the exact string:
   ```
   harness-unit-tests
   ```
4. Save the rule.

**Why this matters**: until this admin step lands, the workflow runs
on every PR but its red status does not block merge. The mission's
contract is that the gate is enforced.

### Verification

After enabling the protection rule:

- [ ] Open a trivial follow-up PR (e.g. README typo) and confirm the
  `harness-unit-tests` check runs and goes green.
- [ ] (Optional, with approval) Open a synthetic-violation PR that
  introduces an envelope-shape regression (e.g. rename a required
  field in a lifecycle payload); confirm the check goes red and merge
  is blocked.

## Test plan

- [ ] CI: `harness-unit-tests` job runs on this PR.
- [ ] CI: `harness-unit-tests` job passes (this PR makes no events
  changes, so the harness should be green at the pinned SHA against
  the current events HEAD).
- [ ] No modification to existing workflows.
- [ ] No source-code changes outside `.github/workflows/` and
  `README.md`.

## Tracker

- Closes (when all three sibling PRs merge): part of
  [`Priivacy-ai/spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247).
- Drift-class epic:
  [`Priivacy-ai/spec-kitty#1198`](https://github.com/Priivacy-ai/spec-kitty/issues/1198).

## Summary

Adds the spec-kitty-saas side of a three-repo CI gate that pins the
identity-boundary canary protocol (closed
[`spec-kitty-end-to-end-testing#41`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41))
as a required check on every PR. This PR adds:

- A new workflow `.github/workflows/canary-gate.yml` that on every PR
  against `main` clones
  [`Priivacy-ai/spec-kitty-end-to-end-testing`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing)
  at the pinned SHA `03e4d3c04fcdf641cd564badfbc87bb19a2a0982` and runs
  `./scripts/run-sync-identity-boundary-canary.sh --single --yes`
  against `https://spec-kitty-dev.fly.dev` using canary-only
  credentials from repo secrets. The job is named `canary-gate`.
- A fail-closed guard that refuses to run the canary if the required
  secrets are missing.
- A README section explaining the gate, required secrets, the
  pinned-SHA update procedure, and the sibling-repo gates.

The workflow uses the deployed-dev target (not an ephemeral Fly app
per PR) to keep CI cost bounded; the cron canary in
[`spec-kitty-end-to-end-testing#61`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/61)
provides the complementary scheduled-protection coverage.

## Evidence

- Mission (in spec-kitty):
  [`kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/`](https://github.com/Priivacy-ai/spec-kitty/tree/main/kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV)
- The canary script being invoked:
  [`spec-kitty-end-to-end-testing/scripts/run-sync-identity-boundary-canary.sh`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/blob/03e4d3c04fcdf641cd564badfbc87bb19a2a0982/scripts/run-sync-identity-boundary-canary.sh)
  at the pinned SHA.

## Action required from repo admin

Two steps, both required for the gate to become enforced:

### 1. Add the canary-only secrets to repo Actions secrets

Open https://github.com/Priivacy-ai/spec-kitty-saas/settings/secrets/actions
and add **either** form (token preferred):

- `SPEC_KITTY_SAAS_CANARY_TOKEN` (a single bearer token), **OR**
- `SPEC_KITTY_SAAS_CANARY_USERNAME` **and**
  `SPEC_KITTY_SAAS_CANARY_PASSWORD`

These should be scoped to the canary's needs only — they must not be
prod credentials. The README documents the rotation procedure.

Until the secrets are present, the workflow's guard step will fail the
job intentionally with a named error.

### 2. Register `canary-gate` as a required status check

Open https://github.com/Priivacy-ai/spec-kitty-saas/settings/branches,
edit the rule for `main`, and add the exact string:

```
canary-gate
```

under "Require status checks to pass before merging".

**Why this matters**: until both steps land, the workflow runs on
every PR but its red status does not block merge. The mission's
contract is that the gate is enforced.

### Verification

After both steps land:

- [ ] Open a trivial follow-up PR (e.g. README typo) and confirm the
  `canary-gate` check runs and goes green.
- [ ] (Optional, with approval) Open a synthetic-violation PR that
  introduces a contract change the canary should reject; confirm the
  check goes red and merge is blocked.
- [ ] After 24 hours of green main, confirm the cron canary in
  spec-kitty-end-to-end-testing (#61) also stays green.

## Test plan

- [ ] CI: `canary-gate` job runs on this PR.
- [ ] Guard step behavior: in absence of secrets, job fails closed
  with the named error.
- [ ] After secrets are added: `canary-gate` job runs the canary
  against deployed-dev and reports pass/fail.
- [ ] No modification to `apps/sync/*` or other source files
  (concurrent mission #258 owns those — verify by `git diff main..HEAD --stat`).
- [ ] No modification to existing workflows.

## Tracker

- Closes (when all three sibling PRs merge): part of
  [`Priivacy-ai/spec-kitty#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247).
- Drift-class epic:
  [`Priivacy-ai/spec-kitty#1198`](https://github.com/Priivacy-ai/spec-kitty/issues/1198).

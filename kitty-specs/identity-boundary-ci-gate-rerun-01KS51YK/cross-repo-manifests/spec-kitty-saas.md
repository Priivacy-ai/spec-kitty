# Cross-Repo Manifest: spec-kitty-saas

**Repo**: `Priivacy-ai/spec-kitty-saas`
**Lane branch**: `mission/identity-boundary-ci-gate-saas-rerun`
**PR**: #264 — https://github.com/Priivacy-ai/spec-kitty-saas/pull/264
**Required-check name** (register post-merge): `identity-boundary-canary` (see `../contracts/check-names.md`)

## Pinned e2e SHA

`4d5206e08a30bf23ae4dabae532dc0e355078e16` (HEAD of
`Priivacy-ai/spec-kitty-end-to-end-testing@main` at planning time).

## Required GitHub Actions secret (one-time, admin)

- `SPEC_KITTY_CANARY_TOKEN` — canary-only API token for the deployed-dev
  SaaS instance (`spec-kitty-dev.fly.dev`).
- Provision at: https://github.com/Priivacy-ai/spec-kitty-saas/settings/secrets/actions

## Files landed

| Path                                      | Status   | LOC delta |
|-------------------------------------------|----------|-----------|
| `.github/workflows/canary-gate.yml`       | NEW      | +75       |
| `README.md`                               | MODIFIED | +85/-0    |

Total LOC delta: +160.

## Admin action required (post-merge)

1. Open https://github.com/Priivacy-ai/spec-kitty-saas/settings/branches
2. Edit the rule for `main`
3. Under "Require status checks to pass before merging", add the exact name `identity-boundary-canary`
4. Save

## Verification (post-admin-action)

Open any trivial follow-up PR; confirm the `identity-boundary-canary`
check runs and the merge button greys out while it's pending. A red
check should block merge.

## Notes

- Concurrency group `identity-boundary-canary` (NOT keyed by ref)
  serializes all PR canary runs against deployed-dev — only one at a time.
  `cancel-in-progress: false` ensures in-flight canaries are not aborted
  by newer PRs. Trade-off: slow under high PR throughput; acceptable for
  the saas repo's actual PR volume.
- The canary script is the closed artifact of `e2e#41`; this mission
  does NOT modify it.
- No ephemeral Fly app spin-up per PR (operating-rule compliance).

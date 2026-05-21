# Cross-Repo Manifest: spec-kitty-events

**Repo**: `Priivacy-ai/spec-kitty-events`
**Lane branch**: `mission/identity-boundary-ci-gate-events-rerun`
**PR**: #36 — https://github.com/Priivacy-ai/spec-kitty-events/pull/36
**Required-check name** (register post-merge): `cross-repo-harness-tests` (see `../contracts/check-names.md`)

## Pinned e2e SHA

`4d5206e08a30bf23ae4dabae532dc0e355078e16` (HEAD of
`Priivacy-ai/spec-kitty-end-to-end-testing@main` at planning time).

## Files landed

| Path                                                  | Status   | LOC delta |
|-------------------------------------------------------|----------|-----------|
| `.github/workflows/cross-repo-harness-tests.yml`      | NEW      | +73       |
| `README.md`                                           | MODIFIED | +54/-0    |

Total LOC delta: +127.

## Admin action required (post-merge)

1. Open https://github.com/Priivacy-ai/spec-kitty-events/settings/branches
2. Edit the rule for `main`
3. Under "Require status checks to pass before merging", add the exact name `cross-repo-harness-tests`
4. Save

## Verification (post-admin-action)

Open any trivial follow-up PR; confirm the `cross-repo-harness-tests`
check runs and the merge button greys out while it's pending. A red
check should block merge.

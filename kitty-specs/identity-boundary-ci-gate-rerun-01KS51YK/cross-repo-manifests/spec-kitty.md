# Cross-Repo Manifest: spec-kitty

**Repo**: `Priivacy-ai/spec-kitty`
**Lane branch**: `kitty/mission-identity-boundary-ci-gate-rerun-01KS51YK-lane-a`
**PR**: #1267 — https://github.com/Priivacy-ai/spec-kitty/pull/1267
**Required-check name** (register post-merge): `drift-detector` (see `../contracts/check-names.md`)

## Files landed

| Path                                       | Status | LOC delta |
|--------------------------------------------|--------|-----------|
| `.github/workflows/drift-detector.yml`     | NEW    | +48       |
| `README.md`                                | MODIFIED | +34/-0  |

Total LOC delta: +82.

## Admin action required (post-merge)

1. Open https://github.com/Priivacy-ai/spec-kitty/settings/branches
2. Edit the rule for `main`
3. Under "Require status checks to pass before merging", add the exact name `drift-detector`
4. Save

## Verification (post-admin-action)

Open any trivial follow-up PR; confirm the `drift-detector` check runs
and the merge button greys out while it's pending. A red check should
block merge.

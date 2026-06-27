---
title: Identity-Boundary CI Gate
description: 'The drift-detector required CI check running the canonical-registry recognition test on every PR to catch drift against the consumer-recognition contract (an #1247 gate).'
doc_status: active
updated: '2026-06-12'
---
# Identity-Boundary CI Gate

The `drift-detector` required check runs
`tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition` on every PR
against `main`. It catches drift between the canonical registries in this
repo and the consumer-recognition contract that
`spec-kitty-end-to-end-testing#41` closed over an 8-RC peeling cycle
(rc14 -> rc22). Workflow file:
[`.github/workflows/drift-detector.yml`](../../.github/workflows/drift-detector.yml).

This is one of three coordinated CI gates tracked under
[`#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247):

- `drift-detector` here (this repo).
- `cross-repo-harness-tests` in [`spec-kitty-events`](https://github.com/Priivacy-ai/spec-kitty-events) - workflow `.github/workflows/cross-repo-harness-tests.yml`.
- `identity-boundary-canary` in [`spec-kitty-saas`](https://github.com/Priivacy-ai/spec-kitty-saas) - workflow `.github/workflows/canary-gate.yml`.

This repo's drift-detector pins no external SHA. It only runs an in-repo
test. The sibling repos' workflows pin a specific commit of
`Priivacy-ai/spec-kitty-end-to-end-testing`; see each sibling's README
`Identity-Boundary CI Gate` section for the SHA-bump procedure.

## Admin Action

After this gate merges, a repo admin must register the check as required on
`main`:

1. Open https://github.com/Priivacy-ai/spec-kitty/settings/branches.
1. Edit the rule for `main`.
1. Under "Require status checks to pass before merging", add the exact name
   `drift-detector`.
1. Save.

Until that step is done, the workflow still runs on every PR but its red
status does not block merge.

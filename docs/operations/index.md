---
title: Operations
description: 'Durable operational runbooks for Spec Kitty: deployment, CI/CD setup, and standing CI-gate procedures that outlive any single mission.'
doc_status: active
updated: '2026-06-27'
related:
- docs/configuration/index.md
- docs/guides/index.md
- docs/index.md
- docs/operations/identity-boundary-ci-gate.md
- docs/operations/ssh-deploy-keys.md
- docs/plans/index.md
---
# Operations

Durable operational procedures — deployment, on-call, incident, and standing
CI-gate runbooks. These pages are maintainer-facing references that stay correct
across missions (unlike the effort-scoped notes that live under
[`../plans/`](../plans/index.md)).

## Pages

- [SSH deploy-key setup for CI/CD](ssh-deploy-keys.md) — one-time deploy-key provisioning runbook.
- [Identity-boundary CI gate](identity-boundary-ci-gate.md) — the `drift-detector` required check and its cross-repo SHA-bump procedure.

## See also

- [Documentation home](../index.md)
- [Guides](../guides/index.md)
- [Configuration](../configuration/index.md)

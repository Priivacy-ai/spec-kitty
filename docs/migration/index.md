---
title: Migration to Spec Kitty 3.2
description: Migration hub for upgrading existing Spec Kitty projects to the current 3.2 Charter-era runtime and archive boundary.
doc_status: active
updated: '2026-06-03'
related:
- docs/context/index.md
- docs/archive/index.md
- docs/migration/2-1-main-cutover-checklist.md
- docs/migration/charter-ownership-consolidation.md
- docs/migration/cross-repo-e2e-gate.md
- docs/migration/doctrine-local-overlay-to-org-layer.md
- docs/migration/feature-flag-deprecation.md
- docs/migration/from-charter-2x.md
- docs/migration/mission-id-canonical-identity.md
- docs/migration/mission-type-flag-deprecation.md
- docs/migration/retrospective-events-upstream.md
- docs/migration/shared-package-boundary-cutover.md
- docs/migration/teamspace-mission-state-920-closeout.md
- docs/migration/teamspace-mission-state-repair.md
- docs/migration/upgrade-to-0-12-0.md
---
> Migration note: This page collects migration paths and historical cutover notes. For new projects, start with [Getting Started](../guides/getting-started.md).

# Migration to Spec Kitty 3.2

Use these pages when an existing project, script, or operator habit predates the current 3.2 documentation set. New projects should start with [Getting Started](../guides/getting-started.md) and the [3.2 current overview](../context/index.md).

## Answer summary

- Current target version: Spec Kitty 3.2.
- Current runtime model: Charter-era missions with governed context injection.
- Current governance source: `.kittify/charter/charter.md`.
- Current mission loop: `spec-kitty next --agent <name> --mission <slug>`.
- Historical 1.x and 2.x pages are archived under [Historical Archive](../archive/index.md).

## Current 3.2 migrations

- [Migrating from 2.x / early 3.x](from-charter-2x.md)
- [Doctrine local overlay to org layer](doctrine-local-overlay-to-org-layer.md)
- [Mission ID canonical identity](mission-id-canonical-identity.md)
- [Mission type flag deprecation](mission-type-flag-deprecation.md)
- [Feature flag deprecation](feature-flag-deprecation.md)

## Historical and internal runbooks

These pages are preserved for older cutovers, closeouts, and engineering context. Use them only when the current migration pages link to them or when auditing historical behavior.

- [Historical 2.1 cutover](2-1-main-cutover-checklist.md)
- [Historical upgrade to 0.12.0](upgrade-to-0-12-0.md)
- [TeamSpace mission-state repair](teamspace-mission-state-repair.md)
- [TeamSpace mission-state closeout](teamspace-mission-state-920-closeout.md)
- [Charter ownership consolidation](charter-ownership-consolidation.md)
- [Cross-repo E2E gate](cross-repo-e2e-gate.md)
- [Retrospective events upstream](retrospective-events-upstream.md)
- [Shared package boundary cutover](shared-package-boundary-cutover.md)

---
title: Architecture 3.x
description: 'Landing page for the 3.x architecture track (since the 3.0.0 release on 2026-03-30): its core decisions, constraints, and end-to-end behavior expectations.'
doc_status: active
updated: '2026-05-19'
---
# Architecture 3.x

This directory is the current architecture track for Spec Kitty, starting with
the 3.0.0 release on 2026-03-30.

## What This Track Captures

1. Core architecture decisions and constraints (`adr/`).
2. (Future) End-to-end behavior expectations, initiatives, and layered C4
   documentation analogous to the 2.x track.

The 2.x track (`architecture/2.x/`) captured the architecture through the
2.x → 3.x cutover. ADRs dated on or after 2026-03-30 live here in 3.x; older
ADRs remain in `docs/adr/2.x/`. Back-compat symlinks at the old
`docs/adr/2.x/<filename>` paths point at the new 3.x location so
existing references — in CHANGELOG entries, test snapshots, and shipped
docs — continue to resolve.

## ADR Authoring

Use the shared template at `docs/architecture/adr-template.md`. The same template
serves all tracks (1.x, 2.x, 3.x) — there is no per-track template fork.

Naming: `YYYY-MM-DD-N-descriptive-title-with-dashes.md` where `N` increments
per ADR landed on a given date (1, 2, 3…).

## Cutover Note

The 3.x track formally exists from this commit forward. ADRs landed before
this restructuring that thematically belong to 3.x architecture (e.g. the
shared-package-boundary cutover, mission-identity-uses-ULID, retrospective
gate work) were moved here with their history preserved via `git mv`.

## See Also

- [3.x ADR Index](../adr/3.x/README.md)
- [2.x README](README-2.x.md) — prior architecture track
- [Top-level architecture README](README.md)
- [Shared ADR template](adr-template.md)

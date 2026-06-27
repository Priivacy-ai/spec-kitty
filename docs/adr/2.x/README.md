# 2.x ADRs

Architectural Decision Records for the 2.x track. **Not the current track —
see [`architecture/3.x/adr/`](../../3.x/adr/README.md) for current decisions.**

## Naming

- `YYYY-MM-DD-N-descriptive-title-with-dashes.md`

## Source of Truth

This folder is canonical for 2.x decisions (dates before 2026-03-30, the
3.0.0 release). ADRs dated on or after 2026-03-30 were moved to
[`architecture/3.x/adr/`](../../3.x/adr/README.md); back-compat symlinks at
the old `architecture/2.x/adr/<filename>` paths point at the new location so
existing references in CHANGELOG entries, test snapshots, and shipped docs
continue to resolve.

Legacy links through `architecture/adrs/` are 1.x compatibility aliases.

## Status Conventions

- `Accepted` means the decision remains current policy.
- `Superseded` means a newer ADR replaced the decision; keep the file for history, but do not implement from it.
- `Deprecated` means the direction is in active retirement and should not receive new work.

# 2.x ADRs

Architectural Decision Records for the 2.x track. **Not the current track —
see [`docs/adr/3.x/`](../3.x/README.md) for current decisions.**

## Naming

- `YYYY-MM-DD-N-descriptive-title-with-dashes.md`

## Source of Truth

This folder is canonical for 2.x decisions (dates before 2026-03-30, the
3.0.0 release). ADRs dated on or after 2026-03-30 were moved to
[`docs/adr/3.x/`](../3.x/README.md). The `architecture/` tree was removed by the
Common Docs structural move (PR #2225); existing references using the old
`architecture/2.x/adr/<filename>` or `architecture/adrs/` paths will need
updating to the new `docs/adr/` paths.

## Status Conventions

- `Accepted` means the decision remains current policy.
- `Superseded` means a newer ADR replaced the decision; keep the file for history, but do not implement from it.
- `Deprecated` means the direction is in active retirement and should not receive new work.

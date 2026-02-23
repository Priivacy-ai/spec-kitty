# 2.x ADR Coverage

## Audit Summary

A fresh-clone audit compared `architecture/adrs/` against current 2.x code surfaces.

Result:

1. Runtime and status/event areas were already covered by ADRs.
2. Doctrine artifact governance and living glossary architecture were implemented but undocumented.
3. This gap is closed by new ADRs dated `2026-02-23`.

## Coverage Matrix

| Code Surface | ADR Coverage |
|---|---|
| `src/specify_cli/runtime/*` and canonical `next` loop | `2026-02-17-1`, `2026-02-17-2`, `2026-02-17-3` |
| Status/event-lifecycle model | `2026-02-09-1` through `2026-02-09-4` |
| Doctrine artifact model (`src/doctrine/**`, constitution compiler/commands) | `2026-02-23-1` |
| Living glossary model (`glossary/**`, glossary hook integration) | `2026-02-23-2` |
| Versioned docs strategy (`docs/1x`, `docs/2x`, docs workflow) | `2026-02-23-3` |

## New ADR Files Added in This Update

1. `architecture/adrs/2026-02-23-1-doctrine-artifact-governance-model.md`
2. `architecture/adrs/2026-02-23-2-living-glossary-context-and-curation-model.md`
3. `architecture/adrs/2026-02-23-3-versioned-1x-2x-docs-site-without-hosted-platform-scope.md`

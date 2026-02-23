# Architecture Navigation Guide

Use this guide to quickly locate the right ADR set.

## Fast Paths

### Need the full ADR list?

```bash
ls -1 architecture/adrs | sort
```

### Need doctrine/glossary decisions?

1. `architecture/adrs/2026-02-23-1-doctrine-artifact-governance-model.md`
2. `architecture/adrs/2026-02-23-2-living-glossary-context-and-curation-model.md`
3. `architecture/adrs/2026-02-23-3-versioned-1x-2x-docs-site-without-hosted-platform-scope.md`

### Need mission runtime / `next` decisions?

1. `architecture/adrs/2026-02-17-1-canonical-next-command-runtime-loop.md`
2. `architecture/adrs/2026-02-17-2-runtime-owned-mission-discovery-loading.md`
3. `architecture/adrs/2026-02-17-3-events-contract-parity-and-vendor-deprecation.md`

### Need status/event model decisions?

1. `architecture/adrs/2026-02-09-1-canonical-wp-status-model.md`
2. `architecture/adrs/2026-02-09-2-wp-lifecycle-state-machine.md`
3. `architecture/adrs/2026-02-09-3-event-log-merge-semantics.md`
4. `architecture/adrs/2026-02-09-4-cross-repo-evidence-completion.md`

## Reading Workflow

1. Read the ADR for rationale and tradeoffs.
2. Follow code references in that ADR.
3. Confirm behavior in tests.

## Writing Workflow

1. Copy `architecture/adr-template.md`.
2. Capture one architectural decision per ADR.
3. Add concrete code/test references.
4. Keep accepted ADRs immutable; supersede with a new ADR if a decision changes.

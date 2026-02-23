# Architecture Documentation

This directory is the canonical ADR corpus for Spec Kitty.

## Purpose

ADRs in `architecture/adrs/` record architectural decisions, alternatives, and consequences.  
Implementation details live in code and tests; ADRs capture why.

## Current 2.x Coverage Highlights

| Area | ADRs |
|---|---|
| Runtime mission loop and discovery | [2026-02-17-1](adrs/2026-02-17-1-canonical-next-command-runtime-loop.md), [2026-02-17-2](adrs/2026-02-17-2-runtime-owned-mission-discovery-loading.md), [2026-02-17-3](adrs/2026-02-17-3-events-contract-parity-and-vendor-deprecation.md) |
| Status model and event semantics | [2026-02-09-1](adrs/2026-02-09-1-canonical-wp-status-model.md), [2026-02-09-2](adrs/2026-02-09-2-wp-lifecycle-state-machine.md), [2026-02-09-3](adrs/2026-02-09-3-event-log-merge-semantics.md), [2026-02-09-4](adrs/2026-02-09-4-cross-repo-evidence-completion.md) |
| Doctrine/governance model | [2026-02-23-1](adrs/2026-02-23-1-doctrine-artifact-governance-model.md) |
| Living glossary model | [2026-02-23-2](adrs/2026-02-23-2-living-glossary-context-and-curation-model.md) |
| Versioned docs strategy | [2026-02-23-3](adrs/2026-02-23-3-versioned-1x-2x-docs-site-without-hosted-platform-scope.md) |

## ADR Naming

- Path: `architecture/adrs/`
- Format: `YYYY-MM-DD-N-descriptive-title-with-dashes.md`
- `N` increments within the same day.

## ADR Lifecycle

1. Create ADR as `Proposed`.
2. Review and either accept or replace.
3. After acceptance, do not mutate decision history; supersede with a new ADR if needed.

## Creating a New ADR

```bash
cp architecture/adr-template.md architecture/adrs/YYYY-MM-DD-N-your-decision.md
```

Then fill context, options, outcome, and consequences. Keep it concise and include direct code/test references.

## Find ADRs

```bash
ls -1 architecture/adrs | sort
rg -n "Status:|Decision Outcome|Technical Story" architecture/adrs
```

See also:

- `architecture/ARCHITECTURE_DOCS_GUIDE.md`
- `architecture/NAVIGATION_GUIDE.md`

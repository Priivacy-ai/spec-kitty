# Architecture Navigation Guide

Use this guide to quickly locate the right architecture artifact set.

## Fast Paths

### Need full ADR lists?

```bash
ls -1 architecture/1.x/adr | sort
ls -1 architecture/2.x/adr | sort
```

### Need the 2.x architecture model?

1. `architecture/2.x/README.md#domain-breakdown`
2. `architecture/2.x/01_context/README.md`
3. `architecture/2.x/02_containers/README.md`
4. `architecture/2.x/03_components/README.md`

### Need architecture audience/personas?

1. `architecture/audience/README.md`
2. `architecture/audience/internal/README.md`
3. `architecture/audience/external/README.md`

### Need doctrine/glossary decisions (2.x)?

1. `architecture/2.x/adr/2026-02-23-1-doctrine-artifact-governance-model.md`
2. `architecture/2.x/adr/2026-02-23-2-living-glossary-context-and-curation-model.md`
3. `architecture/2.x/adr/2026-02-23-3-versioned-1x-2x-docs-site-without-hosted-platform-scope.md`

### Need mission runtime and `next` decisions (2.x)?

1. `architecture/2.x/adr/2026-02-17-1-canonical-next-command-runtime-loop.md`
2. `architecture/2.x/adr/2026-02-17-2-runtime-owned-mission-discovery-loading.md`
3. `architecture/2.x/adr/2026-02-17-3-events-contract-parity-and-vendor-deprecation.md`

### Need status/event model decisions (2.x)?

1. `architecture/2.x/adr/2026-02-09-1-canonical-wp-status-model.md`
2. `architecture/2.x/adr/2026-02-09-2-wp-lifecycle-state-machine.md`
3. `architecture/2.x/adr/2026-02-09-3-event-log-merge-semantics.md`
4. `architecture/2.x/adr/2026-02-09-4-cross-repo-evidence-completion.md`

### Need user journey artifacts (2.x)?

1. `architecture/2.x/user_journey/`
2. `architecture/2.x/user_journey/README.md`

## Reading Workflow

1. Read domain breakdown for responsibility boundaries.
2. Read C4 context, container, and component docs in order.
3. Check relevant audience personas for stakeholder intent.
4. Read ADRs for rationale and tradeoffs.
5. Confirm behavior in code and tests.

## Writing Workflow

1. Copy `architecture/adr-template.md` for new decisions.
2. Keep one architectural decision per ADR.
3. Update domain/C4 docs when responsibilities or behavior contracts change.
4. If actor personas are referenced in journeys, link to `architecture/audience/internal/` or `architecture/audience/external/`.
5. Keep accepted ADRs immutable; supersede with a new ADR if needed.

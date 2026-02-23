# Architecture ADR Guide

## Scope

Architecture docs in this repository are ADR-first:

- `architecture/adrs/` contains decision records.
- Code/tests contain implementation detail.

## What Belongs in an ADR

Create an ADR when a change:

1. Selects between meaningful architectural alternatives.
2. Affects multiple components or system behavior over time.
3. Needs preserved rationale for future maintainers.

Do not create ADRs for routine bug fixes or low-impact implementation details.

## ADR Structure

Use `architecture/adr-template.md` and include:

1. Context/problem statement.
2. Decision drivers.
3. Considered options.
4. Decision outcome.
5. Consequences.
6. Confirmation signals.
7. Code/test references.

## Quality Bar

An ADR is complete when:

1. The decision is explicit and testable.
2. Alternatives and tradeoffs are documented.
3. Referenced paths exist in repo.
4. Scope boundaries are clear.

## Lifecycle

1. Start as `Proposed`.
2. Review and accept.
3. Keep accepted ADRs immutable.
4. If the decision changes, publish a superseding ADR.

## Useful Commands

```bash
ls -1 architecture/adrs | sort
rg -n "Status:|Decision Outcome|Consequences" architecture/adrs
```

## Current 2.x Gaps Closed in This Cycle

1. Doctrine artifact/governance model ADR.
2. Living glossary model ADR.
3. Versioned 1.x/2.x docs-site strategy ADR.

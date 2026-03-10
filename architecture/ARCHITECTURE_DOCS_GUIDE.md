# Architecture Documentation Guide

## Scope

Architecture documentation is versioned:

- `architecture/1.x/` for legacy architecture and ADRs
- `architecture/2.x/` for current architecture and ADRs
- `architecture/adrs/` as legacy compatibility aliases to moved ADR files
- `architecture/audience/` for persona references used by architecture journeys
  - `architecture/audience/internal/` for internal contributors/runtime actors
  - `architecture/audience/external/` for external stakeholders

Code and tests remain the source of implementation detail.

## 2.x Modeling Layers

1. Domain responsibility model: `architecture/2.x/README.md#domain-breakdown`
2. C4 context boundary: `architecture/2.x/01_context/README.md`
3. C4 container responsibilities: `architecture/2.x/02_containers/README.md`
4. C4 component behavior: `architecture/2.x/03_components/README.md`

## Audience and Persona Rule

When a user-journey actor table includes a Persona value, it must link to a file
under `architecture/audience/`.

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
ls -1 architecture/1.x/adr | sort
ls -1 architecture/2.x/adr | sort
rg -n "Status:|Decision Outcome|Consequences" architecture/1.x/adr architecture/2.x/adr
```

## Track Assignment Rules

Use `architecture/1.x/adr/` when the decision documents 1.x behavior.

Use `architecture/2.x/adr/` when the decision documents 2.x behavior.

If a decision spans both tracks, place it in the active track and cross-reference from the other track.

## 2.x Gaps Closed in This Cycle

1. Doctrine artifact/governance model ADR.
2. Living glossary model ADR.
3. Versioned 1.x/2.x docs-site strategy ADR.
4. Domain + C4 responsibility alignment and audience persona linkage.

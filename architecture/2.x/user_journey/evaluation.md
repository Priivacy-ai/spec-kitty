# 2.x User Journey Evaluation

Date: 2026-02-28

## Scope

This evaluation compares:

1. Canonical user journeys imported from `develop` into `architecture/2.x/user_journey/`
2. Exploratory user journeys from the brainstorm corpus in `architecture/2.x/initiatives/2026-02-architecture-discovery-and-restructure/user_journey/`

## Assessment

1. Canonical set (this directory):
   - Broad system lifecycle coverage
   - Better fit for long-lived architecture narrative
   - Status remains `DRAFT` pending explicit ADR-backed adoption
2. Brainstorm set (initiative-scoped):
   - High-value exploration of ad-hoc specialist and formalization flows
   - Useful for mission evolution and governance experiments
   - Not yet stable enough for canonical architecture baseline

## Decision

1. Keep canonical journeys in `architecture/2.x/user_journey/`.
2. Keep brainstorm journeys initiative-scoped until they are:
   - reconciled with current runtime architecture,
   - mapped to explicit ADR decisions,
   - and accepted as stable behavior.

# 2.x Documentation (Current Track)

`2.x` is the current architecture track, centered on doctrine-backed governance,
living glossary semantics, and runtime-owned mission execution.

## Key 2.x Shifts

1. Doctrine artifacts are typed and schema-validated under `src/doctrine/`.
2. Charter generation uses interview answers plus doctrine catalog selection.
3. Glossary is context-owned (`glossary/contexts/*.md`) and integrated into mission execution through glossary hooks.
4. Runtime loop and mission discovery are driven by canonical `next` and runtime precedence rules.

## Start Here

1. [Doctrine and Charter](doctrine-and-charter.md)
2. [Glossary System](glossary-system.md)
3. [Runtime and Missions](runtime-and-missions.md)
4. [Orchestration and API Boundary](orchestration-and-api.md)
5. [ADR Coverage](adr-coverage.md)

## Architecture Repository Layout

- 2.x domain map: `architecture/2.x/README.md#domain-breakdown`
- 2.x C4 docs: `architecture/2.x/01_context/`, `architecture/2.x/02_containers/`, `architecture/2.x/03_components/`
- 2.x ADRs: `architecture/2.x/adr/`
- 2.x user journeys: `architecture/2.x/user_journey/`
- architecture personas: `architecture/audience/`

# Contracts

This mission is an internal-CLI bug-fix cluster (sync layout / event-journal capture).
It introduces **no external API, webhook, or network contract** — all surfaces are
in-process Python (layout resolution, cutover engine reuse, emitter capture flag,
backfill command). The behavioral contracts live in `data-model.md` (layout state
machine + invariants INV-1..6) and the per-WP acceptance scenarios in `spec.md`.

No OpenAPI/GraphQL/schema artifacts apply.

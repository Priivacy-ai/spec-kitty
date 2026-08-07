# Decision Moment `01KZ9Q2DC9WX6GTJZ57GE0BZNM`

- **Mission:** `docs-seo-metadata-enforcement-01KZ9PJ2`
- **Origin flow:** `plan`
- **Slot key:** `plan.adr.exemption-retirement`
- **Input key:** `adr_exemption_retirement`
- **Status:** `resolved`
- **Created:** `2026-08-05T19:40:39.689692+00:00`
- **Resolved:** `2026-08-05T19:45:42.412019+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

How far should the existing docs/adr/ frontmatter exemptions be retired?

## Options

- Narrowly: description only
- Fully: retire all ADR frontmatter exemptions

## Final answer

Narrowly: description only. Remove docs/adr/ from the description gate exclusion and fix its stale byte-invariance comment; leave all other ADR frontmatter exemptions intact (DIRECTIVE_024 locality of change).

## Rationale

_(none)_

## Change log

- `2026-08-05T19:40:39.689692+00:00` — opened
- `2026-08-05T19:45:42.412019+00:00` — resolved (final_answer="Narrowly: description only. Remove docs/adr/ from the description gate exclusion and fix its stale byte-invariance comment; leave all other ADR frontmatter exemptions intact (DIRECTIVE_024 locality of change).")

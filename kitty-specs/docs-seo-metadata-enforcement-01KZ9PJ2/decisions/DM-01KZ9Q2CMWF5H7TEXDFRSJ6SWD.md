# Decision Moment `01KZ9Q2CMWF5H7TEXDFRSJ6SWD`

- **Mission:** `docs-seo-metadata-enforcement-01KZ9PJ2`
- **Origin flow:** `plan`
- **Slot key:** `plan.enforcement.gate-layer`
- **Input key:** `enforcement_gate_layer`
- **Status:** `resolved`
- **Created:** `2026-08-05T19:40:38.940659+00:00`
- **Resolved:** `2026-08-05T19:47:01.791379+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should metadata enforcement run as a source-level gate, a built-output gate, or both?

## Options

- Both: source gate at PR time plus built-output assertion in the pages build
- Source-level only
- Built-output only

## Final answer

Both layers, plus add a paths: filter to docs-freshness.yml. Source gate blocks at PR time; built-output assertion runs in docs-pages.yml (already path-scoped). Paths filter is safe because branch protection requires only drift-detector, so a skipped docs-freshness cannot deadlock a PR. Filter must cover docs/**, scripts/docs/**, the common-docs styleguide asset, and the workflow file itself.

## Rationale

_(none)_

## Change log

- `2026-08-05T19:40:38.940659+00:00` — opened
- `2026-08-05T19:47:01.791379+00:00` — resolved (final_answer="Both layers, plus add a paths: filter to docs-freshness.yml. Source gate blocks at PR time; built-output assertion runs in docs-pages.yml (already path-scoped). Paths filter is safe because branch protection requires only drift-detector, so a skipped docs-freshness cannot deadlock a PR. Filter must cover docs/**, scripts/docs/**, the common-docs styleguide asset, and the workflow file itself.")

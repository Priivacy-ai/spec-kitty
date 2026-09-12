# Exemption registry (R-014) — one mechanism per file

Each `*.md` file here is ONE enumerated filename-based exemption mechanism, parsed by
`tests/architectural/test_exemption_registry_ratchet.py`. The **per-mechanism-file**
layout is deliberate (squad-mandated): a retirement WP deletes *only its own* row file
and never collides with a sibling retirement editing a shared file — the plan's stated
reason for rejecting golden-count mode.

The registry **only shrinks**. It is pre-populated at WP10 landing with every mechanism
(`status: expected-present`); each later retirement WP (WP11–WP17) routes its mechanism
onto the owner `is_toolchain_generated_churn`, whereupon the mechanism's literal/symbol
vanishes from `src/` and the ratchet's overcount / symbol-presence arm goes RED until
the row file is deleted (red → green per retirement). The registry reaches zero rows
(IC-08 / SC-004).

## Row format (parsed fields)

```
- mechanism: `<canonical name — must equal the file stem>`
- module: `src/<path to the module that defines it>`
- literals: `<A>`, `<B>`   (or `(none)` for a function/field-only mechanism)
- symbol: `<def / field / variable name asserted present in module>`
- retirement-wp: `WP##`
- retirement-ref: `IC-07x`
- owner-route: `is_toolchain_generated_churn`
- status: `expected-present`
```

- **literals** are the R-014 filename-collections (frozenset / tuple / compiled-regex of
  filenames / basenames / suffixes / path-prefixes) the mechanism owns. The negative
  scan asserts no such collection exists *outside* the enumerated rows.
- A mechanism with no literal of its own (a predicate that consults a shared authority,
  a threaded variable, or a dead field) carries `literals: (none)` and is held present
  by the `symbol` presence check instead.

## Adding a row (only for a genuine, justified new mechanism)

Adding a new filename-based exemption is normally **refused** by the anti-ninth ratchet
(C9) — route the classification through `is_toolchain_generated_churn` instead. Add a
row here *only* when a genuine, justified mechanism is unavoidable, and record the
justification in the row's prose.

## `status` vocabulary

- `expected-present` — still-to-retire; the landing default for every WP10 row.
- `justified-survivor` — a genuine must-keep mechanism that cannot route onto the
  owner without a behaviour change (e.g. it is diff-scoped, not kind-scoped). Added
  by a retirement WP when it determines a sibling mechanism cannot be fully retired;
  the row records WHY in its prose so the survivor is explicit, never silent (plan.md
  "never a silent survivor"). A `justified-survivor` row is still held accountable by
  the symbol-presence / literal overcount arms exactly like `expected-present`.

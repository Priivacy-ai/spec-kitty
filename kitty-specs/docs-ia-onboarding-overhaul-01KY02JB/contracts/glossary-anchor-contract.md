# Contract: Glossary Per-Term Anchors

**Owner**: `scripts/docs/generate_kitty_specs_docs.py` (`glossary_page()`)
**Consumers**: `scripts/docs/glossary_linker.py`, any doc page linking directly to a term.
**Requirement**: FR-012

## Input

The existing `.kittify/glossaries/spec_kitty_core.yaml` seed — no schema change to input.
Each entry: `{surface: str, definition: str, confidence: float, status: str}`.

## Output change

`glossary_page()`'s rendered HTML gains one attribute per term card that does not exist today:

```html
<div class="glossary-card" id="term-{anchor_id}" data-surface="{surface}">
  ...
</div>
```

- `anchor_id` = lowercase, ASCII-only, hyphen-separated slug of `surface`
  (e.g. `"branch strategy gate"` → `"branch-strategy-gate"`).
- Collision rule: if two terms slugify to the same `anchor_id` (not expected with the current
  104 terms, but must be handled), append a numeric suffix (`-2`, `-3`, ...) in seed-file order.

## Guarantee

`https://docs.spec-kitty.ai/kitty-specs/glossary.html#term-{anchor_id}` resolves to (scrolls to
or highlights) the correct card for every term, for the lifetime of that term's `surface` value.
Renaming a `surface` value changes its `anchor_id` — out of scope for this mission to solve
generally (no alias/redirect layer for glossary anchors; C-003).

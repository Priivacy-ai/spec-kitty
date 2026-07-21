# Contract: Glossary Term Linker

**Owner**: new `scripts/docs/glossary_linker.py`
**Requirement**: FR-011, NFR-004
**Pipeline position**: Runs after DocFX renders HTML, in the same build stage grouping as
`scripts/docs/seo_postprocess.py` — a post-processing pass over `_site/**/*.html`, not a
markdown transform.

## Input

- `.kittify/glossaries/spec_kitty_core.yaml` (term list, with `anchor_id` per the
  glossary-anchor-contract).
- Rendered HTML files under the DocFX output directory.

## Behavior

For each rendered doc page (excluding `kitty-specs/glossary.html` itself):

1. Walk the page's text nodes, skipping `<code>`, `<pre>`, `<script>`, `<style>`, and any
   existing `<a>` tag's inner text.
2. Match glossary `surface` strings case-insensitively, **longest match first** (a term whose
   surface is a substring of a longer term never pre-empts the longer match).
3. On the **first** match of a given term on that page, wrap it:
   ```html
   <a href="/kitty-specs/glossary.html#term-{anchor_id}"
      class="glossary-link"
      title="{definition, HTML-escaped}">{original matched text}</a>
   ```
4. Every subsequent occurrence of the same term on the same page is left untouched (NFR-004).

## Output

Modified HTML files, written back in place. No markdown source file is ever touched
(plan-phase decision, Decision Moment `01KY03YGX7GQEBKV45Q2Q8FXK3`).

## Failure mode

If the glossary seed fails to parse or a term's `anchor_id` is missing, the linker logs a
warning and skips linking for that term rather than failing the whole docs build (a broken
glossary link is a UX bug, not a publish-blocking error) — consistent with this being a
content-enhancement pass, not a correctness gate (that role belongs to the canonical-term-check
contract below).

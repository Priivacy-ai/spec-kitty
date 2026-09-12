# Contract: Built-Output Verifier

**Modules**: `scripts/docs/seo_verify.py` (new), `scripts/docs/seo_postprocess.py` (modified)
**Concern**: IC-03
**Requirements**: FR-001, FR-005, FR-008, FR-010, FR-011, FR-012

Asserts against the rendered `docs/_site`. This is the only layer that can observe a render-path defect — frontmatter can be perfectly correct while the emitted HTML omits the tag entirely, which is exactly today's state for 147 pages.

---

## Part 1 — `seo_postprocess.py` change

### C-B1 — Emit a description tag (FR-005)

Today `seo_postprocess.py` **reads** a description (`extract_description()`) and uses it for Open Graph, Twitter, and structured data — but never writes a `<meta name="description">`. When DocFX emits none (no frontmatter `description`), the published page ships with none.

The SEO block gains:

```html
<meta name="description" content="{escaped_desc}">
```

emitted **only** when the page has no description tag already, so DocFX's own output stays authoritative where present (single canonical authority — the frontmatter is the author's intent; this is a backstop, not an override).

### C-B2 — Idempotence

The existing `SEO_BLOCK_RE` strip-then-reinsert cycle must remain idempotent. Running the post-processor twice produces identical output. A test asserts this directly — the block is delimited by `<!-- spec-kitty-seo:start -->` / `:end`, and duplicate injection would silently double every tag.

### C-B3 — Fallback stays visible

The boilerplate fallback remains as a last resort but must be **detectable** so the source gate can flag it (C-S3). Do not make the fallback indistinguishable from an authored description — that would let the backstop mask the defect it exists to reveal.

---

## Part 2 — `seo_verify.py` (new)

### Public surface

```
python3 scripts/docs/seo_verify.py --site-dir docs/_site [--strict] [--json REPORT]
```

| Flag | Behaviour |
|---|---|
| *(none)* | Report-only, exit 0 |
| `--strict` | Exit non-zero on any violation |
| `--json PATH` | Write the `AuditRecord` (FR-001) |

Mirrors the exit contract of `description_length_check.py` and `related_validator.py`.

### C-B4 — Reuse the indexability predicate (I-08)

Classification imports `seo_postprocess.should_index()`. It does **not** reimplement the rule. A second definition of "indexable" would recreate the two-authorities bug this mission exists to fix, one module over.

### C-B5 — Rules applied to indexable pages only

| Rule | Assertion |
|---|---|
| V-06 | `<meta name="description">` present |
| V-07 | Not the boilerplate fallback |
| V-08 | `<link rel="canonical">` equals the page's own canonical address |
| V-09 | `og:title` matches `<title>`; `og:description` matches the description |
| V-10 | Description unique across all indexable pages |

Titles: non-empty and not equal to the bare site default (NFR-001).

### C-B6 — Stub and sitemap invariants (FR-012, I-09)

- Every `REDIRECT_STUB` carries `noindex`.
- No stub address appears in `sitemap.xml`.
- Sitemap entries and indexable pages are the same set.
- **The verifier never mutates `_site`.** It is read-only. A tool that can fix what it checks can pass itself.

### C-B7 — Deterministic output (I-06)

Violations sorted by path. Two runs over identical input produce byte-identical reports. Follows the inventory lockfile's established convention.

### C-B8 — Records the stale-URL finding (FR-011)

The audit report includes a section noting that the two addresses named in issue #1652 are pre-move addresses now served as stubs, with their current addresses verified. This is what lets the issue be closed on evidence rather than assertion.

---

## Part 3 — Workflow integration

### C-B9 — Step position is load-bearing (R-009)

`docs-pages.yml` order becomes:

```
docfx build
  → seo_postprocess.py          (injects SEO; stubs do not exist yet)
  → glossary_linker.py
  → redirect_stub_generator.py generate
  → redirect_stub_generator.py coverage
  → seo_verify.py --strict      ← NEW, last
  → upload artifact
```

The verifier runs **last** so it observes the final artifact including stubs, and can assert stubs are correctly excluded (C-B6). Placing it before stub generation would leave stub regressions unobserved. The existing ordering comments in the workflow explain why SEO and glossary injection precede stub generation — that ordering is not to be disturbed.

### C-B10 — Blocking

Runs with `--strict`, so a metadata regression fails the build **before** `upload-pages-artifact`. A defect must not reach the deployed site.

---

## Test contract (`tests/docs/test_seo_verify.py`)

| Test | Asserts |
|---|---|
| `test_missing_description_is_red` | Indexable page without the tag → violation (V-06) |
| `test_boilerplate_description_is_red` | Fallback string → violation (V-07) |
| `test_wrong_canonical_is_red` | Canonical pointing elsewhere → violation (V-08) |
| `test_og_mismatch_is_red` | `og:description` diverging from description → violation (V-09) |
| `test_duplicate_description_is_red` | Two indexable pages sharing a description → both flagged (V-10) |
| `test_stub_is_not_indexable` | Refresh-stub markup classifies as `REDIRECT_STUB`, rules skipped |
| `test_stub_absent_from_sitemap` | No stub address in the sitemap (C-B6) |
| `test_verifier_does_not_mutate_site` | Input tree byte-identical after a run (C-B6) |
| `test_clean_site_is_green` | Fully compliant fixture → zero violations, exit 0 |
| `test_strict_exits_nonzero` | Exit contract (C-B10) |
| `test_report_is_deterministic` | Two runs byte-identical (C-B7) |
| `test_postprocess_emits_description` | Page with no description tag gains one (C-B1) |
| `test_postprocess_preserves_existing_description` | Existing DocFX description not overwritten (C-B1) |
| `test_postprocess_is_idempotent` | Two passes produce identical output (C-B2) |

All operate on synthetic `_site` fixtures under `tmp_path` — no DocFX build required, so these stay in the fast tier despite testing build output.

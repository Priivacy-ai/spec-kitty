# Phase 1 Data Model: Docs SEO Metadata Audit and Enforcement

**Mission**: `docs-seo-metadata-enforcement-01KZ9PJ2`
**Date**: 2026-08-05

This mission has no database. Its "data model" is the set of value objects that flow between the resolver, the source gate, and the built-output verifier, plus the invariants those objects must satisfy. Modelling them explicitly is what keeps the three concerns independently testable (DIRECTIVE_001).

---

## Entities and Value Objects

### `PublishedPageSet` (value object, produced by IC-01)

The authoritative answer to "which source pages are published".

| Field | Type | Description |
|---|---|---|
| `pages` | `frozenset[Path]` | Repo-relative paths of published Markdown source pages |
| `source_globs` | `tuple[str, ...]` | The `build.content` glob patterns read from `docs/docfx.json`, retained for diagnostics |
| `exclusions` | `tuple[Exclusion, ...]` | Explicitly enumerated exclusions, each with a reason (FR-013) |

**Invariants**

- **I-01 (non-vacuous)**: `len(pages) > 0`. An empty set is always an error, never a pass. This is the single invariant whose absence caused the current defect.
- **I-02 (floor)**: `len(pages)` must exceed a committed realistic floor. A resolver that silently under-collects — the exact failure being repaired — must fail loudly rather than shrink quietly.
- **I-03 (single authority)**: `source_globs` is read from `docs/docfx.json` at call time. It is never duplicated into a constant in a consuming module.
- **I-04 (explicit exclusions)**: every path excluded from `pages` is attributable to a member of `exclusions`. No path is dropped by an unstated glob gap.

### `Exclusion` (value object)

| Field | Type | Description |
|---|---|---|
| `pattern` | `str` | Path prefix or glob being excluded |
| `reason` | `str` | Why — e.g. "immutable legacy snapshot (C-005)", "generated, no human author" |

**Invariant I-05**: `reason` is non-empty. An exclusion without a stated reason is indistinguishable from an oversight, which is the failure mode FR-013 exists to prevent.

### `PageMetadata` (value object, source side)

Extracted from a source page's frontmatter.

| Field | Type | Description |
|---|---|---|
| `path` | `Path` | Repo-relative source path |
| `title` | `str \| None` | Frontmatter `title` |
| `description` | `str \| None` | Frontmatter `description` |

**Validation rules**

| Rule | Requirement | Source |
|---|---|---|
| V-01 | `title` present and non-blank | NFR-001 |
| V-02 | `description` present and non-blank | NFR-002 |
| V-03 | `50 <= len(description) <= 180`, inclusive | NFR-003, C-003 |
| V-04 | `description` is not the boilerplate fallback string | FR-006 |
| V-05 | `description` is unique across the published set | FR-007, NFR-004 |

V-01–V-03 already exist. **V-04 and V-05 are net-new** and are the two rules that make the gate meaningfully stronger rather than merely wider.

### `RenderedPage` (value object, built-output side)

Extracted from a file in `docs/_site`.

| Field | Type | Description |
|---|---|---|
| `relative_path` | `str` | POSIX path within `_site` |
| `classification` | `PageClass` | See state model below |
| `title` | `str \| None` | From `<title>` |
| `description` | `str \| None` | From `<meta name="description">` |
| `canonical` | `str \| None` | From `<link rel="canonical">` |
| `og_title` / `og_description` | `str \| None` | Open Graph values |

**Validation rules** (applied only when `classification is INDEXABLE`)

| Rule | Requirement | Source |
|---|---|---|
| V-06 | `description` is present — a rendered page with no description tag is a defect regardless of its frontmatter | FR-005, NFR-002 |
| V-07 | `description` is not the boilerplate fallback | FR-006 |
| V-08 | `canonical` equals this page's own canonical address | FR-008 |
| V-09 | `og_title == title` and `og_description == description` | FR-008 |
| V-10 | `description` unique across all indexable rendered pages | FR-007, NFR-004 |

V-06 is the rule that catches the render-path defect invisible to source checks.

### `AuditRecord` (aggregate, produced by IC-03)

The reproducible evidence artifact satisfying FR-001 and FR-010.

| Field | Type | Description |
|---|---|---|
| `pages` | `tuple[RenderedPage, ...]` | One entry per built page |
| `violations` | `tuple[Violation, ...]` | Rule failures, sorted by path for deterministic diffs |
| `counts` | `mapping` | Totals per classification |

**Invariant I-06 (determinism)**: two runs over identical input produce byte-identical output. Sorting by path is mandatory — this follows the precedent already set by the inventory lockfile and the description gate's report.

### `Violation` (value object)

| Field | Type | Description |
|---|---|---|
| `path` | `str` | Offending page |
| `rule` | `str` | Which of V-01..V-10 failed |
| `detail` | `str \| None` | Observed value or length |
| `peer` | `str \| None` | For V-05/V-10, the other page sharing the description |

**Invariant I-07**: a duplicate violation names **both** pages. A uniqueness failure reporting only one side is not actionable — the author cannot tell what they collided with.

---

## State Model: page classification

Every built page resolves to exactly one class. This classification is the single decision that determines whether the metadata rules apply.

```
                    ┌───────────────┐
   built page ────► │  classify     │
                    └───────┬───────┘
                            │
        ┌───────────────┬───┴────────┬───────────┬──────────────┐
        ▼               ▼            ▼           ▼              ▼
   INDEXABLE      REDIRECT_STUB   TOC_PAGE    ASSET         NOINDEX
   (rules apply)  (noindex,       (noindex,   (not HTML,    (explicit
                   FR-012)         robots-     skipped)      robots:
                                   disallow)                 noindex)
```

**Classification predicate** — reuse `seo_postprocess.should_index()` rather than reimplement:

| Class | Predicate |
|---|---|
| `ASSET` | path starts with `assets/` |
| `TOC_PAGE` | basename is `toc.html` |
| `REDIRECT_STUB` | markup contains `http-equiv="refresh"` |
| `NOINDEX` | an otherwise-ordinary page carrying an explicit `robots: noindex` directive |
| `INDEXABLE` | none of the above, and no existing `noindex` robots directive |

> **Amended during implementation (WP05).** This model originally named four classes.
> Defining `INDEXABLE` as "none of the above **and** no existing noindex directive" left an
> ordinary page carrying an explicit `robots: noindex` with no bucket to land in — a real
> misconfiguration that would have been silently mislabelled as one of its neighbours. The
> fifth member exists so that case is named rather than absorbed. Accepted by WP05's
> reviewer on those merits; recorded here so the doc and the enum agree.

**Invariant I-08 (no second definition)**: the verifier does not define its own notion of indexability. `should_index()` is the existing working authority; a second definition would be exactly the two-authorities bug this mission repairs, reintroduced one module over.

**Invariant I-09 (stubs stay out)**: a `REDIRECT_STUB` never becomes `INDEXABLE`, never appears in the sitemap, and its markup is not modified by the verifier (FR-012).

---

## Relationships

```
docs/docfx.json
      │ (read at call time — never copied into a constant)
      ▼
PublishedPageSet ──────┬──────────────────────┐
      │                │                      │
      ▼                ▼                      ▼
 source gate      coverage assertion    built-output verifier
 (V-01..V-05)     (I-01, I-02)          (V-06..V-10)
      │                                       │
      ▼                                       ▼
  Violation[]                           AuditRecord
```

The resolver knows nothing about its consumers. Both gates depend on it; neither depends on the other. That is what allows IC-02 and IC-03 to proceed in parallel once IC-01 lands.

---

## Derived quantities (current measured baseline)

Recorded so the implementer can detect drift between planning and execution.

| Quantity | Value at planning time |
|---|---|
| Published Markdown source pages | 674 |
| Pages with `title` + `description` | 527 |
| Pages lacking `description` | 147 (all under `docs/adr/`) |
| Pages lacking frontmatter entirely | 3 (ADR README files) |
| Pages lacking `title` | 0 |
| Pages currently covered by `test_docs_seo.py` | 16 |
| Coverage ratio | 2.4% |

If the implementer measures materially different numbers, planning assumptions have drifted and should be re-checked before proceeding.

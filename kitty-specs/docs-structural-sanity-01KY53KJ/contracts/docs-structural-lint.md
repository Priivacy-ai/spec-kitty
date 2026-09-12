# Contract — `scripts/docs/docs_structural_lint.py` (FR-007, FR-008, FR-011)

The durable successor to the retired anti-sprawl ratchet. Contract-level behaviour the implementation and its tests must satisfy. Every check is **scoped so the current clean tree passes with zero violations** (NFR-003) — the guard catches drift, it does not force churn on correctly-placed files.

## Invocation

```
python -m scripts.docs.docs_structural_lint [--json] [DOCS_ROOT=docs]
```

- Exit `0` when no violations; exit non-zero when any violation exists (CI gate role, FR-008; wired into `.github/workflows/docs-freshness.yml`).
- `--json` emits `{"violations": [{rule_id, path, message}], "checked": <int>}`.
- Completes in **< 5 s** on the current tree (NFR-003).

## Checks (each independently testable — SC-003; each scoped to pass the clean tree)

| rule_id | Fails when | Scope / exemptions (so the clean tree passes) | Message names |
|---|---|---|---|
| `index_completeness` | a non-index page in a **curated-complete** section is absent from that section's `index.md` | ONLY sections the styleguide config marks "curated-complete" (initially `architecture/` only); every other section index is a landing page and is exempt. Growing to all 13 sections is explicitly out of scope. | the missing page + its section index |
| `point_in_time_placement` | a file whose name matches a dated pattern (`^\d{4}-\d{2}`) or self-declares point-in-time/closeout lives outside `plans/**` and is not allowlisted | canonical home is `plans/**` **broadly** (ADR D7), not narrowly `plans/engineering-notes/`. Allowlist: `adr/**` (era-dated ADRs — 132 dated files pass) + the audit's STAY subtrees `plans/research/**` and `plans/investigations/**`. | the file + its canonical home |
| `shadow_tree_basename` | the same **non-nav content** basename exists under two distinct section subtrees | "doc root" = the section subtrees. Exempt: nav basenames (`index.md`, `README.md`, `toc.yml`) and sanctioned era files (`README-N.x.md`, `00-SYNTHESIS.md`). This is a content-duplicate check, not an absolute basename-uniqueness count (NFR-005). | both paths |
| `frontmatter_contract` | an **in-scope** page lacks a required frontmatter field | "in-scope" **excludes** section `README.md` landing pages; the 3 frontmatter-less `docs/adr/{1.x,2.x,3.x}/README.md` are allowlisted (deferred to #2227). | the file + missing field(s) |

## Configuration source of truth (FR-011)

The section list + the "curated-complete" set, the dated-filename patterns, the **allowlist** (`adr/**`, `plans/research/**`, `plans/investigations/**`), the required frontmatter fields, and the in-scope exclusions are **read from the extended `common-docs` styleguide's machine-parseable config block** (FR-006/FR-011) — the lint LOADS this config and does not hard-code policy divergent from the doctrine (C-005). A `tests/docs/` test asserts the lint's runtime behaviour matches that styleguide config (single source of truth — one policy store, not two).

## Regression fixture (ATDD — Charter Check)

A `tests/docs/test_docs_structural_lint.py` fixture reintroduces one instance of **each** of the 4 rule classes and asserts each is caught (100% detection, SC-003). A **current-clean-tree assertion** proves zero false positives on the real tree, including explicit assertions that `adr/**` (era-dated) and `plans/{research,investigations}/**` pass clean, that the 38 `index.md`/38 `README.md`/nav basenames do not trip the shadow-tree check, and that the 3 frontmatter-less ADR READMEs do not trip the frontmatter check.

## Non-goals

- Does not move files or rewrite links (that is the mission's content work + `relative_link_fixer` + `bulk_ref_rewrite`).
- Does not resurrect the retired ratchet's `CANONICAL_SECTIONS`/`section_missing_index` behaviour verbatim — index *completeness* (curated-complete sections) replaces index *existence*, and no check enforces an absolute count.

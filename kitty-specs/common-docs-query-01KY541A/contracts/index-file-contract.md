# Artifact Contract: docs retrieval index + freshness gate

## The generated index file

- **Path**: `docs/development/3-2-docs-retrieval-index.yaml` (new, git-tracked).
- **Packaged model** — `src/specify_cli/docs/index_model.py` (shipped in the wheel; the CLI imports
  ONLY this, `src→src`):
  - `Anchor`, `DocsQueryEntry` (frozen dataclasses)
  - `render_index(entries) -> str` (deterministic, byte-stable string)
  - `parse_index(text) -> list[DocsQueryEntry]`
  - `compare_index(committed, regenerated) -> IndexDrift` (mirrors `InventoryDrift`)
  - `DocsIndexStore.load(path)` + `.query(...)`
  - `DEFAULT_INDEX_PATH`
- **Generator (build-tooling)** — `scripts/docs/docs_index.py` (NOT shipped; imports the model DOWN
  from `src`, `scripts→src`):
  - `generate_index(docs_root) -> list[DocsQueryEntry]` (uses `parse_frontmatter`, `DivioType`, sorted
    `rglob`, `slugify`+ordinal)
  - `scan_headings`, `resolve_title`, `resolve_abstract`, `slug_for_headings` helpers
  - `run_generate_and_compare(..., write: bool, strict: bool)` — `__main__` entrypoint; `--write`
    refreshes the file, `--strict` exits non-zero on drift.
- **Import-direction invariant**: `scripts → src` is legal; **`src → scripts` is forbidden** (the wheel
  excludes `scripts`, so an installed-CLI import of `scripts.*` would `ModuleNotFoundError`). A test MUST
  assert the CLI-facing symbols (`DocsQueryEntry`, `Anchor`, `DocsIndexStore`) import from
  `specify_cli.docs.index_model`.
- **Determinism (NFR-001)**: entries sorted by `path`; anchors in document order; slugs pure. Two
  regenerations over an unchanged tree produce byte-identical output.
- **Header**: a `# GENERATED — do not edit by hand.` leading comment (inventory-lockfile convention).

## C-001 invariants (page-inventory untouched)

The following MUST be byte-for-byte unchanged by this mission:

- `docs/development/3-2-page-inventory.yaml`
- `scripts/docs/_inventory.py::PageInventoryEntry` (schema, `_REQUIRED_KEYS`)
- `scripts/docs/inventory_lockfile.py::render_lockfile`
- `scripts/docs/check_docs_freshness.py::_check_inventory_lockfile_drift`
- `tests/docs/test_inventory_path_stable.py`, `tests/docs/test_bulk_ref_rewrite.py::test_inventory_lockfile_untouched`

A regression test SHOULD assert the docs-index generator does not import/mutate `PageInventoryEntry`.

## Freshness gate

- **New checker**: `scripts/docs/check_docs_freshness.py::_check_docs_index_drift` — regenerates the
  index in-memory, compares to the committed file, emits an `error`-severity finding on drift.
- **Registration**: folded into the aggregate ruler list alongside (not replacing)
  `_check_inventory_lockfile_drift`. Rule id e.g. `DOCS-INDEX-DRIFT`.
- **CI**: `.github/workflows/docs-freshness.yml` — verify the aggregate call covers the new checker; add
  an explicit step only if the aggregate does not.
- **Behavioral contract**:

| Given | When | Then |
|-------|------|------|
| committed index matches the tree | `check_docs_freshness --ci` | new checker passes (exit 0 contribution) |
| a page's heading/description changed but index not regenerated | `check_docs_freshness --ci` | `DOCS-INDEX-DRIFT` error, aggregate exits non-zero |
| index regenerated + committed | `check_docs_freshness --ci` | green again |

## Reuse (C-004)

Import from existing `scripts/docs/` surfaces — do not fork:
`parse_frontmatter`, the sorted `rglob("*.md")` walk, `DivioType`, the `InventoryDrift`/`compare`
diff shape, and `slugify` (+ ordinal-dedup pattern) from `generate_kitty_specs_docs.py`.

# Research: Common Docs query — CLI retrieval index

Consolidated from the pre-plan adversarial squad (architect-alphonso + python-pedro, convergent,
code-cited). Every decision below is grounded in an existing repo surface; no NEEDS CLARIFICATION
remain.

## Decision 1 — Sibling artifact, NOT enrichment of the page-inventory

- **Decision**: The retrieval index is a new, separate generated file
  (`docs/development/3-2-docs-retrieval-index.yaml`) built by a new module
  (`scripts/docs/docs_index.py`) with its own `DocsQueryEntry` schema.
- **Rationale**: `PageInventoryEntry` (`scripts/docs/_inventory.py:93`) is a `frozen` 6-field
  dataclass with a `_REQUIRED_KEYS` frozenset, imported by 8 tooling modules + 6 test files, rendered
  byte-stably by `render_lockfile` (`inventory_lockfile.py:227`) and guarded by a now-*blocking*
  `_check_inventory_lockfile_drift` (`check_docs_freshness.py:681`). Widening it changes every
  committed inventory row → instant drift red, and forces edits to `test_inventory_path_stable.py`
  and `test_inventory_lockfile_untouched` — the exact C-001 consumers. The sibling holds C-001 *by
  construction*.
- **Alternatives considered**: Enrich `PageInventoryEntry` in place (rejected — breaks C-001, reds the
  blocking gate). A brand-new framework unrelated to the inventory (rejected — violates C-004; the
  inventory generator is the proven deterministic pattern to mirror).

## Decision 2 — Reuse the inventory generator machinery (C-004)

- **Decision**: Import and reuse `parse_frontmatter` (`scripts/docs/_inventory.py:38`, the canonical
  ruamel-safe docs-page frontmatter extractor), the sorted `rglob("*.md")` walk, the `DivioType`
  StrEnum (`_inventory.py:83`, sourced from the frontmatter `type:` key per `inventory_lockfile.py:68`),
  and the `InventoryDrift` / `compare_inventories` diff shape.
- **Rationale**: These are the canonical, already-tested docs-page primitives. `parse_frontmatter` is
  the right surface (NOT `src/specify_cli/frontmatter.py`, which is the WP-file manager).
- **Alternatives considered**: A second frontmatter parser (rejected — DIRECTIVE_044).

## Decision 3 — Parallel freshness gate, inventory ruler untouched

- **Decision**: Add `_check_docs_index_drift` to `check_docs_freshness.py` and register it in the
  aggregate as a new `error`-severity ruler; leave `_check_inventory_lockfile_drift` byte-for-byte
  unchanged.
- **Rationale**: Mirrors the proven drift pattern; C-001 keeps the inventory gate untouched.
- **Open verification (Phase 2)**: confirm whether `.github/workflows/docs-freshness.yml` invokes the
  aggregate (auto-covering the new gate) or needs an explicit step.

## Decision 4 — Mirror the glossary CLI shape

- **Decision**: New `src/specify_cli/cli/commands/docs.py` Typer sub-app with a `query` command,
  registered via `app.add_typer(docs_module.app, name="docs", ...)` next to `glossary`
  (`cli/commands/__init__.py:208`). JSON path uses `print(json.dumps(output, indent=2))` (not Rich
  `console`); empty result prints `"[]"` and returns (exit 0); human path uses a Rich `Table`.
- **Rationale**: `glossary.py:292-363` is the exact proven shape; empty→`[]`/exit-0 satisfies
  Acceptance Scenario 2.
- **Alternatives considered**: Rich `console.print_json` (rejected — markup/formatting risk for machine
  consumers). A new top-level command instead of a sub-app (rejected — inconsistent with glossary).

## Decision 5 — Anchor authority: canonical `slugify` + ordinal dedup, NOT DocFX-exact

- **Decision**: Compute heading anchors with the canonical `slugify`
  (`generate_kitty_specs_docs.py:193`, already import-shared by `glossary_linker.py`) plus ordinal
  disambiguation (the `assign_anchor_ids` pattern) for duplicate headings. Anchors are deterministic
  source-heading slugs; byte-identical fidelity to the rendered DocFX site is an explicit non-goal
  (C-005).
- **Rationale**: The `docs/` tree is a DocFX site (`toc.yml`/`docfx.json`, `seo_postprocess.py`), not
  rendered by the Python `slugify`. Reverse-engineering DocFX's JS slugger is disproportionate; the
  index's job is to point an agent at the correct source heading deterministically, which the canonical
  `slugify` does. Reusing it (not forking) satisfies DIRECTIVE_044 and keeps NFR-001 byte-stability.
- **Alternatives considered**: Replicate DocFX exactly (rejected — scope/maintenance cost, C-005). Write
  a fresh slugger (rejected — canonical-sources violation).

## Decision 6 — Title precedence and abstract fallback

- **Decision**: `title` = frontmatter `title` else first `# H1` else path stem. `abstract` =
  frontmatter `description` else first non-heading paragraph else empty. Both are total (never crash).
- **Rationale**: NFR-001 needs a deterministic, total precedence. ADR/changelog pages with no
  `description` (the `_EXCLUDE_PREFIXES` set in `description_length_check.py`) are included with an
  empty abstract — consistent with that gate's exemptions.
- **New code**: the first-non-heading-paragraph extractor and the `##`/`###` heading scan are new pure
  helpers (no existing extractor); trivially unit-testable.

## Performance (NFR-002)

- **Decision**: Load the generated index file once at command entry into an in-memory structure; filter
  term/divio-type/section over that structure. No per-query filesystem walk of doc bodies.
- **Rationale**: Mirrors the glossary in-memory-cache filter (`glossary.py:160`); a pre-generated index
  makes full-tree query trivially < 1s.

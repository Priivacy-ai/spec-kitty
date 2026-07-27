---
work_package_id: WP01
title: Docs retrieval index generator
dependencies: []
requirement_refs:
- FR-001
- NFR-001
planning_base_branch: feat/agent-knowledge-canonical-homes
merge_target_branch: feat/agent-knowledge-canonical-homes
branch_strategy: Planning artifacts for this mission were generated on feat/agent-knowledge-canonical-homes. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-knowledge-canonical-homes unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-common-docs-query-01KY541A
base_commit: 72359aa50457c48bdd77b8b8cc85e356088a0d72
created_at: '2026-07-22T15:11:05.810465+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history:
- at: '2026-07-22T14:56:33Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: scripts/docs/
create_intent:
- src/specify_cli/docs/__init__.py
- src/specify_cli/docs/index_model.py
- scripts/docs/docs_index.py
- docs/development/3-2-docs-retrieval-index.yaml
- tests/docs/test_docs_index.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/docs/**
- scripts/docs/docs_index.py
- docs/development/3-2-docs-retrieval-index.yaml
- tests/docs/test_docs_index.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its directives and tactics (spec fidelity, locality, canonical-sources reuse, close-defect-by-construction, anti-scaffold testing) for the whole WP. State which you applied in your handoff note.

## Objective

Build the deterministic, byte-stable **sibling** docs retrieval index across a **packaged model** and a
**build-tooling generator**, and generate the committed index file
(`docs/development/3-2-docs-retrieval-index.yaml`). Foundation both WP02 (freshness gate) and WP03
(query CLI) consume.

**Canonical decisions (locked by the pre-plan + post-tasks squads — do NOT re-litigate):**
- **PACKAGING SPLIT (load-bearing).** `scripts/` is NOT in the shipped wheel, so the installed CLI
  cannot import `scripts.*`. Put the CLI-facing schema + store in a **packaged** module and import it
  *down* from the generator:
  - `src/specify_cli/docs/index_model.py` (+ `__init__.py`) — `Anchor`, `DocsQueryEntry`,
    `render_index`, `parse_index`, `compare_index`/`IndexDrift`, `DocsIndexStore`, `DEFAULT_INDEX_PATH`.
    **No `scripts` import.**
  - `scripts/docs/docs_index.py` — the generator: `generate_index`, `scan_headings`, `resolve_title`,
    `resolve_abstract`, `slug_for_headings`, `run_generate_and_compare`, `__main__`. Imports the schema
    + `render_index`/`compare_index` **from `specify_cli.docs.index_model`** (`scripts→src`, legal).
  - **`src→scripts` is forbidden** (would `ModuleNotFoundError` in the installed CLI).
- **SIBLING topology.** Do NOT widen or import-mutate `scripts/docs/_inventory.py::PageInventoryEntry`
  (it is `frozen`, C-001-pinned, consumed by 8 tooling + 6 test modules). Define your own `DocsQueryEntry`.
- **Reuse (C-004), don't fork:** import `parse_frontmatter` (`scripts/docs/_inventory.py:38`), the sorted
  `rglob("*.md")` walk pattern, `DivioType` (`scripts/docs/_inventory.py`), the `InventoryDrift`/compare
  diff shape (`scripts/docs/inventory_lockfile.py`), and `slugify` (+ the ordinal-dedup pattern from
  `assign_anchor_ids`) from `scripts/docs/generate_kitty_specs_docs.py`. (`generate_index`/helpers, which
  need `parse_frontmatter`+`slugify` from `scripts`, therefore live in `scripts/docs/docs_index.py` — NOT
  in the packaged model, which stays `scripts`-free.)
- **Anchors are source-heading slugs (C-005)**, NOT DocFX-exact fragments. Deterministic via canonical
  `slugify` + ordinal suffix for duplicates.

Read `plan.md`, `research.md`, `data-model.md` (Module-layering table), and
`contracts/index-file-contract.md` before coding — they carry the exact schema, split, and API.

**Test fixtures:** build a small fixture docs tree **locally in `tests/docs/test_docs_index.py`**
(module-level helper, not `conftest.py`) — WP02/WP03 build their own; do not introduce a shared
`tests/docs/conftest.py` fixture (avoids cross-WP ownership coupling).

## Branch Strategy

Planning base + merge target: **`feat/agent-knowledge-canonical-homes`** (coord topology). The execution
worktree is allocated per computed lane from `lanes.json` by `spec-kitty implement WP01`. Do not create
worktrees by hand.

## Subtasks

### T001 — Red-first byte-stability test (NFR-001) — NON-FAKEABLE

**Purpose**: Prove determinism before the generator exists. ⚠️ A same-process "run twice → equal" check
is FAKEABLE (it passes even if the impl never sorts by path — `rglob` order is stable within a process).
Pin the two NFR-001 clauses ("alphabetical by path" + "deterministic anchor slugs") explicitly:

- In `tests/docs/test_docs_index.py`, build a `tmp_path` fixture tree whose files are **created in
  non-alphabetical order** (e.g. write `zeta.md` before `alpha.md`), with ≥1 page carrying duplicate
  headings and ≥1 with no `description`.
- Assert the rendered entries appear in **ascending `path` order** (a direct sort assertion — not just
  "twice-equal").
- Assert byte-stability across **independent generation**: either (a) snapshot against a committed golden
  string, or (b) regenerate in a subprocess with a **different `PYTHONHASHSEED`** and assert byte-equal
  (guards against hash-seed-dependent set/dict ordering).
- This test MUST fail (import error / missing symbol) before T002–T004 land — the red-first signal.

### T002 — `DocsQueryEntry` + `Anchor` + slug helper

**Purpose**: The data model + the anchor slugger.

- Define `Anchor` (`slug: str`, `text: str`, `level: int`) and `DocsQueryEntry`
  (`path: str`, `title: str`, `divio_type: str`, `anchors: list[Anchor]`, `abstract: str`) as `frozen`
  dataclasses in the **packaged** `src/specify_cli/docs/index_model.py`. Match `data-model.md` exactly.
- `slug_for_headings(texts: list[str]) -> list[str]` (in `scripts/docs/docs_index.py`, since it needs
  `slugify` from `scripts`): apply the canonical `slugify` to each heading
  text, then disambiguate duplicates with an ordinal suffix (`-2`, `-3`, …) following the
  `assign_anchor_ids` pattern. Import `slugify` — do NOT re-implement it (DIRECTIVE_044).
- Unit-test slug + ordinal dedup directly (empty, unicode/punctuation, 3× duplicate → `x`,`x-2`,`x-3`).

### T003 — Pure helpers: heading scan, title precedence, abstract fallback [P]

**Purpose**: Total, deterministic extraction — never crash on missing frontmatter.

- `scan_headings(body: str) -> list[tuple[int, str]]`: walk `##`/`###` lines (level 2/3), return
  `(level, text)` in document order. Ignore fenced code blocks (```) so `## ` inside code is not a
  heading.
- `resolve_title(frontmatter: dict, body: str, path: Path) -> str`: frontmatter `title` → first `# H1`
  → path stem. Never empty.
- `resolve_abstract(frontmatter: dict, body: str) -> str`: frontmatter `description` → first
  non-heading, non-blank paragraph → `""`.
- Unit-test each precedence branch, incl. the ADR/changelog "no description → empty abstract" case.

### T004 — Generator API mirroring `inventory_lockfile.py`

**Purpose**: The generate/render/compare/CLI surface, correctly layered.

In the **packaged** `src/specify_cli/docs/index_model.py` (no `scripts` import):
- `render_index(entries) -> str`: deterministic byte-stable YAML with a `# GENERATED — do not edit by
  hand.` header (mirror `render_lockfile`); entries sorted by `path`; anchors as `{slug, text, level}`.
- `parse_index(text) -> list[DocsQueryEntry]`: inverse of `render_index`.
- `compare_index(committed: str, regenerated: str) -> IndexDrift` (mirror `InventoryDrift`).
- `DEFAULT_INDEX_PATH` = `docs/development/3-2-docs-retrieval-index.yaml`.

In the **generator** `scripts/docs/docs_index.py` (imports the above from `specify_cli.docs.index_model`):
- `generate_index(docs_root: Path) -> list[DocsQueryEntry]`: sorted `rglob("*.md")`, `parse_frontmatter`,
  build entries (using T002/T003 helpers + `DivioType` coercion from the `type:` key), sort by `path`.
- `run_generate_and_compare(docs_root, index_path, *, write: bool, strict: bool)` + a
  `if __name__ == "__main__"` argparse entry with `--write` and `--strict` (exit non-zero on drift under
  `--strict`). Keep each function ≤15 complexity — extract phases.

### T005 — Generate + commit the index file

- Run `python scripts/docs/docs_index.py --write` to produce
  `docs/development/3-2-docs-retrieval-index.yaml` over the live `docs/` tree, and commit it.
- Sanity-check the file is sorted, has the header, and round-trips (`--strict` exits 0 immediately after).

### T006 — Unit tests + C-001 + layering regressions

- Consolidate the helper tests.
- **Positive `slugify`-import assertion** (enforces C-005/DIRECTIVE_044 "no fork"): assert
  `scripts/docs/docs_index.py` imports `slugify` from `scripts.docs.generate_kitty_specs_docs` (module
  inspection) — a re-implemented slugger reds this even if its outputs happen to match.
- **C-001 negative assertion**: assert neither `docs_index.py` nor `index_model.py` imports
  `PageInventoryEntry` (symbol absent from imports). Do NOT claim a unit test "proves" the inventory YAML
  is byte-untouched — instead reference the existing guards
  (`tests/docs/test_inventory_path_stable.py`, `tests/docs/test_bulk_ref_rewrite.py::test_inventory_lockfile_untouched`).
- **Layering assertion (Paula)**: assert the CLI-facing symbols (`DocsQueryEntry`, `Anchor`,
  `DocsIndexStore`) are importable from `specify_cli.docs.index_model`, and that `index_model` does NOT
  import `scripts` (so the installed CLI's dependency is loadable).
- Run `PWHEADLESS=1 uv run pytest tests/docs/test_docs_index.py -q` — all green.

## Definition of Done

- [ ] Packaged `src/specify_cli/docs/index_model.py` (+ `__init__.py`) exposes `Anchor`,
      `DocsQueryEntry`, `render_index`, `parse_index`, `compare_index`/`IndexDrift`, `DocsIndexStore`,
      `DEFAULT_INDEX_PATH`, and imports NO `scripts` symbol.
- [ ] `scripts/docs/docs_index.py` implements `generate_index` + helpers + `run_generate_and_compare` +
      `__main__`, importing schema/render/compare DOWN from `specify_cli.docs.index_model`.
- [ ] **Public API pinned + proven**: a test imports `DocsQueryEntry`/`Anchor`/`DocsIndexStore` from
      `specify_cli.docs.index_model` (the WP02/WP03 seam) and asserts `index_model` has no `scripts` import.
- [ ] `docs/development/3-2-docs-retrieval-index.yaml` generated, committed, byte-stable (`--strict` exit 0);
      entries are path-sorted (asserted directly, not just twice-equal).
- [ ] No import of `PageInventoryEntry` in either new module (C-001, asserted); the inventory YAML's
      byte-identity is left to the existing `test_inventory_path_stable.py` / `test_inventory_lockfile_untouched`.
- [ ] Anchors use canonical `slugify` (positive import assertion) + ordinal dedup (C-005); slug is NOT a fork.
- [ ] `uv run ruff check src/specify_cli/docs/ scripts/docs/docs_index.py tests/docs/test_docs_index.py` → 0 issues;
      `uv run mypy src/specify_cli/docs/ scripts/docs/docs_index.py` clean; every function ≤15 complexity.
- [ ] All new tests green (run with `uv run`, foreground).

## Reviewer guidance

Verify: no import/mutation of `PageInventoryEntry`; `slugify` imported not re-implemented; render is
deterministic (regenerate twice → identical); title/abstract precedence total; the committed index
round-trips under `--strict`. Confirm the generator does not touch the page-inventory file or its gate.

## Risks

- Fenced-code `## ` false headings → scan must skip code fences.
- Non-total title/abstract precedence → crash on frontmatter-less pages. Floor with path stem / `""`.
- Accidentally importing `PageInventoryEntry` for convenience → C-001 breach. Keep the schemas separate.

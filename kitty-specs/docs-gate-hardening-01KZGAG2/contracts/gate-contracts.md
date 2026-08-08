# Phase 1 Contracts: Gate Behavior

No HTTP/API surface — the "contracts" here are each gate's input → exit/message behavior. Each gate is non-vacuous (a committed negative test drives the failure path).

## GATE-1 — `scripts/docs/check_slash_command_freshness.py` (FR-001)

- **Input**: reads `CONSUMER_SKILLS` (imported) and the `## /spec-kitty.<name>` headings of `docs/api/slash-commands.md`.
- **Success (exit 0)**: `documented == CONSUMER_SKILLS`.
- **Failure (exit non-zero)**: prints the symmetric difference — `MISSING` (in registry, not documented) and `EXTRA` (documented, not in registry) — one line per offending command.
- **Negative test**: add a fake command to the registry (or drop/insert a heading) → non-zero naming it; backfilled tree → exit 0.
- **CI**: invoked as a step in `.github/workflows/docs-freshness.yml`.

## GATE-2 — per-include-glob non-vacuity in `scripts/docs/_published_pages.py` (FR-003)

- **Input**: `docs/docfx.json` content entries → include globs; the docs tree.
- **Success**: every declared include glob matches ≥1 markdown file pre-exclusion **and** aggregate ≥ 500.
- **Failure**: a declared include glob resolves to zero pages pre-exclusion → **raises `ValueError`** naming the glob and its content entry, even if aggregate ≥ 500. (Exception type pinned so GATE-2b propagates by-contract.)
- **Non-false-fail**: excluded-by-design trees (`archive/**`) whose raw glob matches ≥1 file pass — the check runs **before** `_apply_exclusions` (iterating `(entry, pattern)` on md-filtered `entry.includes`, not the deduped `source_globs`, so entry attribution survives).
- **Implementation note**: additive helper after the collect loop / before exclusions; do not alter `_collect_entry_pages`' union semantics or the `PublishedPageSet` return type. Shared `_vacuity_error()` builder must reproduce `violates I-01` / `violates I-02` / `expected at least` substrings verbatim.
- **Negative test** (`tests/docs/test_published_pages.py`): `_write_config` with two globs — one ≥500, one empty → raises `ValueError`; an equivalent per-entry check would pass.

## GATE-2b — propagation via `description_length_check.py` (FR-004)

- **Contract**: the empty-glob fixture, driven through `description_length_check.py`'s resolver entry point, surfaces as a `CoverageError` (exit 2) — because `_resolve_page_set` catches `(FileNotFoundError, ValueError)` and re-wraps. This proves the shared-resolver consumer inherits GATE-2's failure path (not just the happy path), and is why GATE-2 must raise `ValueError`, not a bespoke type.

## GATE-3 — docs-freshness safety-structure test (FR-005)

- **Input**: `.github/workflows/docs-freshness.yml` (repo-readable; may parse with `ruamel.yaml`, already a project dep, rather than regex).
- **Success**: all three properties hold — (a) the `paths:` **allowlist** is present AND does **not** contain `tests/**` or `kitty-specs/**` (absence-from-allowlist — there is no explicit `!` exclusion pattern to match); (b) unfiltered `push: main` backstop present (a `push:` trigger with `branches:[main]` and no `paths:` key); (c) documented safety-invariant comment present.
- **Failure**: any property missing → test fails naming it.
- **Explicit non-goal**: does NOT read live GitHub branch protection; does NOT assert `required == {drift-detector}`.

## Notes (documentation-only, verification-free)

- FR-006: `docs-freshness.yml` invariant comment cross-references GATE-3 (reuses the "Required-check contract" idiom).
- FR-007: `docs-pages.yml` comment records that `seo_verify` runs push-only (`main`/`2.x`), no `pull_request` trigger — the deploy-side analogue of the item-3 gap.

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
- **Failure (raise)**: a declared include glob resolves to zero pages pre-exclusion → raises loud naming the glob and its content entry, even if aggregate ≥ 500.
- **Non-false-fail**: excluded-by-design trees (`archive/**`) whose raw glob matches ≥1 file pass (evaluated pre-exclusion).
- **Negative test** (`tests/docs/test_published_pages.py`): `_write_config` with two globs — one ≥500, one empty → raises; an equivalent per-entry check would pass.

## GATE-2b — propagation via `description_length_check.py` (FR-004)

- **Contract**: the empty-glob fixture, driven through `description_length_check.py`'s resolver entry point, also raises loud — proving the shared-resolver consumer inherits GATE-2's failure path (not just the happy path).

## GATE-3 — docs-freshness safety-structure test (FR-005)

- **Input**: `.github/workflows/docs-freshness.yml` (parsed as text/YAML, repo-readable).
- **Success**: all three properties hold — (a) `paths:` filter present and excludes `tests/**` + `kitty-specs/**`; (b) unfiltered `push: main` backstop present; (c) documented safety-invariant comment present.
- **Failure**: any property missing → test fails naming it.
- **Explicit non-goal**: does NOT read live GitHub branch protection; does NOT assert `required == {drift-detector}`.

## Notes (documentation-only, verification-free)

- FR-006: `docs-freshness.yml` invariant comment cross-references GATE-3 (reuses the "Required-check contract" idiom).
- FR-007: `docs-pages.yml` comment records that `seo_verify` runs push-only (`main`/`2.x`), no `pull_request` trigger — the deploy-side analogue of the item-3 gap.

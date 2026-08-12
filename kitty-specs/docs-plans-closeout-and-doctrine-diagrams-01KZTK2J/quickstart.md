# Quickstart: docs/plans Tier 3 closeout (Scope A)

## Add the `durable` doc_status value

1. Edit the AUTHORITY first: `packs/built-in/directives/042-common-docs.directive.yaml` (add `durable` to the vocabulary).
2. Mirror in `scripts/docs/frontmatter_backfill.py:DocStatus` (`DURABLE = "durable"`).
3. Update the styleguide `structural_lint_config` / freshness-SLA gate so `durable` is accepted and `durable ∉ point_in_time`.
4. Run `PWHEADLESS=1 python -m pytest tests/docs/ tests/doctrine/test_schema_generation_integrity.py -q` — the `durable`-accepted-everywhere test must go green.

## Retire a plan cluster

1. Confirm shipped/distilled evidence (`gh issue view <n>` or an open-core-plan citation).
2. Flip `doc_status` to `deprecated` (RECORD-tier) or move the cluster to an archive dir; never delete. `closeout` is NOT a doc_status value.
3. Update `docs/plans/index.md`; keep `3-2-x-milestone-roadmap.md` untouched (deferred, C-001).

## Migrate a domain plan into domains/

- Follow `occurrence_map.yaml`: move the file into `docs/plans/domains/`, update every reference (index, release docs, §6 cross-refs), regenerate the docs lockfiles (`docs_index.py --write` + `inventory_lockfile.py`), and confirm zero dead links via the relative-link-fixer test.

## Gates before commit

`PWHEADLESS=1 python -m pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q` and the doc-freshness check must be green.

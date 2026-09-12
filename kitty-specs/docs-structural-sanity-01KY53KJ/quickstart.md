# Quickstart — Docs Structural Sanity & Concern Guard

How to execute and verify this mission's work. All commands run from the repository-root checkout. **All link-repointing tooling (`relative_link_fixer` + `bulk_ref_rewrite`) is driven against THIS mission's `occurrence_map.yaml` via `--occurrence-map`** — its built-in default is pinned to a foreign mission (`common-docs-structural-move-01KW3SBK`); never rely on that default (FR-010/C-007). **This mission does NOT regenerate `redirect_map.yaml`** — the moved/removed paths are never-published (absent from `redirect_baseline_urls.json`), so `redirect_stub_generator regenerate-map` would derive zero entries and overwrite the map, wiping the landed `01KW3SBK` 149 redirects (PB2). Leave the redirect corpus untouched; link integrity comes from `relative_link_fixer` (in-repo docs) + `bulk_ref_rewrite` (non-docs).

```bash
MAP=kitty-specs/docs-structural-sanity-01KY53KJ/occurrence_map.yaml
```

## Recipe A — relocate a point-in-time file (target does NOT yet exist)

```bash
git mv docs/architecture/audits/2026-05-spec-kitty-caacs.md \
       docs/plans/engineering-notes/architecture-audits/2026-05-spec-kitty-caacs.md
# NOTE: this mission does NOT regenerate redirect_map.yaml. The moved paths are never-published
# (absent from redirect_baseline_urls.json); `regenerate-map` would derive ZERO entries and OVERWRITE
# the map, wiping the landed 01KW3SBK 149 published-URL redirects (PB2). Leave redirect_map.yaml untouched.
# 1. repoint in-repo relative links (docs/** ONLY — writes by default; NO --write flag; --occurrence-map mandatory, C-007)
python -m scripts.docs.relative_link_fixer --occurrence-map "$MAP"
# 2. rewrite NON-docs/ prefix referrers (src/, scripts/) the relative fixer never walks
python -m scripts.docs.bulk_ref_rewrite --occurrence-map "$MAP"
# 3. regenerate the page-inventory lockfile in place (path pinned — C-004; WRITER, not the read-only checker)
python scripts/docs/inventory_lockfile.py --write docs/development/3-2-page-inventory.yaml
# 4. update related: frontmatter edges on the moved file + referrers
```

## Recipe B — fold-then-delete a shadow (canonical twin ALREADY EXISTS)

The 3 `plans/notes/` shadows have canonical twins that STAY — do **NOT** `git mv` (it clobbers the canonical).

```bash
# 1. reconcile: port any UNIQUE content from the shadow INTO the existing canonical twin
diff docs/plans/notes/feature-detection.md docs/architecture/feature-detection.md
#    (merge divergent content into docs/architecture/feature-detection.md by hand)
# 2. delete the shadow
git rm docs/plans/notes/feature-detection.md
# NOTE: no redirect stub — the shadow URL was never published; this mission regenerates NO redirect_map (PB2).
# 3. repoint referrers to the canonical path (--occurrence-map mandatory, C-007)
python -m scripts.docs.relative_link_fixer --occurrence-map "$MAP"
python -m scripts.docs.bulk_ref_rewrite --occurrence-map "$MAP"
# 4. correct docs/plans/notes/README.md; regenerate inventory via `inventory_lockfile.py --write`
```

The authoritative relocation list is `occurrence_map.yaml` (`moves:` block); the 3 folds are carried in its clearly-marked fold-then-delete note, not as `moves:` relocations.

## Run the new guard

```bash
python -m scripts.docs.docs_structural_lint            # exit 0 = clean
python -m scripts.docs.docs_structural_lint --json     # machine-readable violations
```

## Verify the aggregate (mission Definition of Done)

```bash
python -m scripts.docs.relative_link_fixer --check --occurrence-map "$MAP"   # NFR-001: 0 broken relative links
git status --porcelain scripts/docs/redirect_map.yaml scripts/docs/redirect_baseline_urls.json  # NFR-002: both UNTOUCHED (no redirect regen)
python -m scripts.docs.check_docs_freshness --ci       # NFR-004: inventory fresh, no baseline 404s
pytest tests/docs/ -q                                  # docs_structural_lint regression fixture + config-SSOT assert (SC-003, FR-011)
pytest tests/architectural/test_no_legacy_terminology.py -q   # NFR-004: terminology guard (CI-only gate)
python -m scripts.docs.docs_structural_lint            # SC-003/004/005: clean tree, 0 shadow basenames, full architecture/ index
```

## Success signals

- `architecture/` holds no dated dossier; `architecture/index.md` enumerates every page (SC-005).
- `docs/plans/notes/` no longer shadows any canonical basename (SC-004).
- Every in-repo referrer resolves (`relative_link_fixer --check --occurrence-map "$MAP"` is clean); `redirect_map.yaml` + `redirect_baseline_urls.json` are UNTOUCHED (the 149 `01KW3SBK` redirects preserved) and no baseline URL 404s (SC-002 / NFR-002 reframed).
- DIRECTIVE_042 + the `common-docs` styleguide are extended in place, the lint loads the styleguide config, the 4 dangling-ratchet references are reconciled, and `#2302` is closable (SC-006).
- Reintroducing any of the 4 finding-classes fails `docs_structural_lint` (SC-003).

# Quickstart — running the Common Docs Convergence gates locally

All commands run from the repo root under clone-local isolation:

```bash
export SPEC_KITTY_HOME="$PWD/.spec-kitty-home"
export PATH="$PWD/.venv/bin:$PATH"
export SPEC_KITTY_SYNC_DISABLE=1
```

## The gates this mission must keep green

```bash
# 1. Structural lint (extended for mission invariants — FR-023/NFR-003)
.venv/bin/python packs/built-in/assets/docs_structural_lint.py \
  --styleguide packs/built-in/styleguides/common-docs.styleguide.yaml --json docs

# 2. Cross-reference resolvers (non-vacuous — NFR-002). Run --strict.
.venv/bin/python scripts/docs/related_validator.py --strict docs
.venv/bin/python scripts/docs/audience_resolver.py --strict docs      # NEW (FR-003)

# 3. Link integrity (report/check)
.venv/bin/python scripts/docs/relative_link_fixer.py --check docs

# 4. Redirect coverage / map staleness (NFR-010) — driven by THIS mission's occurrence map
.venv/bin/python scripts/docs/redirect_stub_generator.py coverage \
  --occurrence-map kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml
.venv/bin/python scripts/docs/redirect_stub_generator.py check-map \
  --occurrence-map kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml

# 5. Inventory lockfile freshness (rollups regenerated in place — FR-020)
.venv/bin/python scripts/docs/inventory_lockfile.py --check

# 6. Terminology guard (NFR-004)
.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q

# 7. Stale-path grep gate (NFR-005) + authority-path resolution (FR-019) + audience resolve
.venv/bin/pytest tests/docs/ -q

# 8. Pre-merge site build (NFR-001/FR-017) — the NEW PR job, locally:
docfx docs/docfx.json   # must be zero-error/zero-warning
```

## Behavior-documenting pages
Regenerate from source rather than hand-editing (NFR-009):
```bash
.venv/bin/python scripts/docs/build_cli_reference.py
.venv/bin/python scripts/docs/check_cli_reference_freshness.py
```

Full-suite runs (~1h) are CI's job — do not run them in-session. Use targeted gates above.

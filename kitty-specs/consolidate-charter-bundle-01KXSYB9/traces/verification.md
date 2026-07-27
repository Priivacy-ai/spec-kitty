# Tracer: Verification

Seeded at planning; append evidence during implement; assess at close.

## Seeded (planning) — how each success criterion will be proven
- **SC-001 (freshness reflects mutation)**: red-first through `compute_freshness`; activate→stale→reconcile→fresh e2e; no permanent-stale reachable.
- **SC-002 (no retired-file / prose decision reads)**: grep gate (four filenames only in migration code); no governance decision reads charter.md.
- **SC-003 (migration idempotent/fail-loud)**: legacy fixture → fail-loud before; migrate; re-run → 0 changes.
- **SC-004 (derived-set == hash-set)**: manifest assertion `{charter.yaml}`; #2758/#2759 stopgaps removed.
- **SC-005 (content-identity #2732)**: existing content-identity suite unchanged; unchanged charter.yaml → identical hash.
- **SC-006 (charter.md never clobbered, folds #2772)**: inverted clobber test — curated prose survives `generate --force`.
- **SC-007 (extractor retired)**: `SECTION_MAPPING`/`extract_with_ai` deleted; loaders read charter.yaml.
- **SC-008 (activation relocated, behavior-preserving)**: `activated_*` in charter.yaml not config.yaml; activation-parity + DRG-filter suites green; overlays default.yaml.
- **FR-015 (config pointer)**: resolver locates charter.yaml via the `charter:` pointer; dangling pointer fails loud.

## Gate matrix (must be green at the single PR head — NFR-005/C-006)
`ruff check .` · `mypy --strict` · `tests/architectural/{test_shared_package_boundary,test_no_legacy_terminology}` · `tests/charter` · `tests/specify_cli/charter_runtime` · `tests/specify_cli/charter_freshness` · `tests/doctrine/test_activation_parity_guard.py` · `tests/upgrade` (migration) · `spec-kitty doctor doctrine` · `scripts.docs.check_docs_freshness --ci`

## Appended (implement)
_(implementers append per-WP proof: commands run + exit codes + evidence)_

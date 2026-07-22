# Quickstart / Validation: Consolidate the Compiled Charter Bundle

End-to-end validation the mission is complete. Run from the repo root after all concerns land.

## 1. One charter, tracked, authorable
```bash
ls .kittify/charter/charter.yaml            # exists, git-tracked
git check-ignore .kittify/charter/charter.yaml || echo "tracked (good)"
# the four legacy files are gone:
! ls .kittify/charter/governance.yaml .kittify/charter/directives.yaml .kittify/charter/references.yaml .kittify/charter/metadata.yaml 2>/dev/null
```
Expect: `charter.yaml` present + tracked; the four legacy files absent (SC-002/SC-004).

## 2. config.yaml: no activation, one pointer
```bash
grep -E "^activated_|activated_kinds|mission_type_activations" .kittify/config.yaml && echo "FAIL: activation still in config" || echo "ok: no activation in config"
grep "^charter:" .kittify/config.yaml       # the one-line pointer
```
Expect: no `activated_*` in config; a single `charter:` pointer (INV-2, FR-015).

## 3. Freshness reflects mutation, no permanent-stale (SC-001)
```bash
spec-kitty doctor doctrine --json            # fresh on a clean tree
# activate/deactivate a doctrine element, recompile, re-check → signal flips, no dead-end
```

## 4. charter.md is a curated companion, never clobbered (SC-006, folds #2772)
```bash
# edit a curated line in .kittify/charter/charter.md, then:
spec-kitty charter generate --force
git diff --quiet .kittify/charter/charter.md && echo "ok: curated prose survived"
```
Expect: curated prose preserved.

## 5. No governance decision reads charter.md prose (SC-002)
```bash
# every charter.md read is display-only; the tier-3 language fallback is migrated:
grep -rn "charter.md\|charter_content" src/charter src/specify_cli | grep -iv "display\|render\|companion\|policy_summary\|section" || true
```

## 6. Extractor retired (SC-007)
```bash
! grep -n "SECTION_MAPPING\|extract_with_ai" src/charter/extractor.py 2>/dev/null && echo "ok: scraper deleted"
```

## 7. Activation behavior-preserving (SC-008)
```bash
PWHEADLESS=1 pytest tests/doctrine/test_activation_parity_guard.py -q
PWHEADLESS=1 pytest tests/charter -q
```

## 8. Migration idempotent + fail-loud (SC-003, NFR-003)
```bash
# on a legacy fixture: charter op fails loud with an actionable message before migration;
# run migration; re-run migration → 0 changes.
PWHEADLESS=1 pytest tests/upgrade/test_unified_bundle_migration.py -q
```

## 9. Gates green (the consistent whole — C-006)
```bash
ruff check .
mypy --strict src/charter src/specify_cli/charter_runtime
PWHEADLESS=1 pytest tests/architectural/test_shared_package_boundary.py tests/architectural/test_no_legacy_terminology.py -q
PWHEADLESS=1 pytest tests/charter tests/specify_cli/charter_runtime tests/specify_cli/charter_freshness -q
python -m scripts.docs.check_docs_freshness --ci
```
Expect: all green in the single PR (no half-inverted state — NFR-005).

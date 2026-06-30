# Quickstart: Documentation Quality Hardening Gate

How to run and verify the surfaces this mission touches. All commands from the repo root.

## Run the body-link gate (the one authoritative gate)

```bash
# Current scope (excludes docs/adr/, docs/changelog/):
python scripts/docs/relative_link_fixer.py --check --repo-root .

# Full-tree gate-unmask dry-run (C-007) — what acceptance requires before merge:
EXCLUDE_PREFIXES_OVERRIDE=1 python scripts/docs/relative_link_fixer.py --check --repo-root .   # or the test below
pytest tests/docs/test_relative_link_fixer.py -q          # incl. TestLiveTreeGate (fast, blocking)
```

A failure lists every offender as `file:line -> target` (NFR-003).

## Find the broken links this mission fixes

```bash
# ADR-body dead links (the 27) — temporarily un-exclude docs/adr/ to enumerate:
python scripts/docs/relative_link_fixer.py --check --repo-root .   # after EXCLUDE_PREFIXES is emptied
# Canonical CHANGELOG dead links (the 5):
#   inspect docs/changelog/CHANGELOG.md body links against docs/ tree
```

## CHANGELOG sync (Lane B)

```bash
python scripts/docs/sync_changelog.py --check    # exit 1 if root != generate(canonical)
python scripts/docs/sync_changelog.py --write    # regenerate root from canonical
```

## ADR byte-invariance (Lane C)

```bash
pytest tests/docs/test_adr_content_invariance.py -q
# Expect: census == 119, invariant == 118 after migration.
```

## Terminology guard (Lane D)

```bash
pytest tests/contract/test_terminology_guards.py -q
pytest tests/architectural/test_no_legacy_terminology.py -q   # repo-wide (CI-only shard) — run before push
```

## Full local gate sweep before pushing

```bash
PWHEADLESS=1 pytest tests/docs/ tests/contract/ -q
ruff check . && mypy scripts/docs/
```

## Acceptance checklist (maps to Success Criteria)

- [ ] SC-001: full-tree gate green (no exclusions).
- [ ] SC-002: deliberate-breakage test reports file+line+target.
- [ ] SC-003: CHANGELOG divergence test red→green.
- [ ] SC-004: ADR invariance green at 119/118.
- [ ] SC-005: exactly one body-link resolver remains (3 hidden checkers retired).
- [ ] SC-006: prose triage resolved + terminology policy doc linked.
- [ ] SC-007: pre-merge full-tree dry-run green on the integrated branch.

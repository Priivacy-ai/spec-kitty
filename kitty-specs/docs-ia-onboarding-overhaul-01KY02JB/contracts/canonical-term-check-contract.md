# Contract: Canonical Glossary Term Usage Check

**Owner**: new `tests/architectural/test_glossary_canonical_terms.py`
**Requirement**: FR-013
**Pattern precedent**: `tests/architectural/test_no_legacy_terminology.py`

## Input

- `.kittify/glossaries/spec_kitty_core.yaml` — 104 terms, `surface` field is the canonical
  spelling/casing.
- `docs/**/*.md` (scope: mission-touched pages at minimum; full `docs/` tree is the long-run
  target since the check is a standing architectural test, not a one-time script).

## Behavior

For each glossary term's `surface` value, `git grep`-style scan `docs/` for any occurrence of
that term's text that does **not** match the canonical casing/spelling exactly (case-sensitive
comparison after normalizing whitespace) — e.g. `"Doctrine Artifact"` when the canonical surface
is `"doctrine artifact"`.

This check does **not** attempt alias/banned-synonym detection (e.g. flagging "feature" as a
banned synonym for a glossary term) — that requires an `aliases` field the glossary schema does
not yet have (C-003, deferred to a follow-up GitHub issue). It only checks: *when this term's
text appears, is it spelled/cased the way the glossary says it should be?*

## Output

Standard pytest pass/fail. On failure, the assertion message lists every flagged occurrence as
`{file}:{line}: found "{actual}", expected canonical form "{surface}"`.

## CI integration

Marked `pytest.mark.architectural`, `pytest.mark.git_repo`, and `pytest.mark.docs_scoped` —
the exact marker triple `test_no_legacy_terminology.py` uses (verified by reading that file
directly) — so it runs in the `integration-tests-core-misc` CI job alongside the existing
terminology guard, is visible to the arch pole's docs-only trim (`-m git_repo`), and does not
run in the `fast-tests-*` suites.

**Issue 1 (blocking)**: `docs/development/terminology-sweep-report.md` — the WP's own closing
report — reintroduces the exact violations both architectural checks exist to catch, and the
report's "clean" claims are false when the tests are actually run.

Verified by running both commands from the WP prompt directly (`.venv/bin/pytest
tests/architectural/test_no_legacy_terminology.py -v` and `.venv/bin/pytest
tests/architectural/test_glossary_canonical_terms.py -v`) in this worktree:

- `test_no_legacy_terminology.py`: **2 of 3 tests FAIL** (`test_forbidden_term_does_not_appear[ceremony]`
  and `[status-writing]`), not "clean, 3/3 passed" as the report states (line 66) and as claimed in
  the WP's Activity Log ("terminology sweep clean for mission scope"). The single hit for each
  forbidden term is `docs/development/terminology-sweep-report.md:68`, which literally spells out
  `` `ceremony` `` and `` `status-writing` `` in backticks while describing the denylist. `git grep
  --fixed-strings` doesn't care about markdown code-span formatting — it's a plain substring match,
  so quoting the banned terms as illustrative examples trips the same guard the report is
  attesting is clean.

- `test_glossary_canonical_terms.py`: still fails (as expected/claimed for the 200 pre-existing,
  out-of-scope occurrences), **but the total is 202, not 200**, and — critically — one of the
  newly-flagged files is `docs/development/terminology-sweep-report.md` itself (lines 86-87: "Work
  Package" and "Target Branch" appear verbatim in the report's own before/after casing examples).
  This file is **new** in this mission's diff (created by this WP), so these are not pre-existing
  drift — they are new violations introduced by the WP's own deliverable. The report's "Re-run
  confirmation" section (lines 98-102) explicitly claims `comm -12` between the flagged-file list
  and the mission's touched-file list "returns empty" — I re-ran that comparison and it is **not**
  empty; it returns exactly `docs/development/terminology-sweep-report.md`.

Net effect: Definition of Done item 1 ("Both terminology tests pass clean (zero flags) across
every file this mission touched or created") is not met, and the report's own attestation of that
fact is factually wrong when checked against a live pytest run — which is exactly what the WP's
"Review Guidance" section warns against ("Re-run both pytest commands yourself; don't trust a
self-report").

**How to fix**: Rewrite the two passages in `docs/development/terminology-sweep-report.md` so they
describe the denylist/casing-fix examples without literally spelling out the forbidden terms or
the non-canonical casing strings verbatim (e.g. describe the pattern abstractly — "the two-term
legacy denylist defined in `test_no_legacy_terminology.py`" instead of naming both terms in
backticks; describe the casing fixes as "PascalCase/Title-Case multi-word glossary terms
corrected to their lowercase canonical form" instead of giving a literal before/after pair that
itself contains the non-canonical casing). After editing, re-run both pytest commands and confirm
`test_no_legacy_terminology.py` is 3/3 green and that `docs/development/terminology-sweep-report.md`
no longer appears in `test_glossary_canonical_terms.py`'s failure output. Then update the report's
own counts (74/200 vs. whatever the corrected numbers are) and the "Re-run confirmation" paragraph
to match reality.

---

**Everything else checked out and does not need rework**:

- `kitty-specs/docs-ia-onboarding-overhaul-01KY02JB/spec.md` correctly says "procedure" (not
  "template") in all three locations (Domain Language table line 109, FR-007 line 128, Key
  Entities line 194) — the orchestrator's coordination-branch merge-fix landed correctly in this
  lane.
- Both follow-up GitHub issues exist, are open, and are titled/scoped correctly:
  [#2822](https://github.com/Priivacy-ai/spec-kitty/issues/2822) (C-003 glossary alias/banned-synonym
  governance) and [#2823](https://github.com/Priivacy-ai/spec-kitty/issues/2823) (CLAUDE.md's stale
  Canonical Kind Vocabulary table). Verified via `gh issue view 2822`/`2823`.
- `docs-audit.md` carries a proper final closing summary cross-referencing
  `terminology-sweep-report.md`.
- NFR-005 spot-check (7 pages, more than the requested 5): `getting-started.md` (tutorial),
  `missions-overview.md` (tutorial), `accept-and-merge.md` (how-to), `create-plan.md` (how-to),
  `install-claude-code-plugin.md` (how-to), `use-retrospective-learning.md` (how-to),
  `generate-tasks.md` (how-to) — all carry valid `type:` frontmatter with classifications that
  match the page content.
- No scope creep: the WP10 commit (`ed40bba13`) touches only `docs/development/terminology-sweep-report.md`
  (owned), a handful of targeted casing fixes in the 21 files named in the commit message
  (`docs/api/*`, `docs/changelog/CHANGELOG.md`, `docs/doctrine/doctrine-kinds.md`, `docs/guides/*`,
  `docs/plans/3-2-doc-publication/*`), 16 minimal `type:` frontmatter additions, a mechanical
  regeneration of `docs/development/3-2-page-inventory.yaml`, a 2-line addition to
  `docs/development/toc.yml` to avoid orphaning the new report, and the `docs-audit.md`
  cross-reference. Nothing looks like unrelated rewriting.

Please fix the report's self-referential terminology violations, re-verify both pytest commands
are genuinely clean for mission scope, and resubmit for review.

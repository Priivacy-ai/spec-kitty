---
affected_files:
- path: tests/docs/test_seo_verify.py
cycle_number: 2
mission_slug: docs-seo-metadata-enforcement-01KZ9PJ2
reproduction_command: PWHEADLESS=1 uv run python -m pytest tests/docs/test_seo_verify.py -q
reviewed_at: '2026-08-05T22:35:00Z'
reviewer_agent: claude:opus-5:reviewer-renata:reviewer
verdict: approved
wp_id: WP05
---

# WP05 Review — Render emission and built-output verifier (cycle 2)

**Verdict: APPROVED.**

Cycle 1 rejected on exactly two missing tests. Both are now closed, and the reviewer
re-derived every load-bearing claim rather than accepting the commit message.

## R-1 (blocking in cycle 1) — closed, inversion verified independently

`_replace_head_close` had zero coverage: reverting it to the string-form `re.sub` passed the
entire suite (650 tests, none noticed). The reviewer reverted it again
(`HEAD_CLOSE_RE.sub(replacement, markup, count=1)`) and ran the file. **Both new tests went
red, and only those two** (2 failed, 31 passed):

- `test_postprocess_survives_group_reference_in_description` — `re.error: invalid group
  reference 1`. The loud mode.
- `test_postprocess_does_not_corrupt_windows_path_in_description` — the **silent** mode,
  visible in the failure output as `ache at C:<TAB>emp`. No exception; it failed on a value
  assertion.

The reviewer went further than the brief: with the fix inverted **and** the test's raw-text
guards (`assert "\t" not in rendered`, the `find_description` check) stripped out, the
remaining parsed-value assertion still failed on `_og_description(rendered)`. The corruption is
therefore caught through a successfully-parsed value, not merely a byte scan — the test
genuinely pins the silent mode, which is the one a raise-only test would miss.

After restore, `scripts/docs/seo_postprocess.py` is byte-identical to its committed state
(sha256 `89280311c963…`), `git diff` empty, worktree clean.

## R-2 — closed

`_finding_note`'s `_NOTE_UNEXPECTED` branch is now exercised by a third case in
`test_stale_url_finding_note_states_only_what_was_observed`. The assertion pins the specific
sentence and asserts the value is neither of the other two constants. Flipping the branch to
return `_NOTE_NOT_OBSERVED` turns it red.

## Extra tests — genuine coverage, each the sole catcher of its branch

Every inversion was run against the whole file to rule out duplication:

| Inverted branch | Failures across all 33 tests |
|---|---|
| `og:title` comparison in `_check_open_graph` | 1 — `test_og_title_mismatch_is_red` |
| `page.title is None` branch of `_check_title` | 1 — `test_absent_title_is_red` |
| sitemap-orphan comprehension in `_check_sitemap` | 1 — `test_sitemap_entry_without_a_page_is_red` |

These are real independent branches, and before this commit none had any guard. Not padding.

## Production files unchanged

Diff from the rejected state (`9c75578f9^`) to HEAD touches only
`tests/docs/test_seo_verify.py` (+255) plus mission status bookkeeping.
`scripts/docs/seo_postprocess.py` and `scripts/docs/seo_verify.py` do not appear — the fix was
tests-only as claimed. No smuggled production change.

## Carried forward from cycle 1 (approved as written, not re-litigated)

Workflow step position (after redirect-coverage, before Setup Pages, `--strict`); both
`seo_postprocess.py` defect fixes (idempotence via `\s*</head>`; backslash corruption via the
callable substitution); the fifth `PageClass` member `NOINDEX` (accepted — `data-model.md`
leaves an ordinary page carrying explicit `robots: noindex` unbucketed; **data-model drift
noted for the record: the doc lists four members, the enum ships five**); I-08 (`should_index`
imported, never redefined); conditional emission ordering; read-only guarantee; determinism;
I-07 peer naming; V-07 constant import.

## Gates

- `tests/docs/` — 662 passed; `test_seo_verify.py` — 33 tests.
- `ruff check` clean; `mypy --explicit-package-bases` clean.
- Scope: `description_length_check.py` and `test_docs_seo.py` (WP06) untouched.
- Pre-review `no_coverage — No module named 'pytest'` treated as the known environmental
  anomaly seen on every WP in this mission, not a finding.

## Provenance note

The cycle-1 fix has unusual provenance and it is recorded rather than glossed: the
implementation agent **died on a network error** mid-task having written the tests but not
committed or verified them; the **orchestrator** ran the inversion verification and completed
the handoff. Tests authored by one party, verified by another, neither independently reviewed
at that point. This cycle-2 review is the independent verification — every claim above was
re-derived by the reviewer, and all held, including the headline numbers (33 / 662 / clean).

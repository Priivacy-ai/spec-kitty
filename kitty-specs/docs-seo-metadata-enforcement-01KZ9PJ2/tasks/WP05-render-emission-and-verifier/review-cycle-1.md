---
affected_files: []
cycle_number: 1
mission_slug: docs-seo-metadata-enforcement-01KZ9PJ2
reproduction_command:
reviewed_at: '2026-08-05T20:58:40Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

# WP05 Review — Render emission and built-output verifier

**Verdict: REJECT** — narrow rework only. The implementation is correct; the safety net has a
hole. Two tests are missing, and one of them covers a production helper you introduced
specifically to fix a silent-corruption defect. Reverting that helper to its buggy form passes
**650/650** tests in `tests/docs/`.

Do **not** change anything else. Everything listed under "Verified and accepted" below is
approved as written — re-submitting with unrelated edits will fail review again.

---

## Required changes (2 tests, no production changes)

### R-1 (blocking) — `_replace_head_close` has zero regression coverage

`scripts/docs/seo_postprocess.py:_replace_head_close` routes the substitution through a callable
so `re.sub` treats the block literally. The rationale in the docstring is correct — I reproduced
both failure modes against the pre-change form:

```
description containing "\1"      → re.error: invalid group reference 1   (build crash)
description containing "C:\temp" → JSON-LD emits "C:\temp"; \t is a valid JSON escape,
                                   so json.loads() succeeds and silently yields a TAB
                                   where the author wrote a backslash  (silent corruption)
```

But the guard is untested. I applied this mutation:

```python
# scripts/docs/seo_postprocess.py, in process_html()
-    markup = _replace_head_close(markup, block + "  </head>")
+    markup = HEAD_CLOSE_RE.sub(block + "  </head>", markup, count=1)
```

and ran the **entire** docs suite: `650 passed`. Not one test noticed. That means your
handoff claim "18 mutation proofs, all detected" is not accurate, and a future refactor of
`process_html` can silently reintroduce the corruption.

**Add** a test to `tests/docs/test_seo_verify.py` that runs `process_html` over a page whose
description contains a backslash sequence (cover both `\1` and a lone `C:\...` path) and asserts
the description survives verbatim in the emitted `<meta name="description">` **and** that the
JSON-LD block still round-trips through `json.loads` with the backslash intact. Confirm the test
goes red under the mutation above before you re-submit.

This is not speculative housekeeping: this repo's docs describe regexes and Windows paths, and
descriptions are author-written prose. The mission exists to make silent metadata defects loud;
shipping an untested guard against silent metadata corruption is the same failure one layer down.

### R-2 (blocking) — `_NOTE_UNEXPECTED` branch is untested

`_finding_note()` has three outcomes. `test_stale_url_finding_note_states_only_what_was_observed`
pins `_NOTE_NOT_OBSERVED` and `_NOTE_CONFIRMED`. The third — "Both addresses are present but do
not match the expected stub/live-page shape" — has no test.

I confirmed the branch is reachable and correctly derived (fixture: reported address present as an
ordinary indexable page rather than a stub, current address present → the note fires correctly).
So this is coverage only, not a correctness fix. Extend the existing test with that third fixture.

Charter standing order: every new branch/helper gets a test in the same PR. These two are the
only ones outstanding.

---

## Verified and accepted — do not modify

Checked directly, not taken on trust:

**Workflow position (C-B9/C-B10)** — `.github/workflows/docs-pages.yml`. `Verify built-output SEO
metadata` sits at line 95, after `Verify redirect coverage (NFR-002)` (line 82) and before
`Setup Pages` (98) / `Upload artifact` (101). Runs `--strict`. No existing step reordered or
modified; the diff is purely additive (14 lines). Adding `scripts/docs/seo_verify.py` to
`on.push.paths` is correct and in scope — the workflow now invokes that script, so a change to it
must retrigger the build; WP08 owns `docs-freshness.yml`, not this file.

**I-08, no second definition** — `grep -c "def should_index" scripts/docs/seo_verify.py` → 0.
`classify()` calls `should_index()` first and returns `INDEXABLE` on a positive verdict; the
`assets/` / `toc.html` / refresh-marker branches run only after a negative verdict and only
select an explanatory label. They cannot override the authority. Correct.

**Conditional emission (C-B1)** — `SEO_BLOCK_RE.sub("", markup)` runs at
`seo_postprocess.py:331`, before `find_description(markup) is None` is evaluated at 348. Ordering
is right: a previously-injected backstop is stripped before the "does the author have one?"
question is asked, so the backstop cannot self-perpetuate.

**Read-only (C-B6)** — every read in `seo_verify.py` is `read_text`. The only writes are
`sys.stdout.write` and the `--json` report, and `_resolve_report_path` refuses a report path
inside `--site-dir`. `test_verifier_does_not_mutate_site` compares raw bytes of the whole tree
(deliberately not a normalizing hasher) — a real test, not a token one.

**Mutations I inverted personally** (restored after each; working tree confirmed clean):
- `_check_description` → return `[]` on missing tag ⇒ `test_missing_description_is_red` +
  `test_strict_exits_nonzero` fail. Detected.
- `classify` → always `INDEXABLE` ⇒ 10 tests fail. Detected.
- `main` → always `return 0` ⇒ `test_strict_exits_nonzero` fails. Detected.
- `HEAD_CLOSE_RE` → back to `r"</head>"` ⇒ `test_postprocess_is_idempotent` fails. Detected —
  your idempotence claim is real and covered.
- `_replace_head_close` → string-form `re.sub` ⇒ **650 passed. NOT detected.** See R-1.

**Claim 1 (`--explicit-package-bases`)** — reproduced on untouched
`scripts/docs/description_length_check.py`: mypy fails module-mapping resolution via
`scripts/docs/_inventory.py` without the flag. Pre-existing config drift, not yours. With the
flag, `seo_verify.py` + `seo_postprocess.py` → `Success: no issues found in 2 source files`.

**Claim 3 (evidence-based stale-URL note)** — all three branches reachable, each derived from
actual classifications. Correct fix; FR-011 is satisfied on evidence rather than assertion.

**Claim 4 (fifth `PageClass` member `NOINDEX`)** — accepted. The data-model table defines
`INDEXABLE` as "none of the above, **and no existing noindex robots directive**", which leaves an
ordinary page carrying explicit `robots: noindex` with no bucket at all, while `should_index()`
correctly rejects it. Folding it into `TOC_PAGE` or `ASSET` would mislabel a real
misconfiguration. Documented in the enum docstring, changes no rule's applicability (rules still
apply to `INDEXABLE` only). Verified against a live fixture: counts reported
`{'NOINDEX': 1, 'INDEXABLE': 3, ...}`. **Data-model drift noted for the record** — `data-model.md`
lists four members; the shipped enum has five.

**Claim 5 (21 tests vs 15 contracted)** — genuine. All 14 contract-table tests present; the extras
cover NFR-001 titles, stub-missing-noindex, sitemap set mismatch, the read-only `--json` guard,
the I-07 peer naming, and the stale-URL observation branches. No padding.

**Other criteria** — determinism (I-06) confirmed independently at CLI level: two `--json` runs
over a fixture site are byte-identical (`cmp` clean). Duplicate violations name both peers
(`test_duplicate_violation_names_peer`). V-07 imports `FALLBACK_DESCRIPTION` from
`seo_postprocess` rather than retyping it. `ruff check` clean including `C901`. Scope clean:
`git diff --name-only c936b6f8c^ c936b6f8c` shows exactly the four expected files —
`description_length_check.py` and `test_docs_seo.py` (WP06's) untouched.

**Not counted against you** — the `--strict` failure on ADR pages lacking descriptions inside this
worktree (WP02/03/04 carry the 148 descriptions on sibling lane branches absent from this base),
and the pre-review `no_coverage — No module named 'pytest'` gate artifact (the CLI runs outside
the uv venv).

**Test count note** — you reported 660; this worktree collects 650 in `tests/docs/`, of which 21
are `test_seo_verify.py`. The delta from your base is exactly +21, all green, so attribution is
clean; the 660 figure was measured against a different base.

---
affected_files: []
cycle_number: 1
mission_slug: retire-doctrine-term-01M0JMK9
reproduction_command:
reviewed_at: '2026-08-22T22:20:14Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 review feedback (reviewer-renata) — CHANGES REQUESTED

Verdict: REJECT on one blocking, WP-attributable test failure. Every other acceptance criterion passes
(planning-only diff, frozen baseline, ADR contract completeness §1–§8 + anti-goals, eight self-sufficiency
questions answerable from the ADR alone, generator-written registration, terminology canon, prior-ADR
pointer-only change). Do not rework the ADR body; only the frontmatter `description` needs a fix.

## Issue 1 (BLOCKING) — ADR frontmatter `description` exceeds the docs description-length gate

**What:** `docs/adr/3.x/2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md`, line 3,
`description:` is 232 characters. The published-page gate requires 50–180 characters
(`scripts/docs/description_length_check.py: MAX_DESCRIPTION_LENGTH = 180`).

**Evidence (run on branch at e420f4dcc/HEAD 139ee3418):**
```
PWHEADLESS=1 .venv/bin/pytest tests/architectural/test_no_legacy_terminology.py tests/docs -q -p no:cacheprovider -n auto --dist loadfile
FAILED tests/docs/test_docs_seo.py::test_published_pages_have_title_and_description[docs/adr/3.x/2026-08-22-2-retire-doctrine-term-charter-is-the-canonical-vocabulary.md]
  -> description length is off: 232 (band 50-180)
FAILED tests/docs/test_description_length_gate.py::test_live_tree_is_clean
  -> TOO_LONG docs/adr/3.x/2026-08-22-2-...md (length=232)
2 failed, 1645 passed, 9 skipped
```
The other 777 published pages are clean, so this is new red introduced by WP01 (not baseline red;
the gate predates the WP on origin/main: eb9919d67). WP "Done" requires checks recorded green; CI's
docs gate will also fail on this.

**Why it matters:** C-002 / DIRECTIVE_030 (test and typecheck quality gate) — the WP must land green on
the docs gates it touches; the frontmatter is consumed by the published docs site (SEO description).

**Exact fix:**
1. Shorten the `description:` value to 50–180 chars without changing the decision semantics, e.g.
   `description: 'Retire the doctrine token in favour of charter across the repository outside the immutable kitty-specs/ archive; M1 makes it effective, M6 proves an exact zero audit.'` (≈170 chars — re-count before committing; keep backticks out if they push it over).
2. Re-run, all must be green / exit 0:
   - `PWHEADLESS=1 .venv/bin/pytest tests/docs/test_docs_seo.py tests/docs/test_description_length_gate.py tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider`
   - `.venv/bin/python -m scripts.docs.freshen_adr_inventory --check` (description is not part of the
     index/inventory rows, so no regeneration is expected; the check must still report clean)
   - `git diff --check`
3. Commit on the planning branch (planning-only diff; no WP frontmatter edits) and move WP01 back to
   `for_review` with the note recording the three green commands.

## Non-blocking observations (no action required)
- Scope/owner table differs from `contracts/adr-content-contract.md` §4 only cosmetically ("including
  `retire-doctrine-term-01M0JMK9`" vs "including this one"; "delete; replace" vs "delete, replace";
  "in the checked-out tree"). Semantically identical — acceptable.
- "Pros and Cons of the Options" uses compressed prose instead of the template's `**Pros:**`/`**Cons:**`
  bullet lists. All template sections are present; acceptable for a 1–2 page ADR.
- Tracer files are mission-shared (appended by every WP); WP01's appends are additive only — fine.

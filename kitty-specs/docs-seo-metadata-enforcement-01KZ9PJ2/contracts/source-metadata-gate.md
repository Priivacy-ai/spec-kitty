# Contract: Source-Level Metadata Gate

**Modules**: `scripts/docs/description_length_check.py` (modified), `tests/docs/test_docs_seo.py` (modified)
**Concern**: IC-02
**Requirements**: FR-002, FR-003, FR-006, FR-007, NFR-002–NFR-006

Blocks at PR time, runs without .NET. Catches authoring defects before merge; cannot observe the render (that is `built-output-verifier.md`).

---

## Changes to `description_length_check.py`

### C-S1 — Consume the resolver

Replace the `docs_root.rglob("*.md")` walk with `resolve_published_pages(...)`. The gate stops guessing which pages are published and asks the authority.

Consequence: pages under `docs/plans/`, `docs/templates/`, and other unpublished trees leave the gate's scope. This is correct — publication status is `docfx.json`'s decision. It may **reduce** the checked count; that reduction is legitimate and must not be confused with the under-collection I-02 guards against.

### C-S2 — Retire the ADR exclusion

```python
_EXCLUDE_PREFIXES: Final[tuple[str, ...]] = ("docs/adr/",)
```

Removed. The accompanying comment is **corrected, not deleted** (DIRECTIVE_037): it currently cites byte-invariance "enforced by `test_adr_content_invariance`", which that module's own docstring records as retired on 2026-06-29 (`ccd278061`). Replace with a note stating the rationale expired and descriptions were backfilled by this mission, so the next reader learns the history rather than finding an unexplained deletion.

**Hard ordering constraint**: this change must not land before IC-04 completes. Removing the exclusion against un-backfilled ADRs turns CI red for 147 files.

### C-S3 — Boilerplate detection (net-new, FR-006)

```python
BOILERPLATE_DESCRIPTIONS: Final[frozenset[str]] = frozenset({
    "Spec Kitty documentation for CLI workflows, governed missions, "
    "AI harnesses, and 3.2 upgrades.",
})
```

A description matching a known fallback is reported as `boilerplate`, a distinct reason from `missing`. Distinct reasons matter: "you wrote nothing" and "you inherited the default" call for different author actions.

Single canonical authority: this set must be imported from, or asserted equal to, `seo_postprocess.DEFAULT_DESCRIPTION` — not retyped. A test pins the two together so changing the fallback string cannot silently disarm the check.

### C-S4 — Uniqueness (net-new, FR-007)

After collecting all descriptions, group by exact value; any group of size > 1 yields one violation per member, each naming its peers (I-07).

Comparison is exact-match on the raw string. Normalisation (case, whitespace) is deliberately **not** applied — two descriptions differing only in case are still duplicates for search purposes, and exact matching keeps the rule explainable.

### C-S5 — Coverage assertion (net-new, FR-003, I-01/I-02)

Before validating, assert the resolved page set is non-empty and above floor. A gate that validates zero pages must **fail**, not pass.

This single assertion is what makes the class of bug under repair unrepresentable.

### C-S6 — Preserve the existing exit contract

`--strict` exits non-zero on violations; report-only exits 0. Matches `related_validator.py`. `docs-freshness.yml` already invokes with `--strict`; that invocation is unchanged.

### C-S7 — Preserve the band

`MIN_DESCRIPTION_LENGTH = 50`, `MAX_DESCRIPTION_LENGTH = 180`, inclusive (C-003). Untouched.

---

## Changes to `tests/docs/test_docs_seo.py`

### C-S8 — Delete the hardcoded globs

`_published_markdown_files()`'s ten-pattern list is removed and replaced by a call to the resolver. This is the direct fix for the 2.4%-coverage defect.

### C-S9 — Keep parametrisation

The per-file parametrised shape is retained so a failure names the offending page. Scaling from 16 to ~674 parametrised cases must stay inside the 30-second budget (NFR-007); if it does not, collapse to a single test emitting all violations at once rather than relaxing the budget.

---

## Test contract (NFR-006 — the gate must be provably able to fail)

Extends the existing boundary-proof precedent in `test_description_length_gate.py`, whose docstring already states the principle: *"A length gate that cannot go RED is fake, so the Definition of Done is the boundary proof."*

| Test | Asserts |
|---|---|
| `test_missing_description_is_red` | Absent description → violation, reason `missing` |
| `test_49_and_181_are_red` | Existing boundary proof preserved |
| `test_50_and_180_are_green` | Existing boundary proof preserved |
| `test_boilerplate_description_is_red` | Exact fallback string → reason `boilerplate` (C-S3) |
| `test_boilerplate_set_matches_seo_postprocess` | Constant pinned to the render-side fallback (C-S3) |
| `test_duplicate_descriptions_are_red` | Two pages, same description → both flagged |
| `test_duplicate_violation_names_the_peer` | Violation carries the colliding path (I-07) |
| `test_empty_page_set_is_red` | Zero resolved pages → failure, not pass (C-S5) |
| `test_adr_pages_are_now_in_scope` | An ADR without a description is flagged (C-S2) |
| `test_strict_exits_nonzero` / `test_report_only_exits_zero` | Exit contract preserved (C-S6) |
| `test_live_tree_is_clean` | Post-backfill, the real tree yields zero violations |

`test_live_tree_is_clean` is the acceptance test for IC-04 and will be red until the backfill completes. That is intended and is the red-first signal.

# Quickstart / Verification Runbook: Retire the Doctrine Term

**Mission**: retire-doctrine-term-01M0JMK9 · **Phase 1 output** of `/spec-kitty.plan`
Run these checks in order before merge. All commands run from the repository root checkout on `feat/retire-doctrine-term`.

## 1. Guard stays green (this mission touches no scanned surface)

```bash
pytest tests/architectural/test_no_legacy_terminology.py -q
```

Expected: PASS. This mission adds no user-facing "doctrine" to `src/`, `tests/`, or scanned `docs/` — the new ADR lives under `docs/adr/3.x/`, which is guard-exempt as a historical-snapshot path.

## 2. ADR registered (C-002)

```bash
python -m scripts.docs.freshen_adr_inventory --check docs/adr/3.x/<new-adr-file>.md
```

Expected: clean (era index row + `docs/development/3-2-page-inventory.yaml` lockfile both current). Also verify the old ADR's diff is **status frontmatter only**:

```bash
git diff docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md
```

Expected: `status:` line + pointer only; body byte-for-byte untouched (C-003 carve-out).

## 3. ADR self-sufficiency pass (SC-001)

A reviewer with **no other context** reads only the new ADR and states, from it alone:
1. what is being retired and what replaces it;
2. the three-way distinction (charter bundle / active charter / inactive charter);
3. which kind vocabulary survives;
4. the scope boundary (in: user-facing language; out: internal identifiers, legacy-marked artifacts) **including the operator-typed identifier classification**;
5. the compatibility policy (3.x hidden aliases + warnings; 4.0 zero user-visible "doctrine").

Named reviewers: post-implement squad lens (advisory) + operator at PR review. All five stated correctly = PASS.

## 4. Mechanical audit — inventory completeness (SC-002, NFR-001)

Re-run the audit at the current base and check the inventory's arithmetic:

```bash
git ls-files | xargs git grep -ic 'doctrine' 2>/dev/null | awk -F: '{s+=$NF} END {print s}'
```

Compare against `inventory.md` frontmatter `total_hits`, then verify the completeness statement:
`total_hits = sum(OC rows) + sum(classification-out rows)` with **0 unclassified hits**.

## 5. Stacked-plan completeness (SC-003)

Check the assignment table in `stacked-plan.md`:
- every in-scope OC-## from `inventory.md` appears **exactly once** (assigned to one mission, or deferred with rationale);
- no OC-## is assigned to two missions;
- M1's `open_items` list is **empty** (FR-010).

## 6. First-mission spec-readiness dry run (SC-004, FR-010)

From `stacked-plan.md` + the ADR + `inventory.md` (S2/S5 rows) + `methodology.md` **alone**, attempt to write M1's (`charter-authority-flip`) full spec. PASS = the draft needs **0 new operator decisions** — every vocabulary term, canon line, glossary entry, bundle edit, and guard-baseline parameter is already fixed in this mission's artifacts.

## 7. Methodology invariant check (FR-008)

Verify `methodology.md` states, for each stack level I0–I6: the invariant that must hold, and — for every surface class outside the guard's scan roots (S4/S5/S6/S8/S9) — exactly one named verification mechanism (C-004). Also verify the guard design carries: concrete floor + shrink-only ratchet + self-mutation test (Standing Order #5) and the stated blind spot (count growth inside baseline files; caught by per-wave re-baselining).

## Merge gate summary

| # | Check | Pass condition |
|---|-------|----------------|
| 1 | Guard green | `test_no_legacy_terminology.py` PASS |
| 2 | ADR registered + old-ADR diff minimal | freshen `--check` clean; frontmatter-only diff |
| 3 | SC-001 self-sufficiency | all 5 items stated from ADR alone |
| 4 | SC-002 audit completeness | arithmetic holds; 0 unclassified |
| 5 | SC-003 assignment completeness | every OC-## exactly once; M1 open_items empty |
| 6 | SC-004 first-mission spec-readiness | M1 spec draftable with 0 new decisions |
| 7 | FR-008 invariants + C-004 mechanisms | I0–I6 stated; one named mechanism per out-of-root class |

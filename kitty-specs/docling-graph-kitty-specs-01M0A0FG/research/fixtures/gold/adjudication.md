# Gold Adjudication

**Adjudicator**: `/root`  
**Date**: 2026-08-18  
**Final gold SHA-256**: `9488045c28987f971af87d6f77c59531f81d29868666fd15d100ec10dd2ac2d8`

## Disagreements and Resolutions

1. A011 originally cited `create_intent`, not `owned_files`. Both reviewers rejected it. It was repinned to baseline line 38 and reapproved.
2. Q3 omitted two declared owned files. A020/A021 were added; both reviewers verified the complete six-file set.
3. Q6 atoms were initially critical despite the noncritical query. They were changed to noncritical and reapproved.
4. Reviewer B rejected a mypy-only proof for FR-015. A003 was replaced with the exact eight-test SC-7 3→1 behavioral proof and reapproved.
5. Broad Q1/Q3/Q4/Q5 wording and open predicate aliases could create unfair false positives. Questions were narrowed; forbidden relation families, normalization, inverse handling, and evaluation precedence were frozen.

No reviewer interpretation was overruled. Every correction either selected a reviewer-requested source span, added reviewer-identified missing truth, or narrowed the question. No favorable candidate result existed or was inspected.

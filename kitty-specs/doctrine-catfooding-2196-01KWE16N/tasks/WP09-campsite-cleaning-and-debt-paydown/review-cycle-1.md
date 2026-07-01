---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T10:41:11Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP09
---

# WP09 Review — Changes Requested (review cycle 1)

**Reviewer:** reviewer-renata (claude:opus)
**Verdict:** NOT MET — one blocking deliverable is missing. The YAML extension itself is correct and all functional gates are green; the block is purely the missing mandatory overlap-audit record.

---

## What is GREEN (do not re-do)

- **Diff scope — PASS.** WP09's own commit (`5d51da604`) modifies ONLY
  `src/doctrine/directives/built-in/025-boy-scout-rule.directive.yaml` (27 insertions).
  024, 040, `planning-and-tracking.styleguide.yaml`, the ratchet tactic, the
  brownfield paradigm, and `graph.yaml` are all UNCHANGED. No duplicate campsite
  directive was created. (The dependency-merge commits for WP01/WP02 in the lane
  diff are expected and are not WP09's changes.)
- **No-duplication (substance) — PASS.** Independently verified: the new
  "domain-matched-fold-at-point-cut" atom is genuinely distinct from the existing
  025 rule. Existing 025 = reactive, implementation-time cleanup of failures
  surfaced *within already-touched files* ("Applies to the files and modules
  already modified for the current task … does not license … edits outside the
  touched area"). New atom = proactive, PLANNING-point-cut (post-spec/plan/tasks)
  folding gated on DOMAIN MATCH, which can deliberately pull in items *outside*
  the touched surface when the domain matches. Different temporal phase +
  different trigger. Not a paraphrase.
- **References — PASS.** Four inline edges present via `references:`
  (DIRECTIVE_024, DIRECTIVE_040, `frozen-baseline-shrink-only-ratchet` tactic,
  `brownfield-onboarding` paradigm). Referenced, not re-authored. `graph.yaml`
  correctly left for WP12.
- **Gates — PASS.** `spec-kitty doctor doctrine --json` → healthy, 0 invalid,
  0 skipped. `tests/doctrine/drg/test_shipped_graph_valid.py` → 2 passed
  (extended 025 schema validates). `tests/architectural/test_no_legacy_terminology.py`
  → 3 passed. `tests/doctrine/test_directive_consistency.py` → all passed (no
  root-vs-step dup refs in 025).

---

## BLOCKING — Issue 1: Overlap-audit record is missing

The Conversion DoD makes the recorded overlap-audit a mandatory deliverable:

- `contracts/conversion-dod.md` **reviewer checklist item #1**: "Overlap-audit
  record present + honest (no duplicate authority)."
- T038 / **SHOULD-TIGHTEN 6**: "quote the SPECIFIC lines from
  `025-boy-scout-rule.directive.yaml` … Record these lines verbatim in the
  Activity Log. Then explicitly state why the new 'domain-matched-fold-at-point-cut'
  atom is DISTINCT … This quote + distinction must appear in the Activity Log
  before T039 begins; a reviewer will mechanically confirm no duplication by
  comparing the verbatim 025 text against the new extension."

The Activity Log for WP09 contains only the bald claim
`"Overlap audit recorded"` — there is **no verbatim 025 quote, no distinction
statement, and no augment-vs-create record** in the Activity Log or anywhere
in the mission directory (searched the coord `kitty-specs/` tree and the WP09
task subdirectory — empty). The reviewer is required to confirm the *record is
present*; it is not.

This is not a nitpick for a doctrine-catfooding mission whose whole purpose is
process fidelity: the recorded audit is the durable no-duplication proof future
curators rely on, and SHOULD-TIGHTEN 6 exists specifically so the check is
mechanical rather than reconstructed by the reviewer.

**How to fix (trivial — no YAML change needed):** append to the WP09 Activity
Log the T038 overlap-audit output:
1. Verbatim quote of the pre-existing DIRECTIVE_025 lines that describe what it
   already covered (intent lines re: touched-area failing-test/lint/type fixes;
   scope line "does not license … edits outside the touched area";
   the original procedures/integrity/validation bullets).
2. An explicit statement of why the new domain-matched-fold-at-point-cut atom is
   distinct (planning point-cut vs implementation-time; domain-match trigger vs
   already-touched-file trigger; may pull in out-of-touched-surface items).
3. The augment-vs-create verdict per 024, 040, and
   `planning-and-tracking.styleguide.yaml` (extend/cross-link/RELOCATED-to-WP11),
   per conversion-dod pre-condition #2.

Once the audit is recorded in the Activity Log, this WP is approvable — the
implementation itself needs no changes.

---

## Non-blocking cross-lane note (for WP02, not WP09)

`tests/doctrine/test_tactic_compliance.py::test_root_references_not_repeated_in_steps`
FAILS for `architectural-gate-non-vacuity.tactic.yaml` (step 2 re-declares the
root-level `frozen-baseline-shrink-only-ratchet` reference). That file is owned
by **WP02** (introduced in commit `50687f9f5`), inherited into lane-i only via
the dependency merge. It is NOT WP09's file and does NOT block WP09. Flagging so
WP02's review (or WP12 wiring) addresses the root-vs-step dup before mission merge.

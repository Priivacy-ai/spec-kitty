---
affected_files: []
cycle_number: 1
mission_slug: doctrine-catfooding-2196-01KWE16N
reproduction_command:
reviewed_at: '2026-07-01T10:33:17Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
---

# WP05 Review — Changes Requested (1 issue, narrow scope)

Reviewer: reviewer-renata. Almost everything is excellent — this is a
single, cheap-to-fix factual-accuracy defect in the companion guide.
Everything else passes; see "What passed" below so you know the scope.

## Issue 1 (BLOCKING) — `TERMINOLOGY_GUARD.md` misstates how the guard treats code-block / quoted terms

In `src/doctrine/toolguides/built-in/TERMINOLOGY_GUARD.md`, the "How to Fix"
section says:

> Superseded terms may appear **quoted-and-marked** (inside code blocks, or
> explicitly labeled as `"forbidden term: …"`) without tripping the guard,
> because the guard matches exact strings and a code-block context does not
> remove the match. Therefore: if you need to name a superseded term as an
> example, place it in a code block or quote it explicitly and verify the guard
> still passes.

This is self-contradictory and operationally **wrong**. The guard
(`tests/architectural/test_no_legacy_terminology.py`) runs
`git grep --fixed-strings <term>` over `src/`, `tests/`, `docs/` and then
filters out only excluded *paths*. It has **no markdown/code-block awareness**:
a superseded term written inside a code block or in quotes in a *scanned* file
WILL be matched and WILL trip the guard. The clause "a code-block context does
not remove the match" correctly states this — but it directly contradicts the
surrounding claim that quoting lets a term appear "without tripping the guard,"
and the follow-on instruction ("place it in a code block ... and verify the
guard still passes") would fail for any real forbidden term.

Why this matters for this mission specifically: this is a doctrine-catfooding
mission whose deliverable is *accurate* doctrine that future agents/operators
consume. As written, an operator could put a superseded term in a code block in
a `docs/` page believing it is exempt, then hit a confusing CI failure — exactly
the papercut this doctrine is meant to prevent.

### How to fix (reword the "How to Fix" section)

State the guard's actual mechanism accurately. A superseded term legitimately
survives the guard **only** by one of:
1. living in an **excluded path** — `kitty-specs/` (historical snapshots) or
   `docs/adr/` (immutable decision records); or
2. **not writing the literal term** — e.g. the guard test itself constructs its
   forbidden-term list from string fragments so the test file does not match
   itself.

Code blocks and inline quoting do **not** exempt a term in a scanned file. The
primary and correct remedy is already stated and should remain the headline:
reword the prose to the canonical term; do not add a suppression or exemption.
Drop (or correct) the "place it in a code block ... without tripping the guard"
advice — it is the one inaccurate statement in the file.

(Note: your artifacts themselves correctly avoid this trap by never writing a
literal forbidden term, which is why the guard is green. The defect is only in
the *guidance prose*, not in a live guard hit.)

## What passed (do not re-touch)

- All 4 owned artifacts present: `044-canonical-sources-and-unification.directive.yaml`,
  `canonical-source-unification.tactic.yaml`, `terminology-guard.toolguide.yaml`,
  `TERMINOLOGY_GUARD.md`.
- `guide_path:` resolves to the companion `.md` which exists;
  `test_toolguide_guide_path_exists[...terminology-guard.toolguide.yaml]` PASSES.
- C-004 satisfied: the guard artifacts do **not** trip their own guard —
  `pytest tests/architectural/test_no_legacy_terminology.py -q` → 3 passed.
  (The ironic self-trip is avoided.)
- `spec-kitty doctor doctrine --json` → profile_health healthy, 18/18 valid, 0 errors.
- `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → 2 passed.
- Inline DRG edges present and extract correctly: `DIRECTIVE_044 → tactic`,
  `DIRECTIVE_044 → toolguide`, `tactic ↔ directive`, `toolguide → directive`
  (verified via `extract_artifact_edges`). Uses the established `references:`
  convention (all 11 existing built-in directives use it) rather than the
  prompt's `urn:` sketch — correct call, canonical-source discipline.
- `graph.yaml` UNCHANGED (PD-2); directive number 044 only (PD-1); agent-profile
  wiring deferred to WP12.
- Directive states all three rules clearly (use-canonical-sources /
  unification-not-parity with the explicit "parity preserves the split-brain"
  contrast + load-bearing-invariant exception / missing-command-is-a-gap).
  Tactic is concrete step-by-step. `enforcement: required`.
- Anti-pattern checklist: no dead code (artifacts produce DRG nodes/edges),
  no synthetic-fixture concerns, no silent returns, FR-011 covered by gates,
  no frozen-surface modification, no MUST-NOT violation, owned files disjoint,
  no production-fragility raise. All PASS/N-A.

Fix Issue 1 (single paragraph reword), re-run the terminology guard to confirm
still green, and this is an approve.

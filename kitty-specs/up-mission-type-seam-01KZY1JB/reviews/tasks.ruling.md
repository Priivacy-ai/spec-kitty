# Operator ruling — TASKS-phase preflight, `up-mission-type-seam`

**Date**: 2026-08-13
**Context**: Not a post-review HALT. This ruling covers a **preflight tooling-landmine finding**,
surfaced before WP authoring or `finalize-tasks` were invoked, per the mission brief's pre-armed
landmine #1 (upstream #3394): `finalize-tasks` regex-scans the *entire raw text* of `spec.md`
for `FR-\d+` / `NFR-\d+` / `C-\d+` tokens, with no table-scoping and no allowlist for a marked
citation. Any bare `FR-\d+` token found anywhere — including inside a quoted sentence about
another mission's requirement — is folded into this spec's own declared requirement set and,
if unmapped by any WP, causes `finalize-tasks` to hard-fail (`typer.Exit(1)`,
"Requirement mapping validation failed").

## What was found

The mandated preflight grep —

```
grep -oE '\b(FR|NFR|C)-[0-9]+\b' kitty-specs/up-mission-type-seam-01KZY1JB/spec.md | sort -u
```

— returned this spec's own `FR-001..FR-013` plus one extra: `FR-032`, occurring exactly once, at
`spec.md:77`, inside CL-002 point 2's verbatim quotation of a **different mission's** ADR
decision driver:

> "...'no silent fallback' contract (R-009/CL-1, FR-032, pinned by
> `tests/doctrine/test_org_pack_augmentation.py`)..."

`FR-032` is not declared anywhere in this spec's own Functional Requirements table (which stops
at FR-013) and belongs to whatever mission originally authored that contract/test. It is cited
here purely for context — to justify why `ArtifactKind` promotion (issue #2468) is a separate,
riskier slice this mission does not touch (spec CL-002). This was confirmed a real, deterministic
hard-fail by reading the actual scan/validation source
(`src/specify_cli/requirement_mapping.py:16`, `mission_finalize.py:342-353,609-663`), not merely
inferred from the grep.

This phase agent STOPPED at this preflight check, before dispatching a WP author or invoking
`finalize-tasks`, per the mission brief's explicit instruction: "If a foreign citation exists,
STOP and report it — do not edit the reviewed spec without an operator ruling." Both remediation
options were presented to the operator rather than one being applied unilaterally.

## Options considered

- **Option A** — mark the citation as an intentionally altered quotation using the standard
  scholarly convention for an elided quotation (square brackets), so the regex no longer matches
  the bare token, while the quoted ADR's meaning, its `R-009/CL-1` anchor, and the pinned test
  path all survive legible and traceable.
- **Option B** — have WP01 (the ADR work package, which already discusses this exact quoted
  driver per CL-002(b)) list `FR-032` among its own claimed requirements, purely to satisfy
  `finalize-tasks`'s mapping check, with no `spec.md` edit at all.

**Option B was rejected** — by this phase agent in its initial report, and independently
confirmed by the operator's ruling — on traceability grounds: it would write a **false**
requirement claim into `acceptance-matrix.json` and the eventual mission retrospective's FR
coverage accounting. That trades the tool's own silent-wrongness (a regex false-positive) for a
worse one (fabricated requirement ownership) — precisely the class of defect this mission's own
`NFR-002` / `CL-006` ("silent success is forbidden") exist to eliminate elsewhere in the
codebase. Choosing Option B without explicit operator sign-off would itself have been an
unauthorized silent-wrongness workaround.

## Ruling

**Option A, executed as a bracketed editorial elision — not a silent reword.** `spec.md:77`
changed from:

```
   'no silent fallback' contract (R-009/CL-1, FR-032, pinned by
```

to:

```
   'no silent fallback' contract (R-009/CL-1, [no-silent-fallback FR], pinned by
```

The brackets signal the alteration honestly, per standard convention for marking an editorial
change inside a direct quotation. The ADR's meaning, the `R-009/CL-1` anchor, and the pinned
test-path citation (`tests/doctrine/test_org_pack_augmentation.py`) all survive unchanged.

**Verification performed after the edit:**

1. `grep -oE '\bFR-[0-9]+\b' spec.md | sort -u` → exactly `FR-001` through `FR-013` — this spec's
   own declared set, nothing foreign.
2. The bracketed replacement string `[no-silent-fallback FR]` does **not** itself match
   `\bFR-[0-9]+\b` (no digits follow `FR`) — confirmed by inspection of the pattern and the
   grep output above showing zero hits beyond FR-001..013.
3. `C-011` at `spec.md:313` ("the charter's ATDD-first discipline (C-011)") was re-confirmed as
   **charter** rule-numbering, not a foreign mission constraint, and — per the source read in
   `src/specify_cli/requirement_mapping.py` — does not feed the `FR-`-only hard-fail set at all.
   Left untouched; not a blocker either before or after this edit.

## Scope of authorization and no-delta-re-review determination

This ruling authorizes **exactly one** edit: the bracketed elision at `spec.md:77`. It does not
reopen any other line of `spec.md`, and it does not authorize Option B under any circumstance.

Per the operator's explicit instruction, **no delta re-review of `spec.md` is required** for this
edit, because it changes no requirement, scope claim, or acceptance criterion — it only marks an
already-quoted external citation as elided. This phase agent independently re-read the full
edited passage (CL-002 points 1–3, `spec.md:68-90`) after applying the edit and confirms: the
ADR-relationship narrative CL-002(b) requires, the `#2468`/`#2467` issue references, and the
"no silent contract reversal" framing are all textually unchanged aside from the bracketed token.
No FR, NFR, C, User Story, Acceptance Scenario, or Success Criterion changed meaning. Had this
phase agent judged otherwise, it would have stopped and reported rather than proceeding — per the
operator's own conditional instruction.

## Disposition

TASKS-phase preflight PASSED as of this ruling. WP authoring, the `finalize-tasks` pipeline,
and the R1–R6 adversarial review of `tasks.md` proceed under the mission's original scope from
this point forward. Corresponding entry appended to `tracer-tooling-friction.md` (this mission's
append-only tracer file — prior SPEC-phase SK-12 entries there are untouched).

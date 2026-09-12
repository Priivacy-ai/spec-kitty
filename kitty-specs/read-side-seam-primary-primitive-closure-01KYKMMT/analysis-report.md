---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
mission_id: 01KYKMMTRS1XHXTK1QZ9QGX704
generated_at: '2026-07-28T18:48:21.601960+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/spec.md
    sha256: 934438704dcc7b066b787f44f459877f4f9172b0cd39f72e50064b1261098ec2
  plan.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/plan.md
    sha256: 606b9f2484fac7d0cdc3b00e9e35d6a845de24b9c334584bbdeb0c03933cbfb4
  tasks.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/read-side-seam-primary-primitive-closure-01KYKMMT/tasks.md
    sha256: 1a2046f946138196e1a4243cbb027c7b5adbb7dd2b472d106f949ec75f398474
  charter:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/.kittify/charter/charter.md
    sha256: cb2dc6cd12aade3d5464997467b7ecdbd3849ea3581207b58c207c3d16fff9b8
verdict: ready
issue_counts:
  high: 0
  low: 1
  medium: 1
  critical: 0
  info: 0
findings:
- id: I1
  severity: medium
  category: inconsistency
  summary: FR-022 and plan.md cite '86 references / 22 src files' for _canonicalize_primary_read_handle; live tree has 89/23 (and 38 call sites). Owned by WP08 T036 under FR-016.
- id: S6
  severity: low
  category: style
  summary: Typo 'non-vaciuty' for 'non-vacuity' in spec.md FR-007 and WP02's Definition of Done.
---

## Specification Analysis Report (revision 5)

**Mission**: `read-side-seam-primary-primitive-closure-01KYKMMT`
**Artifacts**: `spec.md` (24 FR / 11 NFR / 11 C / 21 SC / 8 US) · `plan.md` (10 ICs) ·
`tasks.md` (9 WPs / 44 subtasks) · `research.md` · `data-model.md` · `contracts/` (3) ·
`quickstart.md` · `research/expected-reds.md`

**Why revision 5.** The full routing front (WP01–WP07) is now **approved**. WP07's reviewer
identified a blocking forward risk — WP08's pre-authorized out-of-map list did not cover the four
foundation-site files or WP02's gate test, so deleting the wrapper would ImportError the foundation
sites. `tasks.md` §6 and WP08's body were expanded with the four pre-authorizations and a 6-item
reconciliation section (M1 build-break re-point + seed, non-vacuity drop, index-discriminator
reconcile, RecursionError stale-test fix, `emit.py:71` gate-owner-or-allowlist, T024 test). That
`tasks.md` edit marked the report stale — hence this re-record. Ownership validation still passes.

**Why revision 4.** Revision 3 returned `ready`. One further `tasks.md` amendment has since landed
(`a0109eeaf`): WP03's cycle-1 fix re-pointed `retrospective/writer.py:85` at the extracted leaf,
which makes WP02's ledger row for that site stale — its verdict is now `sanction-infra`
(verify-only), not `migrate-fail-loud`, and the enumerated finding set drops **32 → 31** at merge.
WP02 is already approved and routing WPs may not author in its ledger, so §6 now grants **WP06**
scoped authority for that single row. That edit correctly marked the report stale and blocked all
four routing claims. The two open findings are unchanged and both remain deliberate.

**Process note, now three times observed.** Every one of these re-records was caused by the same
ordering error: editing `spec.md`/`plan.md`/`tasks.md` *after* calling `record-analysis`. Each
individual edit was correct and necessary — the cost is purely mine for not batching them before
recording. The rule is: fold **every** pending planning correction first, record once.

### Planning defects corrected since revision 2 (execution-exposed, both mine)

| # | Defect | Exposed by | Correction |
|---|---|---|---|
| P1 | `owned_files` could not express the **allow-list token coupling**: `resolution_gate_allowlist.yaml` pins the literal *token text* of sanctioned call sites, so re-pointing such a site at the extracted leaf necessarily changes the token. WP03's T016 was impossible without editing WP01's file. | WP03 implementation (`77226250f`) | `tasks.md` §6 and WP07's T034 now name the coupling, scope the leeway to the affected entry's `token:` line, require a per-entry rationale, and cite WP03 as precedent. WP07 hits this identically on the four FR-005 foundation sites. |
| P2 | I instructed WP06 to *"route `retrospective/writer.py` through `resolve_retrospective_home`"* — **self-recursive**: line 85 is *inside* that function (defined line 37). Following it literally produces infinite recursion. | WP03 review cycle 1 | WP06 now records `writer.py:85` as a **foundation site — do not route, verify only**. `read_dir` short-circuits `RETROSPECTIVE` to `resolve_retrospective_home` (`resolution.py:1462`), bypassing `resolve_artifact_surface`, so the site sits *beneath* the seam like the four FR-005 sites. |

**P2 is the more serious of the two**, and worth recording as a lesson rather than a footnote: the
`RETROSPECTIVE` short-circuit was *already known* — paula flagged it during the post-plan squad and
it is written into WP09's documentation requirements as a layer-model omission. Nobody connected it
to **recursion analysis** until WP03's reviewer traced the call graph. A fact can be documented in
the plan and still not reach the WP whose correctness depends on it.

### The cycle WP03 introduced (fixed in cycle 1; recorded here because the *detection* generalises)

```
read_dir(RETROSPECTIVE) → resolve_retrospective_home (writer.py:85)
  → primary_feature_dir_for_mission (the public wrapper)
    → placement_seam(...).read_dir(PRIMARY_METADATA)      ← back into read_dir
```

NFR-009 violated, and **newly introduced** — pre-WP03 the wrapper was a pure leaf. No
`RecursionError` fired because the wrapper hard-codes `PRIMARY_METADATA`, whose leg does not
re-enter: **termination is a property of that constant, not of the call graph.** WP03's designated
stop-everything signal was therefore *silent on a cycle that exists*, as was the orchestrator's own
verification. Proved by the reviewer with `sys.setprofile` across six real-repo fixtures × every
`MissionArtifactKind`: `RETROSPECTIVE` enters the wrapper on all six, every other kind zero.

The transferable lesson: **"no `RecursionError`" is not evidence of "no cycle"** when a call graph is
broken only by a hard-coded constant. NFR-009 needs a structural check, not a runtime symptom.

### Open findings (unchanged from revision 2)

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
| I1 | Inconsistency | MEDIUM | spec.md:308; plan.md:265; WP08:186 | FR-022 cites "86 references / 22 files"; live tree has **89/23**, and a third figure (38 **call sites**) circulates in WP08. | **Left open deliberately** — WP08 T036 owns the correction under FR-016 and must re-derive it from a census rather than from prose. |
| S6 | Style | LOW | spec.md:309; WP02:333 | "non-vaciuty" → "non-vacuity". | Fix on next touch; not worth another gate invalidation. |

### Coverage (unchanged)

| Class | Total | Covered | Notes |
|---|---|---|---|
| Functional (FR) | 24 | **100%** | `map-requirements` reports `unmapped_functional: []` |
| Non-functional (NFR) | 11 | **100%** | every NFR cited by ≥1 WP |
| Constraints (C) | 11 | **100%** | C-008/C-010 enforced in `tasks.md` §1/§5 by design |
| Success criteria (SC) | 21 | 16 cited / 21 satisfied | the 5 uncited are covered in content (see rev 2) |
| Subtasks | 44 | **100%** | T001–T044, no gaps, no duplicates |

### Execution status at this revision

| WP | State | Cycles | Notes |
|---|---|---|---|
| WP01 | ✅ approved | 1 rejection | write-arm branch was dead (name- not kind-discriminated) |
| WP02 | ✅ approved | 1 rejection | index key lacked the site token; four-site test was vacuous |
| WP01–WP07 | ✅ **all approved** | WP01/02/03 one rejection each; WP04–07 clean | routing front complete; every red classified against the true base |
| WP08 | planned, re-scoped | — | the structural finish + a 6-item reconciliation ledger inherited from the routing WPs |
| WP09 | planned | — | docs, after WP08 |

**WP03's approval added two confirmations worth recording.** The reviewer re-ran the cycle trace in
**both** directions (0 wrapper entries with the fix; exactly 6, all `RETROSPECTIVE`, with the fix
reverted at runtime — still no `RecursionError`), and independently enumerated `read_dir` for
**further kind short-circuits**: there is exactly one (`RETROSPECTIVE`), confirmed both statically
(the body is a single `if … return` then an unconditional return) and empirically across 96 traced
calls. So the defect class is closed, not merely the one instance.

Also confirmed: a pre-existing structural guard
(`tests/retrospective/test_home_resolution_single_authority.py`) had pinned the call to the wrapper
**by name** — that assertion was itself enforcing the regression and would have failed the correct
fix. Now inverted and verified to bite.

**Three rejections, three of the same species**: an assertion or a signal that cannot fail for what
it claims to check. WP01's write-arm branch could not match any of its own subjects; WP02's
four-site test asserted distinctness of a key that never held the discriminator; WP03's
no-`RecursionError` signal could not observe a cycle broken by a constant. None would have failed a
green run. All three were found by **mutation or call-graph tracing rather than reading** — which
is the review instruction that produced them, and the strongest evidence so far that this mission's
thesis (structurally verify the verifier) is correct.

### Charter alignment

**No violations.** Eight principles evaluated in `plan.md`; the two doctrine tensions
(FR-007 vs `DIRECTIVE_043`; `/ad-hoc-profile-load` scope) remain explicitly adjudicated rather than
silent. The four recorded doctrine gaps stay correctly scoped file-don't-fix.

## Next Actions

**Verdict: ready.** No CRITICAL or HIGH findings. WP03 may re-claim and proceed to cycle 1.

- **I1** stays with WP08 T036.
- **S6** on next touch.
- **Process note, now twice-observed**: fold analysis findings and planning corrections **before**
  calling `record-analysis`. Editing `spec.md`/`plan.md`/`tasks.md` afterwards marks the report
  `stale_analysis_report` and blocks every WP claim until re-recorded. This has now cost two
  re-records (rev 2 after folding rev 1's findings; rev 3 after the P1/P2 corrections).

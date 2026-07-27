# Independent review — planning artifacts (2026-07-23)

**Status:** external review record, not a binding constraint. Read-only pass requested
by the operator; no artifact was edited and no work package was created as part of it.
Recorded against branch tip `d9b3162eb`, mission base `8074107d7`.

**Scope of the ask:** an independent judgement (not a confirmation) on six questions —
central-claim support, requirement verifiability, internal contradictions, decomposition
and sequencing soundness, what is missing, and whether the scope is right. Load-bearing
measurements and `file:line` references were re-verified against the code rather than
trusted; prior review rounds were treated as claims to test.

## Method

Fetched the branch into an isolated worktree and isolated the mission's real footprint
(the top 27 commits over base `8074107d7`; the remainder of the `merge-base..HEAD` range
is main's intervening work). `spec.md`, `plan.md`, and `data-model.md` were read in full
and a set of load-bearing refs verified directly. Three profile-loaded reviewers ran in
isolated worktrees on independent lenses: (a) central-claim defect reproduction against
`src/`, (b) requirement verifiability and cross-artifact contradiction sweep, (c) the two
landed renames plus the two ADRs. The rename-affected suites were executed on the branch
(`tests/mission_runtime/` + `tests/specify_cli/tool_surface/` → **755 passed**). Every
finding below survived a second look; findings that did not reproduce were dropped.

## Overall verdict

**The work is sound.** The central claim is real and reproduces at every cited site; the
design is coherent and unusually self-critical. The defects found are almost all
**artifact drift** — spec/contract prose lagging corrections the mission itself already
made in `research.md` — rather than design errors. There is a bounded, specific fix-list
(below) to clear before tasking. Nothing found says "this is wrong"; several items say
"the last review round did not fully propagate," which is the state the operator
predicted.

---

## 1. Is the central claim supported by the evidence? — Yes, verified

All four user-story defects reproduce on the branch as published (no fix has landed yet;
only the two enabling renames and their ripple):

- **US1** — acceptance runs `pending` negative-invariant checks from the bare primary
  `repo_root` (`acceptance/gates_core.py:298` → `acceptance/matrix.py:351/354`). A
  mission-added subject that lives only on unconsolidated lanes reads `still_present` →
  `overall_verdict == "fail"` → acceptance blocks. The landed #1834 guard only protects
  *already-recorded non-`pending`* results; a scaffolded-`pending` invariant is still
  judged from the wrong surface.
- **US2** — the dry-run readiness preview feeds a **PRIMARY**-resolved directory to
  `materialize()` for a coordination-topology mission (`merge/forecast.py:174-192` →
  `post_merge/review_artifact_consistency.py:168`), so every work package resolves to
  `None` state and a genuinely rejected review slips through as "ready." This is issue
  **#2885**; the earlier `_resolve_review_cycle_read_dir` fix repaired the *review-cycle
  artifact* read but not the *lane-state* read. The fix must correct the dry-run's
  `materialize` surface specifically.
- **US3 / C-002** — the *reported* cause (#2795, "lock written into the coordination
  worktree") is genuinely stale: the VCS lock writes to the PRIMARY-partition dir
  (`cli/commands/implement.py:1166`, a `SPEC`-kind read). The artifacts handle this
  correctly — they refuse to fix against the stale cause and require live reproduction
  (FR-011) before any WP reaches its terminal step. Disciplined, not hand-waved.
- **Exemption census** — every enumerated exemption symbol exists in `src/` on the branch;
  **zero phantoms**.

**Two reference defects found by direct verification:**

- `data-model.md:52` cites the `Surface → TopologySurface` rename as commit **`da41c6343`**,
  which **does not exist**. The real rename is `35f54df21`. A fabricated ref that survived
  review.
- The load-bearing **count is false**: the spec says "eight" exemption mechanisms, but the
  real population is **at least 11–12** — `research.md` R-014 already admits this
  (8 → 9 → "at least eleven", then pivots to a derivation rule + shrinking registry). The
  design resolution is correct; the spec prose never caught up (see §3).

## 2. Are the requirements verifiable as written? — Mostly; two are silently untestable

Most FR/NFR/SC are pinned by a named contract clause, acceptance scenario, or measurable
threshold, and are genuinely verifiable. The NFR-002/SC-006 enrolment-inventory oracle
and the NFR-006/SC-004 enumerated retirement list are both properly defined. Exceptions:

- **FR-015 (archiving) — unverifiable as written.** It appears in exactly one place, its
  own FR row: no acceptance scenario, no success criterion, no data-model entity
  (`ArchivedMission` does not exist), no contract clause, no checklist item. Every
  normative guard it states ("refused for a non-terminal mission", "refused while any
  invariant is `still_present`", "record names operator/timestamp/reason", "remain
  enumerable") has no oracle anywhere. `research.md` R-013 gives rationale; a decision log
  is not a test.
- **FR-014 (`LEGACY_UNRECORDED` sentinel migration) — unverifiable and type-homeless.** No
  contract discharges it, and it is written as a `verified_surface_kind` value while that
  field is typed `TopologySurface`, whose own anti-phantom rule forbids an unresolvable
  member. NI-1 also requires *both* `verified_ref` and `verified_surface_kind` on any
  non-`pending` result, but FR-014 supplies only a surface value for the legacy rows.
- The **gate contract's stale "three states"** (see §3) means `EMPTY`'s resolver verdict —
  a slice of NFR-001 — would ship untested.
- Weaker but acceptable: **FR-016** (the external CI enforcer has no artifact-pinned
  callable/oracle), **FR-011** (a methodology directive whose verification collapses into
  SC-003), **FR-018** (docs-presence with no named target or freshness assertion).
- The requirements checklist ticks "all functional requirements have clear acceptance
  criteria," which is too generous given FR-014 and FR-015.

## 3. Internal contradictions — several remain

- **MAJOR — Gate contract C3/C4 says "three declared states"; NFR-001, the data-model, and
  the code all say four.** The 2026-07-23 `EMPTY` correction landed everywhere except
  `contracts/gate-execution-context.md`, whose C3 is still titled "Three declared states,
  three declared answers" and omits `EMPTY`. The code enumerates four
  (`missions/_read_path_resolver.py:278-281`: `MATERIALIZED`, `EMPTY`, `UNMATERIALIZED`,
  `DELETED`), and `EMPTY` (coord root present, mission dir absent, #1716) is a genuinely
  distinct branch from `UNMATERIALIZED`. Because the gate contract is the behavioural test
  spec, tests written to it never exercise `EMPTY`'s resolve-primary-and-stamp verdict —
  the exact "silently untested" failure this mission exists to remove. Fix: rewrite C3/C4
  to four states, giving `EMPTY` the same answer as `UNMATERIALIZED`.
- **MAJOR — "eight" vs the real ≥11.** `spec.md` Overview, Assumptions, US5, and
  especially **FR-009's title "All eight exemption mechanisms are retired"** contradict
  NFR-006 ("the count … was wrong (9, not 8)") in the same document, and both contradict
  the ≥11 census. The thesis (stop counting, enumerate, ratchet a shrinking registry) is
  right; the residual "eight" in the normative FR-009 must be reworded to the enumerated
  list so no count is normative.
- **MAJOR — `LEGACY_UNRECORDED` vs the `TopologySurface` type.** `spec.md`/`research.md`
  write it as a `verified_surface_kind`, but the data-model types that field
  `TopologySurface` and defines that enum as a resolvable vocabulary with an explicit
  anti-phantom rule. The two cannot both hold; the data-model must host the sentinel or
  the field must be retyped.
- **MAJOR — FR-004 "are judged" vs NI-6/FR-016/FR-017 "not enforced by the loop."** FR-004
  reads as an unconditional guarantee, but the post-consolidation judgement is a
  **manually-dispatched governed Op** (`plan.md:172-174`) whose enforcement is an
  **external CI check** the mission does not install downstream. In a consumer repo
  without FR-016, a `deferred_to_consolidation` invariant is disclosed (FR-017), never
  judged. FR-004's wording hides the conditionality and should carry the caveat.
- **MAJOR — the owner contract's Surfaces list is under-enumerated.**
  `contracts/tool-artifact-owner.md` omits `merge/ordering.py` and `lanes/merge.py`, both
  live consumers of `COORD_OWNED_STATUS_FILES` (`merge/ordering.py:471`,
  `lanes/merge.py:680,715`). A work package scoped to the documented Surfaces under-sizes
  and collides with the `merge/`-package sequencing constraint (C-001) — which the plan's
  own IC-07(c) risk note already flags as "unsatisfiable as literally written" but does not
  resolve.
- **MINOR / drift:** `SurfaceKind` leftover in the data-model relationships diagram and at
  `data-model.md:231` (should be `ToolSurfaceKind`); GEC invariant ordering (1, 2, 3, 5,
  4); spec Input base `eb06ca176` vs `quickstart.md` base `8074107d7` (plausibly
  legitimate re-grounding, but unreconciled); C-001 "two PRs" vs quickstart "three"; and
  **ADR-1's body claims a five-member enum (`PRIMARY | COORD | LANE | CONSOLIDATED | TEMP`)
  while the code declares only `PRIMARY | COORD`** — the companion glossary edit
  (`docs/context/orchestration.md:620`) got this right, so the ADR contradicts both the
  code and its own glossary. Separately, `plan.md` deliberately supersedes decision record
  `DM-01KY7AKXNJZCB2J2W411YM3B9F` (IC-04 "zero `merge/` footprint") while leaving the
  superseded record and `tracers/design-decisions.md` unedited "as history" — defensible,
  but a reader landing on that decision record cold is misled.

For the record, the checks that **passed**: the negative-invariant `result` state set is
consistent across spec, data-model, and the provenance contract (terminal set and the
non-terminal `deferred_to_consolidation` agree); the fourth verdict value
`pass_pending_consolidation` is a distinct axis from the resolver-state framing (no
conflation); and the stamping rules agree across NFR-001, GEC-3/GEC-5, and AH-2 — except
the `EMPTY` omission in the gate contract noted above.

## 4. Is the decomposition sound, and is the claimed sequencing real?

The Implementation Concern map is rigorous and the slicing is *forced by shared consumers,
not chosen* — IC-07's six-way split is justified by measured consumer overlap; IC-08
ratchet-first is a genuine countermeasure to the named "stall two-thirds through the
strangler and leave one more compensator than we started with" failure mode; the IC-09 →
IC-03 fold and the IC-04 zero-`merge/`-footprint decision are sound. The sequencing
constraints (IC-01 first, IC-02 as schema root, IC-06 → IC-08 → IC-07) are correctly
ordered.

The claimed **sequencing** is real; the claimed **parallelism** is thin, and the plan says
so outright: "the file graph is one large connected component … Lane A carries most of the
work … assume roughly serial until the IC-05 check resolves." That honesty is a strength,
not a defect — but it means this is a long, largely serial chain. The one unresolved
sequencing tension is the owner-contract surface omission above: IC-07 group (c) pulls in
`merge/`-package files, colliding with the "merge-package last" rule; the plan flags it but
does not resolve it.

## 5. What is missing entirely

- **FR-015 (archiving)** is half-in — orthogonal to both seams and unoperationalized.
- **FR-016 (the external CI consistency check)** is the linchpin of the entire deferral
  design and the least-specified piece; no artifact defines it as a testable callable.
- **IC-07(f)** depends on a sibling mission "publishing," an external dependency with no
  committed timeline (`research/sibling-mission-coordination.md`).
- Tasks are deliberately not created, so the `owned_files` overlap resolution in the File
  Ownership table has not been validated by `/spec-kitty.tasks` yet.

## 6. Is the scope right?

The mission is two loosely-coupled seams: **gate-execution-context** (surface resolution;
discharges the live, actively-biting defects #1834 and #2885) and **tool-artifact-owner**
(the exemption strangler). They share only IC-11 (the surface→filesystem seam).

- **Keeping them together is defensible.** The ratchet-first countermeasure genuinely means
  a stall leaves the codebase strictly better, and IC-11's totality is best proven by
  repointing *all* its consumers — including Seam 2's — in one pass. That anti-additive
  argument is sound and is the plan's strongest reason to stay unified.
- **But the fault line is real.** Seam 1 is fast, high-value, low-risk, and self-contained
  (US3/C-002 is literally blocking *this* mission's own consolidation); Seam 2 is a large,
  serial, back-loaded strangler with an external sibling dependency and the unresolved
  C-001 tension. If IC-07(f) or the merge-package tension causes real delay, **split at
  IC-05/IC-06** — land Seam 1, make Seam 2 a follow-on — and this should be the pre-agreed
  fallback rather than a mid-mission scramble.
- **FR-015 should come out of scope now** regardless — it is unoperationalized and belongs
  to neither seam.

## The two landed renames (operator's explicit flag)

- `SurfaceKind → ToolSurfaceKind` (`8f1362905`) is a pure, value-preserving type rename:
  members and values byte-identical, all consumers updated, zero dangling references.
- `Surface → TopologySurface` with `PLACEMENT → COORD` (`35f54df21`) **is** a name *and
  value* change (`"placement"` → `"coord"`) — the operator's flag is correct. But it is
  **safe**: that value is a runtime-only in-memory marker, never serialized (the home is
  recomputed on demand by `artifact_home_for(kind)`), never a decision key (only
  `== PRIMARY` is compared; `COORD` is the else-branch — `resolution.py:929/934`), never a
  path segment, and distinct from the persisted `MissionTopology` enum. All value-consumers
  (two pinned tests) were updated in the same commit; no on-disk `"placement"` string
  exists. The persisted-enum migration hazard does not materialize, and the branch suites
  pass (755).

## Fix-list before tasking

All bounded; most are prose reconciliation of the spec/contracts to corrections the
mission already made.

1. **MAJOR** — reconcile the spec to its own census: strike "eight" and reword **FR-009**
   to the enumerated-registry model.
2. **MAJOR** — update **gate contract C3/C4** to four states, giving `EMPTY` the
   resolve-primary-and-stamp verdict (else `EMPTY` ships untested).
3. **MAJOR** — give **FR-014**'s `LEGACY_UNRECORDED` a type home and state the
   `verified_ref` a legacy row carries.
4. **MAJOR** — add `merge/ordering.py` and `lanes/merge.py` to the **owner contract
   Surfaces**, and resolve the C-001 ↔ IC-07(c) tension explicitly.
5. **MAJOR** — reword **FR-004** to reflect operator-dispatched judgement + external-CI
   enforcement.
6. **MAJOR** — **cut FR-015** from scope, or fully specify it (acceptance scenario +
   data-model entity + contract clause).
7. **MINOR** — fix the two bad references (phantom commit `da41c6343` at `data-model.md:52`;
   `SurfaceKind` → `ToolSurfaceKind` at `data-model.md:231`) and reconcile ADR-1's
   five-member claim with the two-member code.

**Bottom line:** a genuinely strong planning set carrying residual prose-reconciliation
debt and two half-specified requirements. Sound to proceed to tasking once the seven items
above are cleared — none of them require redesign.

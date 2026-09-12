---
work_package_id: WP16
title: Truthfulness sweep, census fold, changelog
dependencies:
- WP04
- WP07
- WP08
- WP10
- WP12
- WP13
requirement_refs:
- FR-017
- FR-020
- FR-021
- C-007
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T070
- T071
- T072
- T073
- T076
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/verdict_seam_census.yaml
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/test_verdict_name_truthfulness.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/verdict_seam_census.yaml
- tests/architectural/test_verdict_seam_census.py
- tests/architectural/test_verdict_name_truthfulness.py
- src/specify_cli/cli/commands/agent/workflow.py
- docs/changelog/CHANGELOG.md
- docs/plans/investigations/review-artifact-write-integrity-3044.md
- docs/plans/engineering-notes/coord-splitbrain-rootcause.md
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP16 - Truthfulness sweep, census fold, changelog

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Objective

User Story 5 (spec.md) requires that no test name or contract key in the affected
suites contradicts its own assertions, and FR-020 requires the verdict-seam
contract to be the check's **executable fixture**, not decorative prose. FR-021
requires FR-001/FR-010/FR-011's observable behaviour changes to reach the
CHANGELOG per DIR-009. This WP is where all three land, plus the doc-surface
truthfulness sweep FR-017/FR-020 name explicitly.

**The contract artifact must be a fixture the check reads, not prose nothing
consults.** The census's expected-set fixture is
`tests/architectural/verdict_seam_census.yaml` — the executable target the
NFR-007 check loads. `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/contracts/verdict-seam-census.md`
is a **retired pointer file**, kept only so references in `plan.md` and
earlier revisions resolve to an explanation rather than stale scaffolding; it
is not the census and this WP does not write into it. WP01, WP04 and WP08
each write their own fragment at
`tests/architectural/census/verdict_seam_ICNN.yaml` (e.g.
`verdict_seam_IC01.yaml`, `verdict_seam_IC04.yaml`, `verdict_seam_IC08.yaml`),
precisely because the slicing gate (`validate_no_overlap`) forbids two
dependency-unordered WPs from both claiming the single
`verdict_seam_census.yaml` file as `owned_files`. **This WP's job is the
fold** — it is the one WP positioned after every fragment-writing WP (WP04,
WP07, WP08, WP10, WP12, WP13 are all upstream dependencies) whose job is to
fold those fragments into the one file the NFR-007 check reads as its
expected set.

**`workflow.py`'s docstring is wrong in three independent ways, not one.** The
current text (`src/specify_cli/cli/commands/agent/workflow.py:1-11`) reads:

```
WP04 (#676) — Review-cycle counter inventory
============================================
The ``review-cycle-N.md`` artifact and the implicit counter ``N`` ... are
mutated in **exactly one** place across the runtime: ``_persist_review_feedback``
in ``src/specify_cli/cli/commands/agent/tasks.py`` (currently lines 403-456).
```

1. **Wrong module.** `_persist_review_feedback` is not in `tasks.py` — it is in
   `src/specify_cli/cli/commands/agent/tasks_materialization.py` (confirmed at
   line 128 of that file today), moved there during a prior god-module
   extraction that predates this mission's own WP06 extraction.
2. **Wrong line numbers.** "currently lines 403-456" does not correspond to the
   function's actual location in either the old or the new module.
3. **Wrong count.** "exactly one" mutation point is false even before this
   mission's changes: `create_rejected_review_cycle` (the actual writer,
   `review/cycle.py`) has at minimum the call sites this mission's own WP01
   census enumerates as writers, and after this mission's WP07/WP10/WP12 land,
   the verdict-relevant mutation points are the ones the census's "Verdict
   writers" table names — plausibly three or more, not one, and the docstring
   must state a number the census actually supports, not a stale claim.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story
  5 (FR-017, FR-020, FR-021, SC-007), the Definitions section's "Affected
  suites" block (load-bearing for T070's denominator).
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-12's
  Risks paragraph, and the "The census fixture is fragmented" note under
  "Implementation Concern Map" explaining why per-concern fragments exist at
  all.
- `tests/architectural/verdict_seam_census.yaml`
  — the document this WP folds fragments into; read its "Related" section for
  the doc surfaces this WP reconciles.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/quickstart.md` — the
  "The census" section's exact verification command
  (`pytest tests/architectural/ -k "verdict_seam_census"`).
- `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md` — DIR-009's
  binding force for the CHANGELOG entry (referenced by C-007/FR-021).

**Binding constraint — the audit denominator (SC-007) is machine-derivable, not
a hand-scoped subset, and it is a DIFFERENT, smaller set than NFR-001's
affected-suites collection.** The full rule: *every test in a file this
mission's diff touches, plus every test in the affected suites whose name or
`requirement_refs` marker references a guard, verdict, durability, override or
provenance concept.* That is a union of two counts — **|touched|** (tests in
files the cumulative diff touches) and **|keyword-matched|** (tests in the
affected-suites paths whose name/marker hits the concept list) — not the full
affected-suites collection. **2820 is the full affected-suites collection**
(`research/baseline-8466727eb.md`'s NFR-001 figure, the denominator for a
*different* requirement) and is **not** SC-007's denominator; SC-007's
touched-∪-keyword-matched union is plausibly a few hundred tests, not
thousands. Do not anchor this audit's sanity check on the 2820 figure — a
count near 2820 here would indicate the enumeration rule collapsed to "the
entire affected suites," not that it correctly derived the smaller SC-007
union. Do not silently narrow this to "the tests I personally touched" or "the
tests in this WP's owned files" either — an unbounded hand audit left
ungoverned is exactly what SC-007 exists to prevent by stating the rule as
something a reviewer can re-derive. Build the **rule** as an executable check
(a script or test that enumerates the denominator and flags candidate
name/assertion mismatches via a pattern, e.g. a test named
`test_*_rejects_*`/`test_*_refuses_*` whose body contains no `pytest.raises`)
rather than silently shrinking the population reviewed. State explicitly in
this WP's Activity Log the **separate** `|touched|` and `|keyword-matched|`
counts the rule actually enumerated (both re-derivable — `|touched|` from
`git diff --name-only <merge-base>...HEAD -- 'tests/*'`, `|keyword-matched|`
from the marker/name grep over the affected-suites paths) and how many were
flagged for manual disposition, so the boundary is auditable rather than
assumed.

## Subtask T070 — Audit test names against assertions over the bounded denominator

- **Purpose**: Deliver SC-007 — no test name or contract key contradicts its
  own assertions — over the stated, re-derivable denominator, not a
  convenience subset.
- **Steps**:
  1. Build the denominator mechanically, as the union of two SEPARATELY
     re-derivable counts: **|touched|** — every test file this mission's
     cumulative diff touches (across WP01-WP15, not only this WP's own owned
     files — use `git diff --name-only <merge-base>...HEAD -- 'tests/*'`
     against the mission's base) — and **|keyword-matched|** — every test in
     the affected-suites paths (spec.md's Definitions section list) whose name
     or `requirement_refs` pytest marker references one of: guard, verdict,
     durability, override, provenance. Record `|touched|` and
     `|keyword-matched|` as two distinct numbers, not one combined figure. **Do
     not check this count against the 2820-test affected-suites collection**
     — that figure is NFR-001's denominator (the full affected-suites
     collection), a different and much larger set than SC-007's touched-∪-
     keyword-matched union; a count anywhere near 2820 here is itself a sign
     the enumeration collapsed to "the whole affected suites" rather than
     correctly deriving the smaller union, and must be fixed before auditing,
     not treated as confirmation.
  2. For every enumerated test, compare its name against its actual assertions.
     Prioritize the pattern most likely to hide a real defect: a name asserting
     refusal/rejection (`*_rejects_*`, `*_refuses_*`, `*_is_blocked_*`) whose
     body contains no `pytest.raises`/equivalent failure assertion — this is
     the exact shape T003's house-style reference WP flagged in the predecessor
     mission (`test_new_cycle_body_never_duplicates_a_prior_cycle_file` was
     found not wrapped in `pytest.raises` despite its name).
  3. Build this comparison as a committed, re-runnable check:
     `tests/architectural/test_verdict_name_truthfulness.py` (this WP's own
     `create_intent` — coordinate registration with WP01's shard-map pattern in
     `tests/_arch_shard_map.py` rather than adding an unregistered check) —
     the census check's own precedent (fail when a new untracked member
     appears) is the model: this audit should be re-runnable, not a one-time
     manual pass with no artifact.
  4. For every genuine mismatch found (name contradicts assertion), fix the
     **test**, not the code under test, unless the audit also reveals the code
     itself is wrong — in which case file that as a defect against the WP that
     owns the affected module rather than silently patching it here (this WP's
     `owned_files` does not include production review/status code).
  5. Include the flagship end-to-end test named in User Story 5 Acceptance
     Scenario 2 ("the flagship end-to-end test asserts the non-forced path") in
     this audit explicitly — confirm it exercises the ordinary path, not a
     forced/override path, and rename or fix it if it does not.
- **Files**: `tests/architectural/test_verdict_name_truthfulness.py` (this WP's
  own new, owned test module), plus any test files whose names are corrected
  as a result (outside this WP's `owned_files` list unless the fix belongs to
  a module this WP already owns — file cross-WP findings rather than editing
  another WP's owned surface).
- **Validation checklist**:
  - [ ] The enumeration rule is stated explicitly (in the audit script's
        docstring or this WP's PR description) and its resulting count is
        recorded.
  - [ ] Every flagged name/assertion mismatch is either fixed (test renamed or
        corrected) or filed as a cross-WP finding with the exact test node id.
  - [ ] The flagship end-to-end test's ordinary-path assertion is explicitly
        confirmed.
- **Edge Cases**: a test name that is intentionally broad (e.g.
  `test_review_cycle_lifecycle`) covering multiple assertions including but not
  limited to a refusal — do not flag every broadly-named test as a mismatch;
  scope the pattern-matching to names that make a specific behavioral claim
  (rejects/refuses/blocks/never/always) the body must then support.

## Subtask T071 — Fold the census fragments into the contract the check reads

- **Purpose**: Discharge FR-020 for real — the census check must read
  `tests/architectural/verdict_seam_census.yaml` as its expected-set fixture,
  and that file must be current, which requires folding every per-concern
  `tests/architectural/census/verdict_seam_ICNN.yaml` fragment written along
  the way.
- **Steps**:
  1. Enumerate every fragment file under `tests/architectural/census/`
     that upstream WPs (starting with WP01's own `verdict_seam_IC01.yaml`, and
     WP04's `verdict_seam_IC04.yaml` and WP08's `verdict_seam_IC08.yaml`, plus
     any other WP the tasks.md ownership table shows writing to that fragment
     directory) have produced by this point in the mission.
  2. Merge each fragment's rows into the matching table in
     `tests/architectural/verdict_seam_census.yaml` — "Verdict writers",
     "Location resolvers", "Verdict readers and their declared polarity",
     "Frontmatter readers" — replacing any placeholder rows with the real,
     sourced content. Preserve each row's provenance (which WP/fold populated
     it) as a comment or a `Retired by` column entry where applicable.
  3. Confirm the NFR-007 architectural check (WP01's deliverable) actually
     reads this folded file as its expected set — run the check
     (`pytest tests/architectural/ -k "verdict_seam_census"`) and confirm it
     passes against the folded content, and confirm introducing an
     unregistered writer/resolver/reader still fails it (the check's own
     enumerated-membership invariant).
  4. Confirm every `retire` row names its retiring FR (the census's own stated
     invariant #2: *"Every `retire` row names the FR that retires it"*) — a
     `retire` row with no FR is a census failure per WP01's own rule, and this
     fold must not silently introduce one.
  5. Delete or archive the per-concern fragment files once folded (confirm with
     the census check that nothing still depends on their independent
     existence) so the document nothing-consults problem does not simply move
     from "the census" to "the fragments."
- **Files**: `tests/architectural/verdict_seam_census.yaml`
  and the fragment files under `tests/architectural/census/`
  (deletion/archival only — their creation is each contributing WP's own
  responsibility, not this one's)
- **Validation checklist**:
  - [ ] Every table in `verdict_seam_census.yaml` has real rows, no
        placeholders remain.
  - [ ] Every `retire` row names a specific FR.
  - [ ] Every reader row declares exactly one polarity, and no
        safety-relevant reader is `skip` (cross-check against WP14's output).
  - [ ] The NFR-007 check passes against the folded document and still fails
        when an unregistered member is introduced (spot-check by temporarily
        adding an unregistered symbol and confirming the check reds, then
        reverting).
- **Edge Cases**: a fragment written by a WP that has not actually merged yet
  by the time this WP starts (dependency ordering says it should have, but
  confirm) — treat a missing expected fragment as a blocker, not a silently
  skipped row.

## Subtask T072 — Correct `workflow.py`'s inventory docstring and the doc surfaces

- **Purpose**: Fix the three-way-wrong docstring named in this WP's Objective,
  and reconcile the doc surfaces FR-020 names as needing correction in the same
  work package.
- **Steps**:
  1. In `src/specify_cli/cli/commands/agent/workflow.py`, rewrite the module
     docstring's inventory section: correct the module reference from
     `tasks.py` to `tasks_materialization.py`, correct or remove the specific
     stale line numbers (state "see `_persist_review_feedback`" without a
     brittle line pin, or re-derive the current line number and note it will
     drift), and correct "exactly one" to the actual count the folded census
     (T071) supports — cite the census document as the source of truth for
     that count rather than re-asserting a number in prose that can itself go
     stale.
  2. Reconcile `docs/plans/investigations/review-artifact-write-integrity-3044.md`:
     this document's tables cite `cycle.py:272,299`, `artifacts.py:199,214`,
     and other line-pinned locations from before this mission's rebuild. Add a
     dated note (do not silently rewrite the historical investigation content)
     pointing to `tests/architectural/verdict_seam_census.yaml` as the current
     source of truth for writer/resolver/reader enumeration, and correct any claim this
     mission has now falsified in place (e.g. "kind-blind
     `candidate_feature_dir_for_mission`" is superseded by WP04's
     `REVIEW_CYCLE` kind and WP13's unified resolver).
  3. Reconcile `docs/plans/engineering-notes/coord-splitbrain-rootcause.md`
     similarly: its review-cycle-N.md row (in its authority-matrix table)
     describes the pre-ADR "dual authority" / "written to COORD but declared
     PRIMARY" split-brain this mission's ADR 2026-08-03-1 and WP04/WP07/WP13
     resolve. Add a dated resolution note against that row citing the ADR and
     this mission, without rewriting the historical diagnosis wholesale — the
     value of an engineering note is its record of what was true when written;
     mark it superseded, don't erase it.
  4. Confirm no other doc surface in `docs/` makes a claim this mission's own
     spec.md, ADR, or census document now contradicts — a targeted grep for
     `review-cycle` and `WORK_PACKAGE_TASK` limited to `docs/plans/` and
     `docs/adr/` (excluding `docs/adr/3.x/2026-08-03-1-*` itself, which is
     already correct) is sufficient; a full-repo doc sweep is out of scope for
     this WP's `owned_files`.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py`,
  `docs/plans/investigations/review-artifact-write-integrity-3044.md`,
  `docs/plans/engineering-notes/coord-splitbrain-rootcause.md`
- **Validation checklist**:
  - [ ] `workflow.py`'s docstring names the correct module
        (`tasks_materialization.py`), makes no brittle stale line-number claim,
        and states a mutation-point count the folded census actually supports.
  - [ ] Both `docs/plans/` pages carry a dated resolution/supersession note
        against the specific claims this mission falsifies, without deleting
        the historical record.
  - [ ] A targeted grep for the retired seam's stale claims across
        `docs/plans/` and `docs/adr/` (excluding this mission's own ADR) turns
        up nothing further, or any remaining hit is filed rather than silently
        left.
- **Edge Cases**: a doc surface making a claim that was already correct and
  remains correct after this mission (e.g. `WORK_PACKAGE_TASK`'s placement is
  unchanged per ADR 2026-08-03-1's "P-1 is preserved" note) — do not "correct"
  claims that were never wrong; over-editing a historical document is its own
  truthfulness failure.

## Subtask T073 — Add the CHANGELOG entry for the behaviour changes

- **Purpose**: DIR-009 makes a CHANGELOG entry binding for FR-001, FR-010 and
  FR-011's observable changes to the review and merge contract. FR-021 exists
  specifically because an earlier mission revision omitted this.
- **Steps**:
  1. In `docs/changelog/CHANGELOG.md`, under the current `## [Unreleased]`
     section (matching the existing entry style — bold lead sentence, mission
     name and issue/PR reference in parens, then a paragraph of before/after
     contrast), add an entry covering:
     - **FR-001**: the status event is now the sole authority for *which*
       verdict is current, with a reader downstream of the reducer — no
       consumer answers "is this WP approved?" by parsing artifact
       frontmatter anymore (SC-011).
     - **FR-010**: an arbiter override now durably persists and clears the
       merge gate without a flag, closing the gap where the arbiter writer
       never committed its output.
     - **FR-011**: an arbiter override can no longer be indistinguishable
       from a genuine approval — it is recorded and read as a first-class
       outcome.
  2. Follow the predecessor mission's own changelog entry (search
     `docs/changelog/CHANGELOG.md` for the #3156/#2697/#990 predecessor's
     entry, added by the branch this mission is built on) as the style
     template — this mission's entry should read as a natural continuation of
     that one, not a disconnected new item, since it completes work the
     predecessor started.
  3. Cross-reference the mission slug
     (`review-cycle-verdict-seam-rebuild-01KZ2W7W`) and the governing ADR
     (`2026-08-03-1`) in the entry, so a reader tracing the changelog back to
     source material lands in the right place.
  4. Confirm the entry is under the correct version section (`[Unreleased] -
     3.2.6` or whatever section is current at merge time — check the file's
     current top section before adding, since it may have advanced since this
     prompt was written).
- **Files**: `docs/changelog/CHANGELOG.md`
- **Validation checklist**:
  - [ ] FR-001, FR-010 and FR-011's observable changes each have a distinct,
        readable entry (not one vague combined bullet).
  - [ ] The entry follows the file's existing style (bold lead, mission/issue
        reference, before/after contrast paragraph).
  - [ ] The entry lands under the currently-open `[Unreleased]` section, not a
        stale or already-released one.
- **Edge Cases**: none — this is a documentation-only addition; do not let it
  expand into re-describing the entire mission's scope (FR-002 through FR-020
  are not "observable changes to the review and merge contract" in DIR-009's
  binding sense and do not need their own entries here).

## Subtask T076 — Draft the closing-clause block and the epic carve-out

- **Purpose**: C-007 requires the PR that lands this mission to carry `Closes`
  clauses for the predecessor's five reproductions — #2275, #2996, #990,
  #2697, #2646 — and to state, honestly, that Epic #3044 does **not** close:
  its children are #2275, #2996, #990 and #3088 (verified, not assumed), this
  mission does not touch #3088, and #3088 staying open means the epic stays
  open. An earlier mission revision named #3158 as the blocker instead;
  #3158 is not a child of #3044, and that error must not recur in the PR
  text.
- **Steps**:
  1. Draft the literal closing-clause block: `Closes #2275, Closes #2996,
     Closes #990, Closes #2697, Closes #2646` (check `CONTRIBUTING.md` and a
     handful of recently-merged PRs for this repository's exact house style
     for multiple `Closes` references — some hosts require one clause per
     line rather than a comma-joined list — and match it rather than
     inventing a format).
  2. Immediately following the closing-clause block, draft the explicit
     carve-out sentence: *"Epic #3044's children are #2275, #2996, #990 and
     #3088 (verified, not assumed). This mission does not touch #3088, which
     stays open; the epic therefore does not close, and this PR does not
     claim it does."*
  3. Before finalizing, cross-check that each of the five closed issues
     actually has its regression pinned somewhere in this mission's diff and
     green: #990/#2996(b) via the content-identity guard's pinned tests
     (WP10's T045), #2646 via `tests/regression/test_2646_stale_verdict_closes_via_fr001.py`
     (confirmed green by WP17's T074), and #2275/#2697 via whichever WP's
     Reviewer Guidance names their pinned regression. Do not include a
     `Closes` clause for an issue whose regression is not actually present
     and green in the diff at the point this WP runs.
  4. Record the drafted block and carve-out sentence in this WP's Activity
     Log, verbatim, so whoever opens the actual PR (per this mission's
     draft-PR-first, operator-merges workflow) has the exact text to use
     rather than reconstructing it. If C-006's reviewable-PR-sequence means
     this mission lands as multiple PRs into the mission branch, state
     explicitly that the closing clauses belong on the **final** PR that
     merges the mission branch to `main`, not on an intermediate PR — a
     premature `Closes` clause on an intermediate PR would close the issue
     before the fix has actually reached `main`.
- **Files**: this WP's Activity Log (no production code or `CHANGELOG.md`
  change beyond T073's own entry)
- **Validation checklist**:
  - [ ] The drafted closing-clause block names exactly #2275, #2996, #990,
        #2697, #2646 — no more, no fewer, and not #3158.
  - [ ] The epic carve-out sentence explicitly states #3044 does not close
        and names #3088 as the reason, verified (not assumed) against the
        actual issue tracker relationship.
  - [ ] Each closed issue's regression pin is cross-checked as present and
        green in this mission's diff before being included in the block.
- **Edge Cases**: none beyond the multi-PR sequencing note above.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement`
this WP may branch from a dependency-specific base (WP04, WP07, WP08, WP10,
WP12 and WP13 must all be merged into whatever base this WP branches from), but
completed changes must merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly
redirects the landing branch.

## Definition of Done

- [ ] T070: `tests/architectural/test_verdict_name_truthfulness.py` exists as a
      committed, re-runnable check, registered in `tests/_arch_shard_map.py`;
      the audit denominator is stated as a re-derivable rule (separate
      `|touched|` and `|keyword-matched|` counts), its resulting counts are
      recorded, and every flagged mismatch is fixed or
      filed with an exact test node id.
- [ ] T071: `tests/architectural/verdict_seam_census.yaml` has no placeholder
      rows, every `retire` row names its FR, every reader declares one
      polarity, and the NFR-007 check reads it as its expected set.
- [ ] T072: `workflow.py`'s docstring is correct on module, line-number
      brittleness, and count; both `docs/plans/` pages carry dated
      supersession notes without erasing history.
- [ ] T073: the CHANGELOG carries a distinct entry for each of FR-001, FR-010,
      FR-011 under the correct `[Unreleased]` section.
- [ ] T076 (C-007): the drafted closing-clause block names exactly #2275,
      #2996, #990, #2697, #2646, and the epic carve-out sentence explicitly
      states Epic #3044 does not close because #3088 stays open — recorded
      verbatim in this WP's Activity Log.
- [ ] `ruff` and `mypy --strict` clean on every touched code file (docs are
      exempt from these gates but must pass the terminology guard —
      `pytest tests/architectural/test_no_legacy_terminology.py`).
- [ ] Full regression on `tests/architectural/` — the census check and the new
      truthfulness audit both pass; no new failures beyond
      `research/baseline-8466727eb.md`'s two rows (NFR-001).
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Denominator-shrinking risk**: the touched-∪-keyword-matched audit is large
  enough that quietly narrowing it to "tests I have time to read" is the path
  of least resistance. Mitigate by building the enumeration as an executable rule with
  a recorded count, so the boundary is auditable by a reviewer rather than
  trusted on the implementer's word.
- **Fragment-fold omission risk**: if an upstream WP's fragment file is missing
  or incomplete when this WP starts, folding an incomplete census would ship a
  document that looks authoritative but understates the true set. Mitigate by
  treating a missing expected fragment as a blocker on this WP, not a gap to
  paper over.
- **Historical-document over-editing risk**: correcting stale claims in
  `docs/plans/` pages can tempt a full rewrite that destroys the record of
  what was believed at the time. Mitigate by adding dated supersession notes
  rather than rewriting in place.
- **workflow.py count risk**: restating "exactly one" as a different fixed
  number risks going stale again the next time a writer is added or retired.
  Mitigate by citing the census document as the source of truth in the
  docstring rather than hard-coding a number that will need a fourth
  correction later.

## Reviewer Guidance

- Confirm the audit denominator's enumeration rule and resulting count are
  stated explicitly, not asserted — ask to see the script or check that
  produced the count.
- Confirm `tests/architectural/verdict_seam_census.yaml` has zero remaining
  placeholder (or fragment-pending) rows, and that the NFR-007 check actually
  reads this file (not a copy, not a fragment, and not the retired
  `kitty-specs/.../contracts/verdict-seam-census.md` pointer) as its expected
  set.
- Confirm `workflow.py`'s corrected docstring names `tasks_materialization.py`,
  not `tasks.py`, and does not restate a brittle absolute line number as its
  primary claim.
- Confirm the CHANGELOG entry is genuinely new content under the current
  `[Unreleased]` section, not a duplicate of the predecessor mission's already-
  landed entry.
- Confirm T076's closing-clause block names exactly the five predecessor
  issues and no others, and that the epic carve-out sentence is present and
  correctly attributes the non-closure to #3088 — not to #3158, which is not
  a child of #3044.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.
- 2026-08-05T04:29:30Z – claude – lane=doing – **T071 census fold.** Folded
  `verdict_seam_IC01.yaml` (42 active rows: 16 writer / 10 resolver / 16
  reader) and `verdict_seam_IC08.yaml` (5 retire rows, all resolver, FR-007/
  FR-003/FR-009) into `tests/architectural/verdict_seam_census.yaml` (47 rows
  total), preserving every row's original attribution comment plus a new
  `source: WP01/IC01` / `WP08/IC08` field per row. **`verdict_seam_IC04.yaml`
  contributes ZERO rows** — confirmed by reading it in full: it is a
  partition/classifier/routing decision record (the `REVIEW_CYCLE` kind,
  its COORD placement, four cross-WP-dependency findings), not a
  writer/resolver/reader enumeration; WP01's own IC01 header already says so
  explicitly. The task prompt's framing ("fold every row from IC01, IC04, and
  IC08") does not hold for IC04 — disclosed rather than fabricating rows to
  make it hold. Re-pointed `_CENSUS_FIXTURE_RELPATH` in
  `tests/architectural/test_verdict_seam_census.py` from
  `census/verdict_seam_IC01.yaml` to the folded `verdict_seam_census.yaml`;
  restructured `test_wp01_fixture_retires_nothing` to check the IC01
  fragment directly (its own historical claim) rather than the post-fold
  document (which now legitimately carries retire rows); merged
  `test_ic08_retire_rows_are_valid`'s non-vacuity purpose into
  `test_real_fixture_retire_rows_are_valid` (now genuinely non-vacuous
  post-fold, no longer a separate IC08-specific load). Spot-checked in a
  scratch copy (`/home/stijn/.claude/jobs/c55ec787/tmp/wp16-probe/`, never
  the tracked tree, deleted after): (1) a synthetic new writer function
  reds `test_derived_census_matches_fixture[writer]` against the folded
  file; (2) a retire row with no `retiring_fr` appended to the folded file
  reds `test_real_fixture_retire_rows_are_valid`. Both invariants confirmed
  live post-repoint. Cross-checked WP14's reader-polarity work (T063–T066)
  against the folded reader rows: all five readers named in WP14's Objective
  table are accounted for by name/reasoned-absence (recorded as an
  informational cross-reference block in the census header, since no
  `polarity`/`safety_relevant` field exists anywhere in the actual
  `_CensusRow` schema — WP14's own task file describes a "declared polarity"
  table in IC01 that does not exist there either; WP14 recorded polarities in
  prose instead). No safety-relevant reader is `skip`. **Fragments NOT
  deleted**: `verdict_seam_IC01.yaml`/`IC04.yaml`/`IC08.yaml` are cited by
  path from WP01/WP04/WP06/WP07/WP08/WP10/WP11/WP12/WP14/WP18's own task
  files plus `review/cycle.py`, `_review_cycle_reconcile_doctor.py`,
  `doctor.py`, `test_analysis_report_rehome.py`,
  `test_merge_reconciliation_class_guard.py`, and
  `test_doctor_cli_surface_golden.py` — none owned by this WP. Per this WP's
  own rule ("if something outside your owned files still references a
  fragment path, STOP and report rather than breaking it"), the fragments
  stay on disk as a frozen historical record; only the check's expected-set
  fixture moved. Full `tests/architectural/` suite green after the re-point
  (see final report for verbatim counts).
- 2026-08-05T04:29:30Z – claude – lane=doing – **T070 name-truthfulness
  audit.** Built `tests/architectural/test_verdict_name_truthfulness.py`
  (registered in `tests/_arch_shard_map.py`'s shard_2, the lightest shard by
  file count at landing time). Denominator, re-derived via
  `specify_cli.core.vcs.git.merge_base_changed_files` against
  `pr/review-verdict-write-integrity-01KZ1CGF` (this mission's own base):
  **|touched| = 287** test functions (in 21 touched `.py` test files, of 26
  touched `tests/*` files total), **|keyword-matched| = 100** test functions
  (over spec.md's Definitions-section affected-suites paths, matched on
  name only — no `requirement_refs` pytest marker exists anywhere in this
  codebase; confirmed by grep and by `pytest.ini`'s registered-markers list
  carrying no such entry, so the task prompt's "name or requirement_refs
  marker" phrasing is corrected to name-only in the committed check's own
  docstring). **Union = 348** (39 overlap), far below the 1000-ceiling
  sanity guard and nowhere near NFR-001's unrelated ~2820-test denominator.
  Mechanical scan (refusal-shaped name: `_rejects_`/`_refuses_`/`_blocked_`/
  `_never_`, no visible failure-proving assertion) flagged 6 candidates
  across two heuristic passes; 4 were true negatives on first broadening
  (isinstance-of-a-Refuse-class, `exit_code == 1`, `blocking_verdicts ==
  ()`, `"review_result" not in snapshot`) and are folded into the check's
  `_has_failure_assertion` predicate directly; 1 remains a documented true
  negative (`test_both_stranded_classes_are_never_conflated_across_missions`
  — a genuine non-empty-set-equality proof the mechanical shape can't see)
  recorded in `_REVIEWED_TRUE_NEGATIVES`. **One genuine mismatch found and
  filed** (not fixed — file not owned by WP16):
  `tests/review/test_reader_polarity_merge_gate_regression.py::test_arbiter_override_reader_refuses_a_malformed_event_sourced_slot`
  — named "refuses" but its own docstring and `assert result == []` describe
  a SKIP polarity (silent empty result, no raise); filed against WP14 in
  `_FILED_CROSS_WP_FINDINGS` with the reasoning and a suggested rename.
  **Separately, by direct reading (not the mechanical name-pattern, since its
  name doesn't match the four canonical shapes), the single highest-value
  finding of this audit:**
  `tests/integration/test_review_cycle_rejection_only.py::test_approving_a_rejected_wp_writes_no_verdict_artifact`
  — named "writes NO verdict artifact" while its own docstring and body
  (`assert latest is not None`, `assert latest.verdict == "approved"`) prove
  the opposite: an ordinary approve now DOES write a fresh approved verdict
  artifact. This is the flagship end-to-end test User Story 5 AC2 names (its
  own docstring calls it "this mission's most direct evidence" the fix
  closes the gap at the real CLI boundary) — its AC2 requirement (asserts
  the non-forced path, never passing `--skip-review-artifact-check`) IS
  satisfied; only its NAME is wrong. Filed as a cross-WP finding (WP16 does
  not own `tests/integration/test_review_cycle_rejection_only.py`); a
  dedicated regression test
  (`test_flagship_end_to_end_test_asserts_the_non_forced_path`) confirms the
  AC2 requirement mechanically regardless of the naming defect. Confirmed
  WP10's own precedent rename
  (`test_new_cycle_body_never_duplicates_a_prior_cycle_file` →
  `test_duplicate_prose_in_an_ordinary_feedback_file_is_admitted`) is intact
  and no longer matches the refusal-name pattern
  (`test_wp10_flagship_rename_precedent_is_not_re_flagged`).
- 2026-08-05T04:29:30Z – claude – lane=doing – **T072 workflow.py docstring +
  doc-surface reconciliation.** Corrected `workflow.py`'s module docstring:
  module reference `tasks.py` → `tasks_materialization.py` (confirmed
  `_persist_review_feedback` is defined at `tasks_materialization.py:201`,
  not the task prompt's claimed line 128 — `tasks.py` only re-exports the
  symbol); removed the brittle absolute line-number pins throughout,
  replacing them with function-name references; replaced the stale
  "exactly one" mutation-point claim with a pointer to
  `tests/architectural/verdict_seam_census.yaml` as the source of truth for
  the current count (16 active writers as of this fold), rather than a new
  hardcoded number that would need a fourth correction later. Added a dated
  (2026-08-05) supersession note to
  `docs/plans/investigations/review-artifact-write-integrity-3044.md`
  correcting two falsified claims ("only review-cycle artifact writer" —
  this mission's Option A/B were both adopted; "location split already
  closed" — qualified by the new create-window PRIMARY/COORD split this
  mission's ADR documents) without rewriting the original analysis. Added a
  dated resolution note to
  `docs/plans/engineering-notes/coord-splitbrain-rootcause.md` against its
  `review-cycle-N.md` authority-matrix row, citing ADR `2026-08-03-1` and
  this mission's WP04/WP07/WP13, and noting the row's two cited call-site
  line numbers (`cycle.py:272,299` → `artifacts.py:199,214`) no longer
  describe live code at those lines (the WP16 task prompt attributed these
  exact citations to the *investigations/3044* doc; they actually live in
  *this* doc — corrected here, not there). Targeted grep sweep of
  `docs/plans/` and `docs/adr/` (excluding `docs/adr/3.x/2026-08-03-1-*`) for
  `review-cycle`/`WORK_PACKAGE_TASK`: no other doc asserts a load-bearing
  claim this mission falsifies. One minor, out-of-owned-files finding: ADR
  `docs/adr/3.x/2026-07-23-1-surface-vocabulary-two-domains-and-topology-surface-rename.md`
  lists `_resolve_review_cycle_read_dir` among six scattered surface→
  filesystem translation call paths; that function is now deleted (WP13,
  per `verdict_seam_IC04.yaml`'s WP04-XWP-02 status note) — not fixed here
  (WP16 does not own this ADR; ADRs are also not normally revised
  post-publication), disclosed for a future doc pass.
- 2026-08-05T04:29:30Z – claude – lane=doing – **T073 CHANGELOG.** Added
  three distinct entries under the current `## [Unreleased] - 3.2.6` →
  `### 🐛 Fixed` section, immediately following the predecessor mission's
  own `#3044`/`#2275`/`#2996`/`#990`/`#2697`/`#2646` entry (as its natural
  continuation, per the task's own instruction) — one each for FR-001 (sole
  verdict authority, reader downstream of the reducer), FR-010 (arbiter
  override durably persists and clears the gate without a flag), and FR-011
  (an override can no longer be indistinguishable from a genuine approval).
  Each names the mission slug and ADR `2026-08-03-1`. Terminology guard
  (`test_no_legacy_terminology.py`) reconfirmed green after the edit.
- 2026-08-05T04:29:30Z – claude – lane=doing – **T076 closing-clause block +
  epic carve-out, drafted verbatim below for the final PR to `main` (per
  C-006's multi-PR sequencing — NOT for an intermediate PR).** House style
  confirmed against `CONTRIBUTING.md` (no explicit multi-issue-closing
  guidance) and ~15 recently-merged PRs via `gh pr list`: one `Closes #NNNN`
  clause per line, no bullets, no comma-joining (e.g. PRs 3134, 3099,
  3081, 3098 — de-sigilled by the reviewer; these are PR-format exemplars,
  not issues this mission adjudicates, so they must not read as issue-matrix
  rows). Each issue's regression cross-checked present AND green
  immediately before drafting (verbatim pytest output in the final report):
  - **#2646** — `tests/regression/test_2646_stale_verdict_closes_via_fr001.py`
    (2 passed) — the only one of the five with a file named by its issue
    number.
  - **#990 / #2996(b)** — pinned by BEHAVIOUR, not filename, per the task's
    own guidance: `tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected`
    and its sibling byte-copy-under-a-different-name test (WP10's T045
    content-identity guard) — 2 passed.
  - **#2697** — `tests/review/test_cycle.py::test_create_rejected_review_cycle_raises_when_commit_fails`,
    whose own docstring names "Cycle 2 fix (#2697)" — 1 passed. (No WP's
    Reviewer Guidance names this citation, contrary to the task prompt's
    assumption — found by direct grep of the test file itself instead.)
  - **#2275** — this mission's own `issue-matrix.json` names its discharge
    as "the FR-001 authority split (WP07)" but cites no specific test;
    WP07's sole owned test file is `tests/status/test_reducer.py`, whose
    `TestFindRejectedReviewArtifactConflictsEventSourced` class (T029,
    WP07, FR-001) is the direct behavioural proof — the merge/lane gate now
    consults the event-sourced answer, with the event winning on
    disagreement, closing exactly #2275's "same gate reads different
    partitions" / "stale rejected verdict stays authoritative" shape — 5
    passed. Pinned by behaviour, not an issue-numbered filename, same as
    #990/#2996(b).
  - All five regressions confirmed present and green immediately before
    this entry was written (see final report for verbatim `pytest` output).

  **Drafted closing-clause block (verbatim, for the final PR only):**

  ```
  Closes #2275
  Closes #2996
  Closes #990
  Closes #2697
  Closes #2646
  ```

  **Drafted epic carve-out sentence (verbatim, immediately following the
  block above):**

  > Epic #3044's children are #2275, #2996, #990 and #3088 (verified, not
  > assumed). This mission does not touch #3088, which stays open; the epic
  > therefore does not close, and this PR does not claim it does.

  #3158 does **not** appear anywhere above — confirmed it is not a child of
  #3044 (it is the rename-debt deferral referenced elsewhere in this
  mission's own spec.md, unrelated to this epic's child set).
- 2026-08-05T00:00:00Z – claude-opus-5 – lane=approved – **WP16 REVIEW —
  APPROVED.** Verified independently on lane-h HEAD `d0d1f0fe0`:
  **(1) Census fold is REAL, not decorative** — `_CENSUS_FIXTURE_RELPATH`
  now points at the folded `tests/architectural/verdict_seam_census.yaml`
  (47 rows: 42 active from IC01, 5 retire from IC08) and `_CENSUS_ROWS` is
  loaded from it at collection time. **(2) Invariants survived the re-point
  — mutation-tested in a scratch copy** (`$CLAUDE_JOB_DIR/tmp/wp16-mut`,
  never the tracked tree): a synthetic in-scope writer reds
  `test_derived_census_matches_fixture[writer]` (growth still caught), and a
  `status: retire` row with no `retiring_fr` reds
  `test_real_fixture_retire_rows_are_valid` (FR-naming still enforced). Both
  confirmed live. **(3) Every retire row names its FR** (IC08's five,
  FR-007/003/009); no manufactured arbiter row — the arbiter reader stays a
  reasoned absence per WP14. **(4) T070 denominator NOT collapsed**:
  |touched|=287, |keyword-matched|=100, union=348 — two separate counts,
  below the 1000 guard ceiling, nowhere near NFR-001's ~2820. WP10's rename
  precedent treated as already-fixed. **(5) T076 Closes block** = exactly
  #2275/#2996/#990/#2697/#2646; #3158 correctly EXCLUDED; #3044/#3088
  carve-out present; each regression cross-checked at its real pinning
  location. **(6) CHANGELOG** = three distinct FR-001/FR-010/FR-011 entries
  under `[Unreleased] - 3.2.6` citing ADR `2026-08-03-1`, no ballooning.
  **(7) Gates**: `tests/architectural/` full = **1570 passed, 4 skipped, 2
  xfailed, 0 failed** (`-n auto --dist loadfile`, 329s); ruff + `--select
  C901` + `mypy --strict` clean on touched files; zero new suppressions.
  **Deviations adjudicated:** (a) *Fragments NOT deleted (T071 step 5)* —
  ACCEPTED: the FR-020 goal (the check reads ONE folded doc as its expected
  set) IS met; the three `census/verdict_seam_IC0N.yaml` fragments are now
  inert frozen record, still cited by ~10 WP task files + several src/tests
  surfaces WP16 does not own, so deletion would orphan live citations —
  correct stop-and-report. `verdict_seam_IC01.yaml` is legitimately still
  read by `test_wp01_fixture_retires_nothing` (a historical property of
  WP01's own fragment). (b) *IC04 contributes ZERO rows* — CONFIRMED honest
  by opening it: it is a partition/classifier/routing decision record with 0
  writer/resolver/reader category rows; the prompt's "fold every row from
  IC01, IC04, IC08" was wrong about IC04. (c) *Two backwards test names*
  (`test_arbiter_override_reader_refuses_a_malformed_event_sourced_slot` —
  name says refuses, body `assert result == []` skips, WP14's file; and the
  US5-AC2 flagship `test_approving_a_rejected_wp_writes_no_verdict_artifact`
  — name says "no artifact", body asserts `latest.verdict == "approved"`) —
  both CONFIRMED genuine truthfulness defects, both in files WP16 does not
  own, both correctly filed as cross-WP findings with node ids and both
  backed by mechanical compensating guards (the flagship's AC2 non-forced
  path is proven by `test_flagship_end_to_end_test_asserts_the_non_forced_path`).
  Not fixed here is correct scope discipline; **carried to WP17** as US5/
  SC-007 truthfulness residuals (rename or document-as-debt is WP17's call).
  (d) *`tests/_arch_shard_map.py` one-line additive registration* — CONFIRMED
  minimal, required by T070's own instructions. **Out-of-scope red (NOT
  WP16's fault, NOT greened):**
  `tests/status/test_reducer.py::…test_event_sourced_review_result_this_missions_own_meta_json_fixture`
  reds because it hardcodes `slot_present=False` while reading THIS mission's
  own live `status.events.jsonl`, which accumulated `review_result` slots as
  approvals landed — a WP07 test-design fragility; WP16 touches no status
  code. Carried to WP17.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP16 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

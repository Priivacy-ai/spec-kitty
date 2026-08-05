---
work_package_id: WP13
title: Consumer unification
dependencies:
- WP04
- WP07
- WP08
- WP09
- WP10
- WP12
requirement_refs:
- C-001
- FR-007
- NFR-002
- NFR-003
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T057
- T058
- T059
- T060
- T061
- T062
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/review/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/cycle.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/review/artifacts.py
- src/specify_cli/review/arbiter.py
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- src/specify_cli/post_merge/review_artifact_consistency.py
- tests/integration/test_two_partition_preview.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP13 - Consumer unification

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

## Objective

FR-007's promise is that every read, write, gate and display path resolves **one**
identical location for a work package's verdict, for every accepted filename
separator. Today it does not, and the reason is not where three prior planning
passes located it. The commit-router/kind plumbing (WP04), the coord-partition
authority (WP07), the reconciliation of stranded records (WP08), the numbering fix
(WP09), the atomicity work (WP10) and the arbiter retirement (WP12) all land
*before* this WP because every one of them changes a caller this WP must unify
without re-breaking.

The divergence this WP actually closes is **upstream of the directory resolver**,
in slug derivation. `_resolve_wp_slug` (`src/specify_cli/cli/commands/agent/tasks_materialization.py:105`)
resolves a WP slug by scanning `tasks/` for a file whose stem either starts with
`"{task_id}-"` or equals `task_id` exactly, and falls back silently to the bare
task id otherwise:

```python
for p in tasks_dir.iterdir():
    if p.stem.startswith(f"{task_id}-") or p.stem == task_id:
        return str(p.stem)
return task_id
```

Reproduced by direct call: `WP01_durable_writer.md` (underscore separator) and
`WP01.v2.md` (dot separator) both degrade to the bare slug `WP01` — the accepted
separators named in US3 Acceptance Scenario 1 (`-`, `_`, `.`, or none) are not
symmetric in this function, only `-` and none are honoured. **Unifying the
directory-join layer alone (`_review_cycle_wp_dir` in `review/cycle.py:35`) fixes
nothing**, because every caller that reaches it already went through a slug that
may have silently degraded before the join ever ran. This WP's real work is
upstream of where WP06/IC-06's original framing pointed.

**This WP owns C-001's discharge** — and C-001 must be *rewritten*, not merely
cited, before this WP can claim it. See T060.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 3
  (FR-023, FR-007, FR-008), C-001, SC-006.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-06 (split
  IC-06a/IC-06b; this WP is IC-06b's scope), the "Constraint notes" section on
  C-001, and ADR 2026-08-03-1's "Required machinery" and "Migration" sections.
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/tasks.md` — this WP's
  dependency table (the ownership/slicing gate section) explains *why* six
  packages must land first: `review/cycle.py`, `review/artifacts.py`,
  `review/arbiter.py` and `post_merge/review_artifact_consistency.py` are each
  claimed by more than one WP and this one is always last in that chain.
- `docs/adr/3.x/2026-08-03-1-review-cycle-artifacts-are-coord-partition.md` — the
  partition this WP's unified resolver must respect: COORD under a coordination
  topology, PRIMARY otherwise, with `CoordinationBranchDeleted` absorbed to
  PRIMARY for the 45 pre-ADR missions WP08 reconciles.

**Binding constraint — sequencing inside this WP.** T059 (narrowing the merge-gate
fan-out) must not run, or even be attempted, before WP08's reconciliation has
actually executed against this repository's stranded records. `_artifact_dirs_for_wp`
(`src/specify_cli/post_merge/review_artifact_consistency.py:112`) returns a **list**
— the exact `tasks/<wp_id>` directory plus every sibling matching `tasks/<wp_id>-*`
— and `find_rejected_review_artifact_conflicts` iterates the whole list. That
fan-out is a **deliberate tolerance** for exactly the divergence this WP closes.
Narrowing it to "resolve one directory" before every stranded record has been
reconciled or reported does not make the divergence disappear — it makes the gate
blind to it. A record sitting at a sibling path the narrowed resolver no longer
visits stops being seen as `rejected` at all, which is a fail-open regression on
a safety gate. Confirm WP08's reconciliation command has run (or that this
repository has zero stranded records to reconcile, verified via WP08's own
detector) before merging T059.

## Subtask T057 — Unify slug derivation

- **Purpose**: Fix the actual divergence — not the directory join, the slug that
  feeds it. This is the root-cause subtask; T058's "twelve sites" all become
  correct once they consume this function's output.
- **Steps**:
  1. In `src/specify_cli/cli/commands/agent/tasks_materialization.py`, replace
     `_resolve_wp_slug`'s ad-hoc `startswith`/`==` matching with a single regex
     anchored on the accepted separator set from spec.md US3 AC1: `-`, `_`, `.`,
     or no separator at all (i.e. the file stem equals the task id, or starts
     with `task_id` followed immediately by one of `-_.`).
  2. When more than one candidate file matches unambiguously to *different*
     resolved slugs (e.g. both `WP01-foo.md` and `WP01_bar.md` present), refuse
     with a diagnostic rather than silently picking the first `iterdir()` result
     — this is US3 AC3 ("a filename the system cannot resolve unambiguously ...
     refused ... rather than silently degraded to the bare id").
  3. Keep the existing behavior for the exact-match and hyphen-prefix cases
     byte-for-byte — every current caller that only ever wrote `WP01-slug.md`
     files must see identical output.
  4. Export the corrected matcher as the single place every other resolver in
     this mission (WP13's own T058, and any lingering ad-hoc glob in
     `review/cycle.py` or `review/arbiter.py`) is required to call, rather than
     re-implementing the separator rule locally.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_materialization.py`
- **Validation checklist**:
  - [ ] `WP01_durable_writer.md` resolves to `WP01_durable_writer`, not the bare
        `WP01`.
  - [ ] `WP01.v2.md` resolves to `WP01.v2`, not the bare `WP01`.
  - [ ] `WP01-durable-writer.md` (existing hyphen case) is unchanged.
  - [ ] Two files matching the same task id to different slugs raise a
        diagnostic error, not a silent first-match.
  - [ ] Existing callers of `_resolve_wp_slug` (`tasks_move_task.py:1284`,
        `:1726`, `:1766`; `tasks_materialization.py:147`) compile and pass
        unchanged for their existing fixtures.
- **Edge Cases**: a `tasks/` directory that does not exist yet (first-ever WP);
  a task id that is itself a prefix of another task id (`WP1` vs `WP10`) — the
  separator anchor must not let `WP1` match `WP10-foo.md`.

## Subtask T058 — Route all twelve read/write sites through one owner function

- **Purpose**: FR-007's "one resolution" only holds if every consumer calls the
  same function, not eleven that happen to agree today and one that doesn't.
- **Steps**:
  1. Using WP01's census (`contracts/verdict-seam-census.md`'s "Location
     resolvers" table, populated by WP01) as the enumeration, list every site
     that currently derives a review-cycle directory: `review/cycle.py`'s
     `_review_cycle_wp_dir`, `review/artifacts.py`'s cycle-numbering glob,
     `review/arbiter.py`'s `_find_review_cycle_artifact` (WP12 fixes its
     bare-`wp_id` bug — confirm that fix is present before building on it),
     `post_merge/review_artifact_consistency.py`'s `_resolve_review_cycle_read_dir`
     / `_artifact_dirs_for_wp`, and `tasks_materialization.py`'s
     `_persist_review_feedback`.
  2. Pick the **single owner function** for directory resolution — the natural
     candidate is `_review_cycle_wp_dir` in `review/cycle.py`, since it already
     resolves through `placement_seam(...)` and the `MissionArtifactKind`
     introduced by WP04, rather than building a new one. State explicitly in
     the PR description which function is the owner and why (C-004: consolidate
     onto the existing canonical surface, don't invent a competing one).
  3. Re-point every site from step 1 to call the owner function with the
     **corrected** slug from T057, rather than deriving a directory by its own
     `Path(...) / "tasks" / wp_slug` construction.
  4. For the nine sites plan.md's IC-06b names as hard-coding a PRIMARY
     assumption: confirm each now resolves through the owner function, which
     itself resolves COORD-under-coordination-topology / PRIMARY-otherwise per
     ADR 2026-08-03-1, with `CoordinationBranchDeleted` absorption from WP08.
  5. Do not re-implement the exception-absorption logic locally at any of the
     nine call sites — that logic lives in the owner function (or a helper it
     calls), once, per the ADR's "in one owner function ... not per consumer"
     ruling.
- **Files**: `src/specify_cli/review/cycle.py`, `src/specify_cli/review/artifacts.py`,
  `src/specify_cli/review/arbiter.py`, `src/specify_cli/post_merge/review_artifact_consistency.py`,
  `src/specify_cli/cli/commands/agent/tasks_materialization.py`
- **Validation checklist**:
  - [ ] Every site named in WP01's populated census resolvers table calls the
        chosen owner function (grep confirms no independent `Path(...) / "tasks"`
        construction remains at any of the twelve sites).
  - [ ] A coord-topology mission's review-cycle write and the merge gate's read
        of the same WP agree on directory (integration-level assertion, not
        unit-level).
  - [ ] A pre-ADR mission (coord branch deleted) resolves to PRIMARY via the
        owner function's absorption path, not via an independent try/except at
        the call site.
- **Edge Cases**: `SINGLE_BRANCH`/`LANES` missions (no coord partition at all —
  owner function must return PRIMARY directly, no absorption logic invoked);
  a mission whose `meta.json` predates the coord-branch key entirely.

## Subtask T059 — Narrow the merge-gate fan-out, after WP08 has reconciled

- **Purpose**: Collapse `_artifact_dirs_for_wp`'s multi-candidate fan-out to the
  single resolved directory T058 establishes — but only once nothing is
  stranded outside it.
- **Steps**:
  1. **Precondition, verify before touching code**: run WP08's reconciliation
     detector (or its `doctor` subcommand) against this repository and confirm
     zero unreconciled stranded records remain at any of the retired resolver
     paths WP01's census names. Record the command and its output in this WP's
     Activity Log before proceeding — this is not optional documentation, it is
     the evidence the narrowing is safe.
  2. In `src/specify_cli/post_merge/review_artifact_consistency.py`, change
     `_artifact_dirs_for_wp` (currently returning `list[Path]` — the exact
     `tasks/<wp_id>` dir plus every `tasks/<wp_id>-*` sibling) to resolve and
     return the single directory the T058 owner function produces.
  3. Update `find_rejected_review_artifact_conflicts`'s loop (currently
     `for artifact_dir in _artifact_dirs_for_wp(review_cycle_dir, wp_id):`) to
     consume the single directory rather than iterate a list. Keep the
     function's external contract (its `list[ReviewArtifactFinding]` return
     type) unchanged — only the internal resolution narrows.
  4. If any test in `tests/post_merge/test_review_artifact_consistency.py` or
     `tests/integration/test_two_partition_preview.py` relied on the fan-out
     tolerance (i.e. asserted a finding was produced by scanning a *sibling*
     directory the strict resolver would not visit), that test is asserting the
     divergence this WP retires — update it to assert against the unified path
     instead, and record the update in the census fragment (T060 note).
- **Files**: `src/specify_cli/post_merge/review_artifact_consistency.py`
- **Validation checklist**:
  - [ ] WP08's reconciliation ran against this repo and reported zero
        outstanding stranded records, evidenced in the Activity Log.
  - [ ] `_artifact_dirs_for_wp` (or its narrowed successor) returns exactly one
        directory, not a list, and every call site is updated accordingly.
  - [ ] No test that previously depended on the fan-out silently starts passing
        vacuously (i.e. because the sibling directory it seeded is now simply
        never checked) — inspect each affected test's assertions, don't just
        watch for green.
- **Edge Cases**: a repository where WP08's reconciliation is un-runnable (e.g.
  `doctor` subcommand missing) — treat as a hard blocker on this subtask, not a
  reason to narrow anyway "because tests still pass."

## Subtask T060 — Discharge C-001's premise against the unified resolver

- **Purpose**: C-001 as written in spec.md is not dischargeable — plan.md's
  "Constraint notes" section explains why, and this subtask is where the
  rewrite and the discharge both happen.
- **Steps**:
  1. Read spec.md's C-001 verbatim: *"the fail-closed rejected-verdict refusal
     is not reinstated ... once FR-007 has landed and the merge-time backstop is
     shown to resolve the same location the writer writes to."* Under WP07 the
     gate no longer resolves a **location** for the verdict at all — it resolves
     the reduced event snapshot for *which* verdict is current — so the original
     predicate has no referent. It would be satisfied by construction (there is
     nothing left to disagree), which is **voiding** the constraint, not
     discharging it.
  2. Rewrite C-001 in this WP's PR description (and, if `spec.md` is touched by
     another in-flight WP, coordinate rather than silently diverge) to the
     honest proposition plan.md states: *"for every accepted filename, the
     merge gate reaches a verdict for the work package that the writer wrote."*
     This is testable under both the pre-unification fan-out and the
     post-T059 unified resolver, and remains meaningful after WP07's event
     authority — it is a claim about which artifact's content backs the
     event's `feedback_path` pointer, not about directory equality per se.
  3. C-001's own site is `src/specify_cli/cli/commands/agent/tasks_transition_core.py`,
     `_guard_rejected_verdict` (currently around lines 374-410) — an earlier
     plan revision omitted this site from its "affected surfaces" list
     entirely. Confirm this WP does not need to *modify* that function (its
     refusal arms are `_guard_rejected_verdict`'s own concern, already
     rewritten by the predecessor mission per its own docstring's "EXCEPTION"
     note at line 21) — this subtask only needs to **verify** the guard's
     remaining refusal arms (unparseable verdict; `--skip-review-artifact-check`
     without `--note`) are still correct against the rewritten C-001, and record
     that verification.
  4. Write the test that discharges the rewritten C-001: for a WP with a
     known writer-produced artifact, assert the merge gate's finding (or
     absence of one) is consistent with that artifact's actual verdict, under
     both a `SINGLE_BRANCH` and a coord-topology fixture, and for at least two
     accepted filename separators.
- **Files**: `src/specify_cli/post_merge/review_artifact_consistency.py`,
  `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` (C-001's text,
  coordinate with any concurrently-active WP before editing), new/updated test
  under `tests/integration/test_two_partition_preview.py` or
  `tests/post_merge/test_review_artifact_consistency.py`.
- **Validation checklist**:
  - [ ] C-001's rewritten text appears verbatim in the PR description and (if
        editable without collision) in `spec.md`.
  - [ ] A test exists asserting "the merge gate reaches a verdict for the WP
        the writer wrote", not "the gate resolves the same directory as the
        writer" — the latter is the voided predicate.
  - [ ] `_guard_rejected_verdict`'s two remaining refusal arms are unchanged and
        still pass their existing pinned tests.
- **Edge Cases**: a WP with no artifact at all yet (first-ever cycle) — the
  rewritten C-001's "reaches a verdict for the WP that the writer wrote" must
  degrade to "no verdict, no finding", not a crash.

## Subtask T061 — Correct the "PRIMARY-partition for every topology" docstring

- **Purpose**: `src/specify_cli/post_merge/review_artifact_consistency.py`
  asserts in its own module or function docstring that review-cycle artifacts
  are `WORK_PACKAGE_TASK`, "PRIMARY-partition for **every** topology" — the
  exact claim ADR 2026-08-03-1 falsifies. A docstring making a false claim about
  partition placement is itself a defect this mission exists to close, not
  incidental cleanup.
- **Steps**:
  1. Locate every docstring or comment in this module (and in `review/cycle.py`'s
     `_review_cycle_wp_dir`, which carries a similar "PRIMARY-home" claim in its
     own docstring) asserting PRIMARY-for-every-topology placement.
  2. Rewrite each to state the ADR-governed rule: COORD under a coordination
     topology, PRIMARY otherwise, resolved by the `REVIEW_CYCLE` kind (WP04)
     through the T058 owner function — not a hard-coded partition.
  3. Cross-check `_resolve_review_cycle_read_dir`'s own docstring (`"Resolve the
     WORK_PACKAGE_TASK home (PRIMARY mission dir for every topology)"`), which
     makes the identical false claim at the read seam — correct it in the same
     pass, and confirm the function itself now resolves through `REVIEW_CYCLE`
     (WP04's kind) rather than continuing to borrow `WORK_PACKAGE_TASK`.
- **Files**: `src/specify_cli/post_merge/review_artifact_consistency.py`,
  `src/specify_cli/review/cycle.py`
- **Validation checklist**:
  - [ ] No docstring or comment in either file claims PRIMARY-for-every-topology
        placement for review-cycle artifacts.
  - [ ] `_resolve_review_cycle_read_dir` (or its successor) resolves via
        `MissionArtifactKind.REVIEW_CYCLE`, not `WORK_PACKAGE_TASK`.
- **Edge Cases**: none beyond the docstring/behavior consistency itself — this
  subtask is truthfulness, not new behavior; do not let it silently expand into
  re-deriving directory logic that T058/T059 already own.

## Subtask T062 — Re-pin the #2834 coord-husk test with the both-present case

- **Purpose**: `test_review_artifact_gate_ignores_stray_artifact_on_coord_husk`
  (`tests/integration/test_two_partition_preview.py`, harvested from PR #2834)
  encodes the **pre-ADR** partition rule: it seeds a stale rejected artifact on
  the coord husk and a real approved artifact on PRIMARY, and asserts PRIMARY
  wins unconditionally. ADR 2026-08-03-1's conflict rule inverts this: when both
  surfaces hold a record, **COORD wins under a coordination topology**. The
  existing test's polarity is now wrong, not merely stale.
- **Steps**:
  1. Read the existing test in full — it is the "harvested from @rayjohnson's
     PR #2834" test in `tests/integration/test_two_partition_preview.py`. Do
     not delete it; re-pin it citing ADR 2026-08-03-1 in its docstring, and
     invert its assertion to match the new conflict rule: a stale/incorrect
     artifact on PRIMARY must not shadow a real one on COORD, under a
     coordination topology.
  2. **Add the both-present case the migration fallback does not cover**: seed
     a genuine, non-stale record on **both** surfaces for the same WP — e.g.
     `approved` on COORD and `rejected` on PRIMARY — and assert COORD wins. This
     is distinct from the "stray husk" scenario the existing test covers (one
     side is a stale leftover); this case is two surfaces each holding a record
     someone could plausibly have written, which is exactly the scenario the
     `CoordinationBranchDeleted`-absorption migration path (WP08/WP13's T058)
     does **not** exercise, since absorption only fires when COORD is entirely
     absent, not when COORD and PRIMARY both have content.
  3. Confirm the existing "stray husk" scenario (one side genuinely stale) still
     resolves correctly under the new rule — the ADR's conflict rule is about
     which surface is *authoritative*, not about ignoring staleness; a stale
     COORD record still wins over a fresher PRIMARY one under a coordination
     topology, by design (COORD is the fact-of-record, not "whichever is
     newest").
  4. Update the test's docstring to remove the false "the fix ... resolves to
     PRIMARY" claim it currently carries, replacing it with the ADR-governed
     rule.
- **Files**: `tests/integration/test_two_partition_preview.py`
- **Validation checklist**:
  - [ ] The re-pinned test's docstring cites ADR 2026-08-03-1, not the retired
        PRIMARY-wins rule.
  - [ ] A new both-present case exists and is distinct from the stray-husk case
        (different fixture: two genuine, non-stale records, not one genuine and
        one stale).
  - [ ] Both tests pass against the T058/T059-unified resolver.
- **Edge Cases**: a `SINGLE_BRANCH`/`LANES` mission has no COORD surface at all
  — confirm the both-present scenario is scoped to coord-topology fixtures only,
  and does not accidentally get parametrized over topologies where "both
  surfaces" is not a coherent state.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP04/WP07/WP08/WP09/WP10/WP12 must
all be merged into whatever base this WP branches from), but completed changes
must merge back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the
human explicitly redirects the landing branch.

## Definition of Done

- [ ] T057: slug derivation is separator-symmetric across `-`, `_`, `.`, and no
      separator; ambiguous matches refuse rather than silently degrade.
- [ ] T058: every site in WP01's populated resolver census calls one owner
      function; no independent directory construction remains.
- [ ] T059: the merge-gate fan-out is narrowed to a single directory, and only
      after WP08's reconciliation is verified complete against this repo (with
      that verification recorded in the Activity Log).
- [ ] T060: C-001 is rewritten to the honest, testable proposition and a test
      discharges it against the unified resolver, under both `SINGLE_BRANCH` and
      coord-topology fixtures.
- [ ] T061: no docstring in the touched modules claims PRIMARY-for-every-topology
      placement for review-cycle artifacts.
- [ ] T062: the #2834 test is re-pinned with the inverted conflict rule and a
      new both-present case; the original stray-husk scenario still passes.
- [ ] `ruff` and `mypy --strict` clean on every touched file, zero new
      suppressions (NFR-003).
- [ ] Full regression: `tests/review/ tests/status/ tests/post_merge/
      tests/integration/test_two_partition_preview.py
      tests/specify_cli/cli/commands/agent/` — no new failures beyond
      `research/baseline-8466727eb.md`'s two rows (NFR-001).
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Sequencing risk on T059**: narrowing the fan-out before WP08's
  reconciliation has actually run is the single highest-severity way this WP
  can regress safety. Mitigate by treating the reconciliation-verified
  precondition as a hard gate, not a formality — do not proceed on the
  assumption "WP08 landed in the plan, so it must have run here."
- **C-001 rewrite risk**: if another WP is concurrently editing `spec.md`,
  a naive overwrite can silently drop that WP's edits. Mitigate by rewriting
  C-001's text in this WP's PR description first and coordinating the `spec.md`
  edit as a small, isolated diff reviewed on its own.
- **Docstring drift risk (T061)**: "PRIMARY for every topology" language may
  recur in places this WP's grep did not catch (e.g. new code WP04-WP12 added
  after this prompt was written). Re-grep for the phrase across
  `src/specify_cli/review/` and `src/specify_cli/post_merge/` immediately before
  marking this WP done, not only at the start.
- **Test-polarity risk (T062)**: inverting a landed regression test's assertion
  is exactly the kind of change a reviewer should distrust by default. Mitigate
  by keeping the original stray-husk assertion passing (proving the inversion
  is additive, not a weakening) and citing the ADR explicitly in the diff.

## Reviewer Guidance

- Confirm T059 was not implemented before independently verifying WP08's
  reconciliation ran — ask for the Activity Log entry and its command output,
  don't accept "WP08 is done" as sufficient.
- Confirm T057's fix is in slug derivation (`tasks_materialization.py`), not a
  second patch bolted onto the directory-join layer (`review/cycle.py`) that
  merely papers over symptoms downstream of the real defect.
- Confirm C-001's rewritten text is present in this WP's PR description
  verbatim, and that the new test asserts "the gate reaches a verdict for the
  WP the writer wrote" — not directory equality, which is the voided form.
- Confirm the #2834 test's both-present case is genuinely distinct from its
  existing stray-husk case — a common shortcut is to add a second assertion to
  the same fixture rather than a fixture that actually seeds two non-stale
  records.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

- 2026-08-04T00:00:00Z – claude – lane=in_progress – T059 precondition evidence:
  ran `spec-kitty doctor review-cycle-reconcile --json` against this repository
  before narrowing `_artifact_dirs_for_wp`. Result: 121 missions scanned, 76
  clean, 45 carry findings; 194 total findings, ALL classified
  `deleted_coord_branch_absorption` (zero `live_coord_pre_adr_primary_record`
  findings) — i.e. every stranded record is the steady-state,
  always-PRIMARY-absorbing class the narrowed resolver's own absorption
  fallback already lands on. Confirmed safe to narrow.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – WP13 safety finding
  `review/cycle.py::_review_cycle_wp_dir` (write side) and
  `post_merge/review_artifact_consistency.py::_artifact_dirs_for_wp` (merge
  gate). Reverted both after concrete evidence of regression: (1) flipping the
  writer broke a currently-green, unowned test,
  `tests/coordination/test_analysis_report_rehome.py::
  test_review_cycle_authored_lands_on_coord_ref_and_is_absent_on_primary`; (2)
  flipping ONLY the gate (leaving the writer unflipped) was empirically proven
  to desynchronize writer and gate under a materialized coord worktree (a
  throwaway probe against `coord_topology_mission` driving the REAL
  `create_rejected_review_cycle` writer then the gate returned 0 findings for
  a genuine rejection the writer had just recorded) — reproducing C-001's own
  fail-open defect class as a NEW regression. Both `_review_cycle_wp_dir` and
  `_artifact_dirs_for_wp` stay `WORK_PACKAGE_TASK`-anchored (unflipped);
  `_review_cycle_wp_dir` gained an optional `kind` parameter (default
  unchanged) so the owner-function consolidation (T058) still holds without
  shipping the unsafe flip. T062's "COORD wins" conflict rule is NOT
  implemented as a result — see final report.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – Operator-directed scope
  addition (DM-01KZ75GBNXC73Q38M43GBH38W7): `tasks_verdict_persistence.py`
  added to `owned_files`. Fixed `revert_committed_verdict_write`'s stale
  `kind=WORK_PACKAGE_TASK` → `kind=REVIEW_CYCLE` (this call bypasses
  `commit_artifact`'s path-based override by calling `safe_commit` directly,
  so the kind argument here is NOT self-correcting — a live bug, confirmed).
  Wrote the coord-topology regression test as directed
  (`test_revert_committed_verdict_write_targets_coord_ref_under_coord_topology`
  in `tests/integration/test_two_partition_preview.py`) and captured genuine
  red against the unfixed source (`RuntimeError: safe_commit: failed to stage
  requested files...`). The kind fix ALONE did not turn the test green: a
  SECOND, previously-undiagnosed gap surfaced
  (`SafeCommitHeadMismatch: ... HEAD is 'main', expected
  'kitty/mission-...'`) — `safe_commit`'s `worktree_root` was hardcoded to
  `st.main_repo_root` regardless of target, which only works when the target
  ref IS the primary checkout's HEAD. Added a bounded companion helper,
  `_resolve_revert_commit_worktree`, that resolves the coordination worktree
  (via the public `CoordinationWorkspace.resolve` + `resolve_mid8` +
  `load_meta`) and deletes/commits the coord-staged copy from there when the
  target ref is not primary — mirroring `coordination/commit_router.py`'s own
  `_materialise_coord_worktree`/`_stage_artifacts_in_coord_worktree` staging
  step (not touched; only mirrored via public APIs, entirely within this
  file). Test now genuinely passes; `tests/specify_cli/cli/commands/agent/
  test_move_task_durability.py`'s existing single-branch-topology tests for
  this same function (11 tests) still pass unchanged.
- 2026-08-04T00:00:00Z – claude – lane=in_progress – Operator ruling: T062
  voided (`DM-01KZ77CBY9G8SE9PPJEKCV01KN`) — the two-sided-disagreement premise
  never arises given the read-side stays `WORK_PACKAGE_TASK`-anchored, so
  nothing further required there. One routing fix directed
  (`DM-01KZ77DS4F1PZ92MK6V8ATCJWW`): `resolve_review_verdict_facts`
  (`tasks_verdict_persistence.py`) routed through the T058 owner function.
  Traced (via a dedicated research pass over `task_utils/support.py::
  locate_work_package`): `wp_path` reaching this function is ALWAYS a real,
  glob-found file (never a bare-id guess) already anchored on the same
  separator-anchored regex T057 introduced — so this site was
  **unconsolidated, not actively buggy**. Kept the public signature
  unchanged (`wp_path: Path`) to avoid a companion edit to
  `tasks_move_task.py`'s one call site and to
  `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py`'s three
  existing unit tests (both outside `owned_files`) — all three still pass
  unmodified. New helper `_resolve_verdict_wp_dir` routes through
  `_review_cycle_wp_dir` directly (not `_resolve_wp_slug` too — the slug is
  already known-correct from the real file, so re-deriving a bare task id
  from it just to re-scan `tasks/` again would be a redundant, strictly
  riskier round-trip, not genuine consolidation; disclosed as a deliberate
  deviation from the literal instruction). New regression test added
  (`test_resolve_review_verdict_facts_routes_through_owner_function`,
  underscore-separated WP file, proves the routed answer lands on the
  correctly-slugged directory a bare-id join would miss). Kind stays
  `WORK_PACKAGE_TASK` throughout, per the T062 void.
  `tests/integration/test_two_partition_preview.py`: 11 passed.
  `tests/specify_cli/cli/commands/agent/`: 1575 passed, 2 xfailed, 1 failed
  (the pre-existing known-red `test_command_exposes_exact_flag_surface
  [acceptance-verdict]`, #3160, unrelated). `tests/architectural/
  test_verdict_seam_census.py` + `test_untrusted_path_containment.py`: 38
  passed — no censused shape moved, no new row needed.
---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP13 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

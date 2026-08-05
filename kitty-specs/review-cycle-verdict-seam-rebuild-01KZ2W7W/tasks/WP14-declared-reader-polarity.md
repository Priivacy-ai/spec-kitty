---
work_package_id: WP14
title: Declared reader polarity
dependencies:
- WP01
- WP13
requirement_refs:
- FR-012
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T063
- T064
- T065
- T066
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/agent_utils/
create_intent:
- tests/review/test_reader_polarity_merge_gate_regression.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/agent_utils/status.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/review/arbiter.py
- tests/review/test_reader_polarity_merge_gate_regression.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP14 - Declared reader polarity

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

User Story 4 (spec.md) asserts that every component reading a verdict record must
reach the same conclusion about a damaged one, and that conclusion must be
fail-closed wherever it is safety-relevant. FR-012 requires every reader in
WP01's census to resolve to one of exactly two **declared** polarities — `refuse`
or `skip` — with no reader crashing uncaught, and no safety-gate reader failing
open.

**Five** fail-open or crashing readers were measured against a damaged (non-UTF-8)
verdict record, not the four an earlier spec revision counted:

| Reader | Location | Current behaviour |
|---|---|---|
| Kanban verdict reader | `agent_utils/status.py`, `_get_wp_review_verdict` | `except Exception: return None` — **fail-open** |
| Review-cycle provenance scan | `review/cycle.py`'s `_guard_feedback_source_provenance` | skips and continues (fold `97a9ecfae`) — **already declared `skip`, correct** |
| Merge gate | `post_merge/review_artifact_consistency.py` | structured finding — **already fail-closed, correct** |
| Arbiter override reader | `review/arbiter.py` | **uncaught crash** |
| Move-task review-readiness reader | `cli/commands/agent/tasks_parsing_validation.py`, `_get_latest_review_cycle_verdict` | `except Exception: return None, artifact` with an explicit `# fail-open` comment — feeds the review-readiness/kanban-adjacent facts `move-task` uses | **fail-open, uncounted by the original spec's four-reader table** |

This WP's job is to make the census (WP01's fixture) name a polarity for **every**
one of these five, fix the two genuine defects (the kanban reader and the arbiter
crash), and leave the two already-correct readers alone — with the merge gate's
correctness recorded as an explicit, testable *why*, not silently re-verified by
touching working code.

## Context & Constraints

Read in full before starting:

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — User Story 4
  (FR-012, SC-012), and the "Edge Cases" entry "A prior record is unreadable."
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-08's Risks
  paragraph, which is where the fifth reader and the merge-gate correctness
  rationale were established.
- `tests/architectural/census/verdict_seam_IC01.yaml` — WP01's own fragment,
  populated with the "Verdict readers and their declared polarity" table; this
  WP's readers must appear there with the polarities this WP assigns. (The
  fold into `tests/architectural/verdict_seam_census.yaml` is WP16's job and
  has not happened yet at this WP's point in the dependency graph — read
  WP01's fragment directly, not the not-yet-folded target.
  `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/contracts/verdict-seam-census.md`
  is a retired pointer file, not the census itself.)
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/quickstart.md` — the
  "Reader polarity" section's exact verification commands and the *why* for the
  merge gate's incidental fail-closed behaviour.

**Binding constraints**:

- **Do not "fix" the merge gate.** It is already fail-closed. T066 is
  documentation of *why* it currently works, plus a regression test proving the
  *why* — not a code change to `post_merge/review_artifact_consistency.py`,
  and not an edit to that module's existing test file
  (`tests/post_merge/test_review_artifact_consistency.py`) either. **Both are
  owned by WP07/WP13, not this WP.** T066's regression test lives in a new
  file this WP owns instead (`tests/review/test_reader_polarity_merge_gate_regression.py`);
  the rationale comment on the gate itself is filed as a cross-WP finding
  against WP13, not authored here.
  The reason it works today: `UnicodeDecodeError` is a subclass of `ValueError`,
  and `ReviewCycleArtifact.from_file`'s parsing path funnels `OSError` into a
  `ValueError` as well — so the gate's existing bare `except ValueError` catches
  both. A future reader-side exception type outside that hierarchy (e.g. a raw
  `OSError` that stops being wrapped, or a new parser raising something else)
  would silently re-open the gate to fail-open behaviour with **no code change
  to the gate itself** — which is exactly why this needs to be recorded as a
  named risk with a regression test, not left as an accident of inheritance.
- **Do not touch `pre_review_gate.py`'s deliberate fail-open.** It belongs to a
  different mission and is explicitly out of the NFR-007 census's scope (WP01's
  T004 excludes it by concept).
- **Do not touch `verdict_aggregation.py`.** It is a different sense of
  "verdict" entirely (aggregating CI/test verdicts, not review verdicts) — WP01's
  census scopes by concept, not by symbol name, and this module is excluded.
- **The denominator is WP01's census, without exception.** Do not declare a
  polarity for a reader this WP happens to notice that is absent from the
  census — file it as a census gap against WP01 instead of silently handling it
  here, so the check (not this WP's memory) stays the single source of truth.

## Subtask T063 — Declare a polarity for every reader in the census

- **Purpose**: Before fixing anything, establish the complete, checked
  denominator — the two polarities (`refuse`, `skip`) and which reader gets
  which, including the two that need no code change.
- **Steps**:
  1. Read WP01's populated fragment,
     `tests/architectural/census/verdict_seam_IC01.yaml`, for its "Verdict
     readers and their declared polarity" rows (the fold into
     `tests/architectural/verdict_seam_census.yaml` is WP16's job and has not
     happened yet at this point in the dependency graph). Confirm it lists all
     five readers named in this WP's Objective table (kanban, provenance scan,
     merge gate, arbiter, move-task review-readiness). **If any is missing,
     that is a hard blocker on this subtask, not a scope to narrow around.**
     File the gap against WP01/the architectural check and do not proceed to
     assign polarities or implement T064/T065 until the fragment is corrected
     to include all five rows — an empty or incomplete census fixture would
     make FR-012/SC-012 vacuously true over fewer readers than actually exist,
     which is exactly the failure this mission's own census design (WP01's
     `retire`-with-no-`retiring_fr` rule) exists to prevent recurring in a
     different shape. Do not silently treat "its existing entries" as this
     WP's scope.
  2. For each of the five, assign (or confirm WP01 already assigned) exactly one
     polarity:
     - Kanban reader → `refuse` after this WP's fix (currently `skip`-shaped via
       silent `None`, which is the defect T064 closes).
     - Provenance scan → `skip` (correct today, no change).
     - Merge gate → `refuse` (correct today, no change; T066 documents why).
     - Arbiter override reader → `refuse` after this WP's fix (currently
       crashes uncaught, which is neither polarity — T065 closes this).
     - Move-task review-readiness reader → declare a polarity and implement it;
       see T064's note on scope (this reader is folded into T064's work since it
       shares the identical fail-open shape and shares a fix pattern with the
       kanban reader, even though it lives in a different module).
  3. Mark which readers are **safety-relevant** in the census (per the check's
     invariant: "a reader marked safety-relevant may not have polarity `skip`").
     The kanban reader, the arbiter reader, and the move-task review-readiness
     reader are all safety-relevant — each one feeds a decision an operator or
     the merge gate trusts. The provenance scan is not safety-relevant (its
     `skip` only affects a best-effort duplicate-detection heuristic, not a
     gate).
- **Files**: none code-owned by this subtask directly — it is verification
  against WP01's fixture, feeding T064/T065's implementation. If a gap is found,
  record it in this WP's Activity Log with the exact missing row, rather than
  editing `tests/architectural/census/verdict_seam_IC01.yaml` (owned by WP01)
  or `tests/architectural/verdict_seam_census.yaml` (the WP16 fold target) —
  neither belongs to this WP.
- **Validation checklist**:
  - [ ] All five readers from the Objective table are accounted for in WP01's
        census (or a documented gap is filed).
  - [ ] Each has exactly one polarity assigned: `refuse` or `skip`, never both,
        never neither.
  - [ ] Safety-relevant readers are flagged, and none is `skip`.
- **Edge Cases**: a reader this WP's own review finds that is genuinely new
  (introduced by a WP that landed after WP01's census was authored) — file
  against WP01, do not silently expand this WP's scope to cover it without that
  census entry existing.

## Subtask T064 — Fix the fail-open kanban reader

- **Purpose**: `_get_wp_review_verdict` in `src/specify_cli/agent_utils/status.py`
  returns `None` on any exception reading a verdict record — feeding the kanban
  status board an indistinguishable "no verdict" for both "genuinely no verdict
  yet" and "verdict exists but is damaged." An operator trusting the kanban board
  cannot tell the difference, which is exactly the fail-open shape US4 exists to
  close. The move-task review-readiness reader (`_get_latest_review_cycle_verdict`
  in `tasks_parsing_validation.py`) has the identical shape and is fixed as part
  of this same subtask, since both readers need the same declared-`refuse`
  treatment and sharing the fix pattern avoids two independently-invented
  error-surfacing conventions.
- **Steps**:
  1. In `src/specify_cli/agent_utils/status.py`, locate `_get_wp_review_verdict`
     (currently `except Exception:  # noqa: BLE001 — review artifact may be
     absent or malformed; fail-open` → `return None`). Distinguish "no artifact
     present" (a legitimate `None` — no verdict has ever been recorded, which is
     not damage) from "artifact present but unreadable" (a damaged record,
     which must surface distinctly).
  2. Change the damaged-record branch to surface a declared, distinguishable
     signal — e.g. raise a typed exception the caller (`show_kanban_status`)
     catches and renders as an explicit "damaged verdict record" board entry,
     rather than the same `None` a genuinely-unverdicted WP produces. Do not
     let the exception propagate uncaught out of `show_kanban_status` itself —
     `refuse` here means "the caller is told, clearly, that this WP's verdict
     is unreadable," not "the whole status command crashes."
  3. In `src/specify_cli/cli/commands/agent/tasks_parsing_validation.py`,
     apply the identical distinction to `_get_latest_review_cycle_verdict`
     (currently `except Exception: return None, artifact  # noqa: BLE001 —
     review-cycle artifact may be malformed; fail-open`). Its return shape
     already carries `artifact` alongside the verdict, so the damaged case can
     be distinguished from the callers' side by checking whether `artifact is
     not None` while `verdict is None` — confirm every caller of this function
     (review-readiness validation, move-task facts) already branches on that
     combination correctly, or update them to.
  4. Confirm the "no artifact at all" case (`cycles` is empty) still returns
     `(None, None)` unchanged in both functions — that is not damage, and must
     not be reclassified as a refusal.
- **Files**: `src/specify_cli/agent_utils/status.py`,
  `src/specify_cli/cli/commands/agent/tasks_parsing_validation.py`
- **Validation checklist**:
  - [ ] A WP with zero review-cycle artifacts still reports "no verdict" from
        both functions, unchanged.
  - [ ] A WP whose latest artifact is present but non-UTF-8 (or otherwise
        unparseable) produces a distinguishable signal from both functions —
        not the same `None`/`(None, None)` as the zero-artifact case.
  - [ ] `show_kanban_status` surfaces the damaged case visibly (e.g. a distinct
        board entry or warning), and does not itself crash uncaught.
  - [ ] Every existing caller of `_get_latest_review_cycle_verdict` still
        compiles and behaves correctly for its current green fixtures.
- **Edge Cases**: a record that is valid UTF-8 but has malformed YAML
  frontmatter (missing closing `---`) — this is also "damaged," not merely
  "unreadable encoding," and must hit the same refusal path as the non-UTF-8
  case, not a third, unhandled branch.

## Subtask T065 — Fix the uncaught arbiter crash

- **Purpose**: `review/arbiter.py`'s override reader has no exception handling
  around reading a potentially-damaged record — "inconsistent with the JSON
  branch three lines above it" (spec.md US4's table), which does handle failure.
  An uncaught crash on a damaged record is neither `refuse` nor `skip` — it is
  the one polarity FR-012 explicitly forbids.
- **Steps**:
  1. Locate the arbiter's override-reading path: `get_arbiter_overrides_for_wp`
     (`review/arbiter.py`) and its helpers `_find_review_cycle_artifact`,
     `_persist_in_artifact`, `_persist_standalone_json`. Identify exactly where
     a damaged record (non-UTF-8, or malformed YAML frontmatter) currently
     propagates an uncaught exception rather than being handled.
  2. Wrap the read in the same declared-`refuse` pattern T064 applies elsewhere:
     catch the narrow set of expected parse failures (not a bare
     `except Exception`, which would also swallow genuine programming errors —
     scope the catch to what `from_file`/YAML parsing actually raises, mirroring
     the merge gate's own `except ValueError` scoping documented in T066), and
     surface a clear, typed refusal to the caller rather than letting the
     process crash.
  3. Confirm the "JSON branch three lines above it" spec.md references (the
     sidecar-reading path) already handles failure correctly, and use its
     existing pattern as the template for this fix rather than inventing a new
     one — the goal is one consistent handling shape across both branches of
     the same function, not two different bespoke ones.
  4. If WP12 has already retired the JSON sidecars and frontmatter block into
     `ReviewOverride` by the time this WP runs (WP12 is not a direct dependency
     of WP14, but WP13 depends on WP12 and WP14 depends on WP13, so it will be
     present), confirm this fix targets the **post-retirement** reader shape —
     do not fix a code path WP12 already deleted.
- **Files**: `src/specify_cli/review/arbiter.py`
- **Validation checklist**:
  - [ ] A non-UTF-8 or malformed-frontmatter override record produces a
        declared refusal from the arbiter reader, not an uncaught exception.
  - [ ] The fix targets the post-WP12 reader shape (verified by reading WP12's
        final diff to `arbiter.py` before starting, not assuming the pre-WP12
        shape described in this mission's planning docs).
  - [ ] The exception scope is narrow (matches the actual parse-failure types),
        not a blanket `except Exception`.
- **Edge Cases**: an override record that parses successfully but fails
  `ReviewOverride`'s own `complete` predicate (an incomplete override) — this is
  a *different* concern (FR-011, owned by WP12) and must not be conflated with
  this subtask's damaged-record handling; confirm the two failure modes remain
  distinguishable to the caller.

## Subtask T066 — Pin the merge gate's incidental fail-closed mechanism, in a file this WP owns

- **Purpose**: The merge gate needs no code change — but the reason it works is
  an accident of Python's exception hierarchy, not a designed invariant, and
  that gap between "works today" and "is guaranteed to keep working" must be
  named so a future change does not silently reopen it. **This WP does not own
  `post_merge/review_artifact_consistency.py` or its existing test file
  (`tests/post_merge/test_review_artifact_consistency.py`) — both belong to
  WP07/WP13.** T066's deliverable is narrowed accordingly: author the pinning
  regression test in a file this WP owns, and file the rationale comment as a
  cross-WP request rather than editing a module this WP does not own.
- **Steps**:
  1. Create `tests/review/test_reader_polarity_merge_gate_regression.py`
     (this WP's own new, owned test file — see `create_intent`). Add a
     regression test that constructs a damaged (non-UTF-8) verdict record
     fixture and calls the merge gate's existing **public** entry point
     (`find_rejected_review_artifact_conflicts` or whichever function
     `post_merge/review_artifact_consistency.py` exposes for this purpose —
     import and call it as a black box; do not reimplement its logic),
     asserting it returns a structured finding rather than propagating an
     exception. This pins the specific inheritance relationship the rationale
     below depends on: that a `UnicodeDecodeError` raised while reading a
     damaged artifact is in fact caught by the gate's existing handler. A
     future refactor that accidentally narrows the catch clause (e.g. to
     `except FileNotFoundError` only) reds this test immediately, without this
     WP ever having edited the gate's own file.
  2. Record, in this WP's Activity Log or PR description, precisely why the
     gate is already fail-closed today: `UnicodeDecodeError` is a subclass of
     `ValueError`, and `ReviewCycleArtifact.from_file`/
     `validate_review_artifact_file`'s parsing path funnels a parser-level
     `OSError` into `ValueError` as well — so the gate's existing bare
     `except ValueError` catches both. State explicitly that this is
     **incidental**, not a designed guarantee, and **file this as a cross-WP
     finding against WP13** (the WP that owns
     `post_merge/review_artifact_consistency.py` after WP07), asking it to add
     a docstring or inline comment at the gate's exception-handling site
     recording this rationale. Do not add that comment yourself in a file this
     WP does not own.
  3. Cross-reference the recorded rationale and the new regression test's
     location from WP01's populated census fragment (the merge gate's row in
     the "Verdict readers and their declared polarity" table) so a reader of
     the census, not just of this WP's code, learns the caveat and where its
     pinning test lives.
- **Files**: `tests/review/test_reader_polarity_merge_gate_regression.py`
- **Validation checklist**:
  - [ ] The regression test lives in a file this WP owns
        (`tests/review/test_reader_polarity_merge_gate_regression.py`), not in
        `tests/post_merge/test_review_artifact_consistency.py`.
  - [ ] The test exercises a `UnicodeDecodeError`-raising fixture directly
        against the gate's public entry point and asserts a structured
        finding results.
  - [ ] The rationale (the exact exception hierarchy relationship, and that it
        is incidental) is recorded in the Activity Log/PR description and
        filed as a cross-WP finding against WP13 — no edit to
        `post_merge/review_artifact_consistency.py` or its existing test file
        appears in this WP's diff.
- **Edge Cases**: none — this subtask is explicitly scoped to not introduce new
  branches in the gate itself; resist the urge to "harden" the gate's catch
  clause here, or to add the rationale comment directly, since both are scope
  creep into a component this WP's Context section explicitly says not to
  touch and does not own.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP01 and WP13 must be merged into
whatever base this WP branches from), but completed changes must merge back into
`pr/review-verdict-write-integrity-01KZ1CGF` unless the human explicitly redirects
the landing branch.

## Definition of Done

- [ ] T063: all five census readers have exactly one declared polarity, and
      safety-relevant readers are flagged and are never `skip`.
- [ ] T064: the kanban reader and the move-task review-readiness reader both
      distinguish "no artifact" from "damaged artifact," and neither crashes.
- [ ] T065: the arbiter override reader no longer crashes uncaught on a damaged
      record, and its fix targets the post-WP12 code shape.
- [ ] T066: the merge gate's incidental fail-closed correctness is pinned by a
      regression test in `tests/review/test_reader_polarity_merge_gate_regression.py`
      (a file this WP owns); the rationale is recorded in the Activity
      Log/PR description and filed as a cross-WP finding against WP13, not
      written into `post_merge/review_artifact_consistency.py` or its
      existing test file.
- [ ] `pre_review_gate.py` and `verdict_aggregation.py` are untouched by this
      WP's diff.
- [ ] `ruff` and `mypy --strict` clean on every touched file, zero new
      suppressions (NFR-003).
- [ ] Full regression: `tests/status/ tests/post_merge/
      tests/specify_cli/cli/commands/agent/ tests/review/` — no new failures
      beyond `research/baseline-8466727eb.md`'s two rows (NFR-001).
- [ ] **NFR-002** — every function this WP touches ends at cyclomatic complexity ≤15: `uv run ruff check --select C901 <touched files>` is clean. Extract helpers rather than leaving a function at 16+.

## Risks & Mitigations

- **Scope-creep risk on the merge gate**: the temptation, having just fixed two
  genuinely fail-open readers, is to "future-proof" the merge gate's exception
  handling too, or to add the rationale comment directly to
  `post_merge/review_artifact_consistency.py` since it is a small change.
  Mitigate by treating T066 as strictly test-plus-cross-WP-finding — any edit
  to a file this WP does not own (the gate module or its existing test file)
  is out of this WP's scope per its own Context constraints.
- **Missing-fifth-reader risk**: if WP01's census was authored before this WP's
  Objective table was finalized, it may still list only four readers. Mitigate
  by treating a missing fifth row as a blocking gap to file against WP01/the
  census check, not a license to skip declaring its polarity here.
- **Exception-scope risk on T065**: a blanket `except Exception` in the arbiter
  fix would silently swallow genuine programming errors alongside the intended
  parse failures. Mitigate by scoping the catch to the same narrow set the
  merge gate documents in T066, and testing that an unrelated exception type
  (e.g. a `TypeError` from a genuine bug) still propagates.

## Reviewer Guidance

- Confirm T064's fix distinguishes "no artifact" from "damaged artifact" in
  both functions it touches — a common shortcut is to simply re-raise on any
  exception, which would turn a previously-benign "no verdict yet" WP into a
  crash.
- Confirm T065's fix targets the arbiter code as it exists **after** WP12's
  retirement of the frontmatter block and JSON sidecars, not the pre-WP12
  shape described in planning docs — read the actual diff on `arbiter.py` at
  this WP's base commit before approving.
- Confirm T066 made no edit at all to `post_merge/review_artifact_consistency.py`
  or `tests/post_merge/test_review_artifact_consistency.py` — the regression
  test lives in `tests/review/test_reader_polarity_merge_gate_regression.py`,
  and the rationale comment is a filed cross-WP finding against WP13, not part
  of this WP's diff.
- Confirm `pre_review_gate.py` and `verdict_aggregation.py` do not appear in
  this WP's diff at all.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

- 2026-08-04T22:08:28Z – claude – lane=doing – T063-T066 implemented. Summary
  below; full detail in the WP14 final report.
  **T063 (census verification)**: all five Objective-table readers ARE
  accounted for in `tests/architectural/census/verdict_seam_IC01.yaml` — but
  the fourth (arbiter) is accounted for by a REASONED ABSENCE, not a present
  row, and this is correct, not a gap. Kanban (`_get_wp_review_verdict`,
  `show_kanban_status`), provenance scan (`_guard_feedback_source_provenance`),
  merge gate (`find_rejected_review_artifact_conflicts`), and move-task
  (`_get_latest_review_cycle_verdict`, `_apply_review_status_flags`) all
  appear as `category: reader, status: active` rows. The arbiter reader has
  ZERO reader rows post-WP12 — verified this is NOT a missing row by running
  `tests/architectural/test_verdict_seam_census.py` standalone (26 passed):
  the AST-derived reader predicate (`_classify_reader` — matches
  `ReviewCycleArtifact.from_file`, `extract_scalar(..., "verdict")`, or
  `read_text`+yaml-load+delimiter/glob) does not match
  `get_arbiter_overrides_for_wp`'s current body (calls `wp_snapshot_state` +
  `ReviewOverride.from_dict`, neither of which reads a review-cycle artifact's
  frontmatter). WP01's own fixture comments this explicitly at the reader-row
  removal site. No census gap filed — the check's own green run is the
  evidence the fixture already matches derived reality. Also confirmed the
  census schema (`category`/`module`/`function`/`status`/`retiring_fr` per
  the fixture's header docstring) carries NO `polarity`/`safety_relevant`
  field — "declaring a polarity" is a documentation/behavioural fact recorded
  here and in code comments, not a fixture column; the WP prompt's Objective
  table implies otherwise and that implication is not literally true of the
  current schema.
  **T064**: both `_get_wp_review_verdict` (agent_utils/status.py) and
  `_get_latest_review_cycle_verdict` (tasks_parsing_validation.py) now
  distinguish "no artifact" (unchanged: `None` / `(None, None)`) from
  "artifact present but damaged" via a shared pattern — a new
  `DamagedVerdictRecordError` raised by the kanban reader (narrow catches:
  `(OSError, UnicodeDecodeError)` around `read_text`, `yaml.YAMLError` around
  `yaml.safe_load`, plus a new `isinstance(fm, dict)` guard that closes a
  latent AttributeError-on-non-mapping-YAML hole the old blanket
  `except Exception` used to paper over) — and the EXISTING
  `(None, artifact)` tuple-shape distinction in the move-task reader (already
  correct; only its `except Exception` was narrowed to
  `(OSError, UnicodeDecodeError)`, since `split_frontmatter`/`extract_scalar`
  are pure string ops that never raise). `show_kanban_status` catches
  `DamagedVerdictRecordError` locally per-WP (added `damaged_verdicts` as a
  NEW dict key, kept the existing `stale_verdicts` list/shape byte-for-byte
  unchanged to avoid touching the exact-equality pin in
  `tests/agent/test_agent_utils_status.py::
  test_show_kanban_status_reports_rejected_artifact_under_wp_slug_dir`,
  outside this WP's owned surface) and prints a distinct red board line; it
  never crashes the whole command. `_apply_review_status_flags` was updated
  to add the missing branch (`artifact is not None and verdict is None` →
  damaged) — the sibling function already returned the right tuple shape but
  its ONLY caller in this file did not previously check it, silently treating
  a damaged artifact the same as "no verdict at all". Folded into the SAME
  `stale_verdicts` return slot (with a `"damaged": True` marker) rather than a
  new return value, since `tasks_status_cmd.py` (unowned) and
  `test_apply_review_status_flags_stale_and_stalled` (unowned) both unpack
  this function's 2-tuple shape and must keep working unmodified.
  **Correction to the WP prompt's own Edge Case**: the prompt says a missing
  closing `---` delimiter must hit the SAME refusal path as non-UTF-8. This
  is only true for the move-task reader (already true, via the tuple shape).
  For the kanban reader it is FALSE as a target — an existing, unowned,
  currently-green test
  (`tests/specify_cli/agent_utils/test_status.py::
  test_get_wp_review_verdict_no_frontmatter_returns_none`) pins
  `_get_wp_review_verdict(...) is None` for exactly a no-frontmatter file,
  and NFR-001 forbids breaking it. `_get_wp_review_verdict` therefore still
  returns `None` (not `DamagedVerdictRecordError`) when no closing
  frontmatter delimiter is found at all — narrowed to raising only on actual
  decode/parse failure of a PRESENT frontmatter block. Recorded here rather
  than silently deviating from the prompt without explanation.
  **T065**: verified against `review/arbiter.py` at this WP's base commit
  (read in full) — WP12 (T051-T053) deleted `_find_review_cycle_artifact`,
  `_persist_in_artifact`, and the old JSON-sidecar/frontmatter parse outright;
  they do not exist in the file. The surviving
  `get_arbiter_overrides_for_wp` reads the event-sourced `review` snapshot
  slot via `wp_snapshot_state` and already wraps
  `ReviewOverride.from_dict(review_raw)` in
  `except (KeyError, TypeError, ValueError): return []` — already narrow,
  already correct, matching the merge gate's own narrowing precedent. No
  uncaught-crash path remains; **no code change made to `arbiter.py`** (zero
  diff — confirmed via `git status`/`git diff --stat`). Pinned with two new
  tests in the owned test file (below): one proving a malformed
  event-sourced slot degrades to `[]` (not a crash), one proving an UNRELATED
  exception type (a monkeypatched `RuntimeError` from `ReviewOverride.
  from_dict`) still propagates uncaught — guarding against a future
  "helpful" widening to a blanket `except Exception`.
  **T066**: new file `tests/review/test_reader_polarity_merge_gate_regression.py`
  (3 tests, all green). The merge-gate test constructs a non-UTF-8
  `review-cycle-1.md` (via `tests.reliability.fixtures`'
  `create_mission_fixture`/`write_work_package`/`append_status_event`, an
  approved-lane WP) and calls `find_rejected_review_artifact_conflicts`
  (public entry point, black-box) — asserts exactly one
  `ReviewArtifactSchemaFinding`, no exception. No edit to
  `post_merge/review_artifact_consistency.py` or
  `tests/post_merge/test_review_artifact_consistency.py` (confirmed:
  `git diff --stat` shows neither file). **Cross-WP finding filed here (for
  the orchestrator to carry to WP13, since WP13 is already approved/closed)**:
  WP13 (owner of `post_merge/review_artifact_consistency.py`) should add a
  docstring/inline comment at line ~415's `except ValueError as exc:` in
  `find_rejected_review_artifact_conflicts` recording that this catch is
  fail-closed against non-UTF-8 content ONLY because `UnicodeDecodeError`
  subclasses `ValueError` and `ReviewCycleArtifact.from_file`'s `read_text`
  call is not itself wrapped against `UnicodeDecodeError` (only `OSError`,
  at `review/artifacts.py:285`) — an inheritance ACCIDENT, not a designed
  guarantee, now pinned by this WP's regression test but not yet documented
  at the gate's own call site.
  **noqa/BLE001 removed**: both bare `except Exception: ... # noqa: BLE001`
  clauses (agent_utils/status.py's `_get_wp_review_verdict`,
  tasks_parsing_validation.py's `_get_latest_review_cycle_verdict`) are gone
  — replaced with narrow, real-type catches. Zero new suppressions added
  anywhere in this WP's diff.
  **Quality gates** (all clean, all touched files): `ruff check` — all
  checks passed; `ruff check --select C901` — all checks passed; `mypy
  --strict` — no issues (the new test file has one pre-existing,
  NOT-mine `no-any-return` error in an UNOWNED transitive import,
  `tests/reliability/fixtures/review_prompt.py:127` — reproduces identically
  against `tests/post_merge/test_review_artifact_consistency.py`, an
  existing, unrelated test that imports the same fixture package, and in
  isolation with `--follow-imports=silent` my new file is clean).
  **Suites run**: `tests/review/ tests/post_merge/ tests/merge/ tests/status/`
  (parallel, `-n auto --dist loadfile`): 1981 passed, 1 skipped (benign
  UserWarning in an unrelated pre-existing test). `tests/specify_cli/cli/
  commands/agent/`: 1 failed (`test_command_exposes_exact_flag_surface
  [acceptance-verdict]`, #3160 — pre-existing, confirmed unrelated to this
  WP's owned files), 1575 passed, 2 xfailed. `tests/architectural/` in full:
  1567 passed, 4 skipped, 2 xfailed, zero failures (includes
  `test_verdict_seam_census.py`, 26/26, and `test_gate_coverage.py` — no
  xdist-contention crash observed this run).
---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP14 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

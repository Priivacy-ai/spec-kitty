# Phase 0 Research: Review Verdict Write Integrity

Resolves the architectural unknowns flagged in `plan.md`'s Implementation Concern Map before Phase 1 design.

## R1 — IC-01: Does the writer's commit-target resolution need hardening for the new `approved` path?

**Decision**: No additional hardening beyond what already exists. The generalized writer inherits the
same, pre-existing commit-target behavior the current rejected-writer already has — this is not a new
risk introduced by FR-001.

**Rationale**: `create_rejected_review_cycle`'s only call site (`_mt_finalize_plan`,
`tasks_move_task.py:1704-1716`) resolves its write location via `_ensure_target_branch_checked_out`
(`tasks_shared.py:169-202`), whose own docstring states it "resolve[s] branch context without
auto-checkout (respects user's current branch)" — a deliberate design choice (`resolve_target_branch(...,
respect_current=True)`), not an oversight. Generalizing the writer to also handle `verdict="approved"`
runs through the identical call chain; there is no new coord/lane ambiguity to close here that the
existing rejected path doesn't already carry.

**Alternatives considered**: Auditing/hardening `_ensure_target_branch_checked_out` itself was
considered but rejected as out of this mission's scope (C-001/C-003) — it is shared, pre-existing
infrastructure used well beyond review-cycle artifacts; changing its behavior is a separate,
much larger-blast-radius mission if ever warranted.

**Correction (post-plan adversarial squad, live reproduction)**: this R1 finding was narrowly correct
about the branch-checkout dimension but incomplete about the commit dimension. A post-plan squad
built a real coord-topology fixture, called the production `create_rejected_review_cycle`, and found
via `git status`/`git log` that **the writer never commits its output at all** — the file appears as
untracked, HEAD is unchanged, and nothing downstream in `move-task`'s pipeline sweeps it into a commit
either (`commit_artifact` exists as a port capability but is called only from
`tasks_mark_status.py`/`tasks_map_requirements.py`, never from `tasks_move_task.py`, despite that
file's own top-of-module docstring claiming otherwise — a stale comment). This is corroborated
independently by `tests/coordination/test_analysis_report_rehome.py`, whose own author already treats
write and commit as two separate steps requiring a separate `commit_for_mission(...)` call.
**Revised decision**: add an explicit commit step to the generalized writer using the existing
`commit_artifact` port capability. This is not new risk invented by FR-001 — it is a pre-existing gap
in the current rejected-writer too — but it directly serves this mission's stated purpose (durable
persistence) and independently closes #2697 ("no single canonical committed rejection record"),
which turns out to be the same gap, not a separate mechanism. Operator-confirmed 2026-08-02.

## R2 — IC-02: What is the exact detection rule for a fabricated/wrapped feedback source?

**Decision**: Two-part guard in the generalized writer, both required:
1. **Path check**: refuse if `feedback_source`, once resolved, is itself a `review-cycle-*.md` file
   inside the target WP's own `sub_artifact_dir` (closes the exact-path case, e.g. `review-cycle-1.md`
   fed back to itself).
2. **Content check**: refuse if `feedback_source`'s body (the text after stripping any leading YAML
   frontmatter block) is byte-identical, or identical after whitespace normalization, to the body of
   any existing `review-cycle-N.md` for that WP — closing the renamed/copied-file evasion case
   (`spec.md` User Story 2, Acceptance Scenario 2) and #990's exact wrapping shape.

**Rationale**: `create_rejected_review_cycle` (`review/cycle.py:276-331`) currently validates only
existence/is-file/non-empty (lines 287-294) before reading `feedback_source.read_text()` verbatim as
the new cycle's body — confirmed as the mechanism for both #2996(b) and #990 by direct test execution
(`tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected` and
`::test_new_cycle_body_never_duplicates_a_prior_cycle_file`, both RED on current `main`). A path-only
check would satisfy the first test but not necessarily the second if the fixture uses a renamed copy
rather than the literal path — the content check is the one that generalizes to #990's framing
("frontmatter/body content that should have stayed isolated").

**Alternatives considered**: A content-hash comparison (SHA-256 of normalized body) instead of a direct
string comparison — equivalent in effect for this scale (a handful of prior cycles per WP), simpler to
reason about via direct comparison given the low candidate count; hashing brings no benefit here and is
not adopted.

## R3 — IC-03: What does "the coord-topology authority split" actually mean in current code, and what's the minimal fix?

**Decision**: Route `agent_utils/status.py`'s stale-verdict scan through the same event-sourced review
authority the merge gate already uses (`resolve_snapshot_review` / `latest_review_artifact_verdict`,
both existing, proven machinery from the FR-009/WP09 override work) instead of inventing a new
coord/primary read-routing scheme. **Before any fix is designed further, #2646 and #2697 must be
re-reproduced against current `main` HEAD** — both issues predate the WP09 override-collapse
(`tasks.py:178`'s comment: "`_persist_review_artifact_override_in_coord` deleted in WP09 ... the
primary/coord frontmatter mirror collapsed into the single review emit"), and #2646's own report
("the approved review-cycle-2.md ... committed cleanly on COORD") describes review-cycle-FILE behavior
that current code's `_review_cycle_wp_dir` (unconditionally PRIMARY-partition per `MissionArtifactKind.
WORK_PACKAGE_TASK`) does not appear to still produce — the same kind of staleness this mission's
pre-spec research already found for #2275 and #1817.

**Rationale**:
- `_get_wp_review_verdict` (`agent_utils/status.py:40-62`) does a bare `wp_dir.glob("review-cycle-*.md")`
  and parses frontmatter directly — it never calls `resolve_snapshot_review`/`latest_review_artifact_verdict`,
  the event-sourced pair the merge gate (`review/artifacts.py:307-346`) already uses specifically to
  avoid exactly this kind of staleness for the override case.
- `latest_review_artifact_verdict` accepts an optional `snapshot_override: ReviewOverride | None` and
  treats the event-sourced snapshot as authority when present ("snapshot-first, not dual"). The same
  pattern — resolve the WP's event-sourced review state via `resolve_snapshot_review(feature_dir, wp_id)`
  first, fall back to the file-glob only when no snapshot entry exists — is directly reusable for the
  stale-verdict scan, rather than a bespoke coord-authority read-router.
- `resolve_snapshot_review` takes `feature_dir` as a caller-supplied parameter; for coord-topology
  missions the caller must supply the coord-resolved `feature_dir` (the same one `_mt_resolve_targets`
  already resolves via `ports.coord.feature_write_dir(handle)` for status/task events), not the
  PRIMARY `tasks_dir` `agent_utils/status.py` currently hardcodes.

**Alternatives considered**: Building a new "review-cycle kind" PlacementSeam classification that
routes both write and read per-topology was considered (this is what the pre-spec research's Option D
recommended against as unnecessary) — rejected: it would duplicate the event-sourced snapshot mechanism
that already solves this exact class of problem for the override case, and would touch far more
surface than reusing that existing authority.

**Correction (post-plan adversarial squad, code-verified + live-reproduced) — this R3 decision is
retracted and replaced.** Two independent lenses found the proposed mechanism does not work as
described, and a third found live evidence the fix may be unnecessary:

1. **Type-shape mismatch**: `ReviewOverride` (`status/models.py:398-423`) has exactly four fields —
   `at`, `actor`, `wp_id`, `reason` — and **no `verdict` field**. `resolve_snapshot_review` returns
   `ReviewOverride | None`; it cannot supply a review verdict, only override provenance.
   `latest_review_artifact_verdict` (the pattern this R3 cited) does not get its verdict from the
   snapshot either — it still file-globs and reads `ReviewCycleArtifact.verdict` from frontmatter;
   `snapshot_override` there is consulted only to compute the `has_override` boolean. The snapshot
   `review` slot is populated only on override events — a normal approve/reject never writes it — so
   for exactly #2646's non-override scenario, `resolve_snapshot_review` would return `None` and the
   proposed fallback collapses straight back to the same PRIMARY-only file-glob that is the bug.
2. **Live reproduction shows #2646 is caused by FR-001's absence, not a live coord/primary split.**
   Built a real coord-topology fixture and drove it through the actual `create_rejected_review_cycle`:
   reject cycle 1, approve → no cycle-2 file is ever written (matching #2996(a)'s finding — no code
   path writes an approved-verdict artifact today). `agent tasks status` correctly reports stale,
   because cycle 1 genuinely is the latest artifact. Hand-authoring a `review-cycle-2.md` with
   `verdict: approved` into the **same PRIMARY directory** cycle 1 already lived in (zero changes to
   `agent_utils/status.py`) made the stale-verdict warning disappear cleanly. The write-vs-read
   authority split #2646 originally reported appears to have already been closed by an earlier,
   separately-merged mission (`607e561bf`/`97f24d9bf`, the placement-seam unification) — independent of
   anything this mission does.
3. **#2697 remains live but is a different gap than R3 assumed** — its "no single canonical committed
   record" symptom is the same commit-gap R1's correction above closes, not a read-authority split.

**Revised decision**: drop the `resolve_snapshot_review`-based redesign entirely. FR-003 becomes
verify-first: after FR-001 ships, re-drive #2646's scenario against the real writer and confirm via a
checked-in regression test that the stale-verdict warning is already gone with **zero changes to
`agent_utils/status.py`**. Only if that verification fails does FR-003 include designing and building a
targeted fix against the actual observed failure (not this retracted design). Operator-confirmed
2026-08-02.

## R4 — Verdict-vocabulary validator change (C-002)

**Decision**: `validate_review_artifact` (`review/cycle.py:184-188`) loosens its check from
`if artifact.verdict != "rejected": raise ...` to accepting any member of the existing
`REVIEW_ARTIFACT_VERDICTS` frozenset (`{"approved", "rejected"}`, already defined in
`review/artifacts.py:26`) — the schema already declares both verdicts valid; only this one validator
function is stricter than the schema it's meant to enforce.

**Rationale**: Confirmed by direct read — `ReviewCycleArtifact.verdict` is typed to allow both values
today, but this one call-time guard rejects `"approved"` unconditionally. No other validator or reader
in the codebase has this restriction (the merge gate's read path already tolerates `"approved"` fine).

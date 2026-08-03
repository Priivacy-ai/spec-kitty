---
work_package_id: WP01
title: Durable, provenance-guarded review-verdict writer
dependencies: []
requirement_refs:
- C-002
- FR-001
- FR-002
- FR-004
planning_base_branch: research/3044-review-artifact-topology-seam
merge_target_branch: research/3044-review-artifact-topology-seam
branch_strategy: Planning artifacts for this mission were generated on research/3044-review-artifact-topology-seam. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/3044-review-artifact-topology-seam unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
history:
- at: '2026-08-02T16:42:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/cycle.py
- src/specify_cli/review/artifacts.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- tests/review/test_cycle.py
- tests/post_merge/test_review_artifact_consistency.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 - Durable, provenance-guarded review-verdict writer

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

Today, approving a previously-rejected work package (WP) persists **no artifact at all** — the stale
`rejected` verdict from the last review cycle stays authoritative, so every terminal gate
(`move-task --to done`, `spec-kitty merge`) blocks the ordinary path and forces `--skip-review-artifact-check`,
a flag meant only for genuine arbiter overrides. Separately, the existing rejection writer accepts any
file as "feedback" without checking what it actually is, so it can be fed a prior cycle's own artifact
(by path or by a renamed copy) and silently produce a fabricated/duplicated review under synthetic
frontmatter. And — found via live reproduction by a post-plan adversarial squad — **neither the
existing nor the new writer ever commits its output**: the file lands untracked in whatever branch
happens to be checked out at the main repo root.

This work package closes all three gaps in one generalized function:

1. **FR-001**: a real `verdict: approved` artifact gets written and committed when a rejected WP is approved through the normal path.
2. **FR-002**: the writer refuses to build a new cycle's body from a feedback source that is itself (by path or content) a prior cycle's own artifact for the same WP.
3. **Commit durability** (closes #2697): every write — both verdicts — is committed via the existing `commit_artifact` port capability, not left untracked.

**Success criteria** (from spec.md, verbatim where useful):
- SC-001: every WP moving from rejected-latest to approved/done has a highest-numbered artifact with `verdict: approved` before merge is attempted.
- SC-002: no test exercising the ordinary reject→fix→approve path needs `--skip-review-artifact-check`.
- SC-003 (this WP's share): every write is committed (`git status` shows it tracked immediately after).
- SC-004: `test_self_referential_feedback_source_is_rejected` and `test_new_cycle_body_never_duplicates_a_prior_cycle_file` turn from RED to green.

## Context & Constraints

Read these in full before starting — they contain the exact code citations and design decisions this
WP implements, including two corrections a post-plan squad made after the first plan draft:

- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/spec.md` — User Stories 1 & 2, FR-001, FR-002, C-002
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/plan.md` — IC-01 (merged from the original IC-01+IC-02)
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/research.md` — R1 (commit-step finding + correction), R2 (provenance guard design), R4 (validator loosening)
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/data-model.md` — ReviewCycleArtifact, state transitions
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/contracts/review-cycle-writer.md` — the exact function-contract this WP implements
- `kitty-specs/review-verdict-write-integrity-01KZ1CGF/quickstart.md` — FR-001/FR-002 manual verification commands

**Note on FR-004**: mapped to this WP only for requirement-coverage bookkeeping — FR-004 (the #2275
tracker comment) was already completed before planning began (see spec.md's Assumptions). There is no
code action for FR-004 in this WP; do not look for one.

**Constraints (binding)**:
- C-002: do not introduce a new verdict value — only `"approved"` and `"rejected"` (both already in `REVIEW_ARTIFACT_VERDICTS`, `review/artifacts.py:26`).
- C-001/C-003: do not touch `PlacementSeam`, `_review_cycle_wp_dir`'s routing logic, or `_ensure_target_branch_checked_out`'s branch-checkout behavior — these are confirmed correct and out of scope. The commit step must **reuse** `commit_artifact` as-is, not build new commit/branch-resolution logic.
- Backward compatibility: every existing call site of `create_rejected_review_cycle` must keep working unchanged — the `verdict` parameter defaults to `"rejected"`.

## Subtasks & Detailed Guidance

### Subtask T001 – Generalize `create_rejected_review_cycle` with a `verdict` parameter

- **Purpose**: Make one function capable of writing either verdict, so FR-002's guard and the new commit step protect both paths identically instead of duplicating logic across two functions.
- **Steps**:
  1. In `src/specify_cli/review/cycle.py`, add a `verdict: Literal["approved", "rejected"] = "rejected"` keyword-only parameter to `create_rejected_review_cycle` (function name stays the same — see `contracts/review-cycle-writer.md`, "name unchanged; behavior extended").
  2. Thread `verdict` into the constructed `ReviewCycleArtifact(...)` call (currently hardcodes `verdict="rejected"`).
  3. Do not rename the function or change its return type (`CreatedRejectedReviewCycle`) — every existing caller must compile and behave identically when `verdict` is omitted.
- **Files**: `src/specify_cli/review/cycle.py`
- **Parallel?**: No — T002–T005 all build on this signature.
- **Notes**: Confirm via `grep -rn "create_rejected_review_cycle(" src/` that both existing call sites — `tasks_move_task.py`'s `_mt_finalize_plan` and `tasks_materialization.py:148`'s `_persist_review_feedback` (a post-plan squad found the plan/research docs only named one; there are two) — are unaffected by the new default parameter before moving on. Neither needs a code change; both omit `verdict`, so both keep getting `"rejected"` behavior unchanged.

### Subtask T002 – Loosen `validate_review_artifact` to accept both verdicts

- **Purpose**: `validate_review_artifact` (`review/cycle.py:184-185`) currently hardcodes `if artifact.verdict != "rejected": raise ReviewCycleError(...)` — stricter than the schema it's meant to enforce (`REVIEW_ARTIFACT_VERDICTS = frozenset({"approved", "rejected"})`, `review/artifacts.py:26`). Without this fix, T001's new `verdict="approved"` path will fail its own post-construction validation.
- **Steps**:
  1. Change the check to `if artifact.verdict not in REVIEW_ARTIFACT_VERDICTS: raise ReviewCycleError(...)` (import the frozenset from `review.artifacts` if not already imported).
  2. Keep the error message meaningful for both failure cases (an invalid verdict string, not specifically "must be rejected").
- **Files**: `src/specify_cli/review/cycle.py`
- **Parallel?**: [P] with T003 — different concern in the same file, no line overlap expected.
- **Notes**: Do not touch `REVIEW_ARTIFACT_VERDICTS`'s own definition — C-002 forbids introducing a new vocabulary; this subtask only widens what the *validator* accepts to match what the *schema* already declares.

### Subtask T003 – Add the feedback-source provenance guard

- **Purpose**: Close #2996(b) (fabricated duplicate under synthetic frontmatter) and #990 (content-wrapping) as the identical mechanism in the identical function — confirmed by two pre-existing regression tests already RED on `main`.
- **Steps**:
  1. In `create_rejected_review_cycle`, after the existing existence/is-file/non-empty checks on `feedback_source` (lines ~287-294) and before `body = feedback_source.read_text(...)`, add two checks, both raising `ReviewCycleError` on match:
     - **Path-identity check**: resolve `feedback_source` to an absolute path; refuse if it resolves to a `review-cycle-*.md` file inside this WP's own `sub_artifact_dir` (i.e., `_review_cycle_wp_dir(...)`'s own output directory).
     - **Content-identity check**: strip any leading YAML frontmatter block from `feedback_source`'s body (reuse whatever frontmatter-stripping helper already exists in this module — do not hand-roll a second one), normalize whitespace, and compare against every existing `review-cycle-N.md` in the same `sub_artifact_dir` (also frontmatter-stripped, whitespace-normalized). Refuse on an exact match.
  2. Apply the guard uniformly regardless of `verdict` — a caller could in principle mis-supply a stale file for either an approval or a rejection.
- **Files**: `src/specify_cli/review/cycle.py`
- **Parallel?**: [P] with T002.
- **Notes**: `tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected` and `::test_new_cycle_body_never_duplicates_a_prior_cycle_file` already exist and are RED — read them first; they define the exact fixture shapes this guard must satisfy. Do not weaken the content check to a substring/fuzzy match — exact-match-after-normalization is the documented, testable boundary (research.md R2's "alternatives considered" explicitly rejected hashing/fuzzy matching as unnecessary complexity at this scale, not as a shortcut to skip).
  **⚠️ Contradiction a post-tasks squad found, resolve it exactly this way**: `test_new_cycle_body_never_duplicates_a_prior_cycle_file` (as currently committed) does **not** wrap its second `create_rejected_review_cycle(...)` call in `pytest.raises` — it was written before this mission's design (raise on any content match, per spec.md Acceptance Scenario 2's "the operation is refused") was finalized, and its current form models a narrower, non-raising outcome that this mission's actual scope supersedes. **You must update this test as part of T003** (not leave it as an untouched pinned fixture): wrap its second `create_rejected_review_cycle(...)` call in `pytest.raises(ReviewCycleError, match=...)`, matching `test_self_referential_feedback_source_is_rejected`'s shape, then replace the post-call `assert cycle2.artifact.body not in prior_bodies` block with an assertion that `ReviewCycleArtifact.latest(wp_dir)` still returns cycle 1 (whose `reviewer_agent` is the real value passed at cycle-1 creation, not `"unknown"`) — i.e., the refusal means cycle 2 is never written at all, so "latest" naturally stays cycle 1. Do **not** try to satisfy the test's current (pre-mission-design) assertions by making the write succeed with a merely-different body — that path independently violates spec.md's "operation is refused" requirement even if it turns the assertion green, and a post-tasks squad specifically flagged this as a shortcut that rewards the wrong implementation. Also add one additional case to T006 (see below): a feedback file whose **path** matches (lives at a `review-cycle-N.md` path in the WP's own dir) but whose **content** has been hand-edited to differ — the two existing tests can both be satisfied by content-matching alone, so this extra case is the only thing that forces genuine path-based logic to exist too.

### Subtask T004 – Add the commit step

- **Purpose**: Close the gap a post-plan squad found via live reproduction — the writer's output was never git-committed under any topology, which undercuts this mission's entire purpose (durable persistence) and is the same root cause as #2697 ("no single canonical committed rejection record").
- **Steps**:
  1. Locate the `commit_artifact` port capability (current call sites: `src/specify_cli/cli/commands/agent/tasks_mark_status.py:232`, `src/specify_cli/cli/commands/agent/tasks_map_requirements.py:546` — read both to understand the calling convention: what arguments it needs, what port/ports object it's called on).
  2. After `artifact.write(artifact_path)` succeeds (and after `validate_review_artifact_file(artifact_path)` passes) in `create_rejected_review_cycle`, call `commit_artifact` (or the equivalent port method) to commit `artifact_path`. This is the review-cycle writer's **first** use of this capability — thread through whatever port/ports argument the function needs to gain access to it (check how `_mt_finalize_plan` in `tasks_move_task.py` already has a `ports` object available at its call site, and whether it can be passed down, or whether `create_rejected_review_cycle` needs a new optional `ports`/`commit_fn` parameter — prefer the smallest change that doesn't force unrelated callers to pass a new required argument).
  3. Do not build a new commit/staging mechanism — reuse `commit_artifact` exactly as its two existing callers do.
- **Files**: `src/specify_cli/review/cycle.py`, `src/specify_cli/cli/commands/agent/tasks_move_task.py` (only if threading a ports argument requires a call-site change)
- **Parallel?**: No — depends on T001's new signature existing; sequence after T001, alongside or after T002/T003.
- **Notes**: This was the single highest-severity finding from the post-plan squad (architect-alphonso and debugger-debbie both independently confirmed it via live reproduction and static trace). Do not skip it or treat it as optional — it is FR-001's own acceptance criterion (spec.md User Story 1, Acceptance Scenario 4) and the primary mechanism closing #2697.

### Subtask T005 – Wire `move-task --to approved`/`--to done` to call the writer

- **Purpose**: Make the generalized writer actually fire on the normal approval path — today, `_mt_plan_review_result` (`tasks_move_task.py:1747-1778`) builds an in-memory `ReviewResult(verdict="approved", ...)` that only feeds the status-event FSM; nothing persists it as a file.
- **Steps**:
  1. In `_mt_finalize_plan` (`tasks_move_task.py:1704-1716`), alongside the existing `if decision.planned_rollback and st.resolved_feedback_source is not None:` branch that calls `create_rejected_review_cycle` for rejections, add the approval-side call: when the transition target is `approved`/`done` (`st.target_lane in (Lane.APPROVED, Lane.DONE)`) **and** the WP's current highest-numbered review-cycle artifact has `verdict == "rejected"`, call the (now-generalized) writer with `verdict="approved"`.
  2. Determine the "current highest-numbered artifact's verdict" check using existing helpers (e.g., whatever `latest_review_artifact_verdict`/`ReviewCycleArtifact.from_file` machinery the merge gate already uses — do not hand-roll a second reader).
  3. Ensure this fires identically whether the target lane is `approved` or `done` directly (spec.md User Story 1, Acceptance Scenario 3 — the write must not be conditional on which terminal lane is the target).
  4. Pass a real `reviewer_agent` (from `st.agent`/`st.reviewer`/`st.actor`, matching the pattern `_mt_plan_review_result` already uses) — never the literal `"unknown"` for a genuine approval.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`
- **Parallel?**: No — depends on T001 (verdict parameter) and T004 (commit step) both existing.
- **Notes**: Do not call the writer when the latest artifact is already `approved` (no-op re-approval) or when there is no prior artifact at all (first-ever review cycle for a WP — that path is unaffected by this mission).

### Subtask T006 – Extend `tests/review/test_cycle.py`

- **Purpose**: Turn the two pre-existing red tests green and add direct coverage for the new approved-verdict and commit-durability behavior.
- **Steps**:
  1. Update `test_new_cycle_body_never_duplicates_a_prior_cycle_file` per T003's note above (wrap in `pytest.raises`, assert `latest` stays cycle 1), then confirm both it and `test_self_referential_feedback_source_is_rejected` pass.
  2. Add a path-only test: a feedback file at a `review-cycle-N.md`-shaped path inside the WP's own directory, but with hand-edited (non-duplicate) content — assert it is still refused (`pytest.raises(ReviewCycleError)`). This is the case that forces genuine path-based detection to exist, since the two pre-existing tests can both be satisfied by content-matching alone.
  3. Add a test that calls the generalized writer with `verdict="approved"` against a WP whose latest artifact is `rejected`, and asserts the new artifact's frontmatter (`verdict: approved`, real `reviewer_agent`, correct next cycle number).
  4. Add a test asserting the write is committed — e.g., call the writer against a real git-initialized fixture repo and assert `git status --porcelain` shows no untracked/modified marker for the new artifact file immediately after the call (mirrors quickstart.md's FR-001 commit-step verification).
  5. Add a test confirming existing callers of `create_rejected_review_cycle` (omitting `verdict`) still produce identical `rejected` behavior — a straightforward backward-compatibility regression.
- **Files**: `tests/review/test_cycle.py`
- **Parallel?**: No — depends on T001-T004 all being implemented.
- **Notes**: `tests/coordination/test_analysis_report_rehome.py` already shows the pattern for asserting commit state after a review-cycle write via `commit_for_mission(...)` — read it for the fixture idiom before writing new git-state assertions from scratch.

### Subtask T007 – Extend `tests/post_merge/test_review_artifact_consistency.py`

- **Purpose**: Confirm the merge gate's own integration behavior — `REJECTED_REVIEW_ARTIFACT_CONFLICT` must not fire once a real approved artifact exists, closing the loop from writer to gate.
- **Steps**:
  1. Add an integration test: reject a WP (cycle 1), approve it via the shipped writer (cycle 2, `verdict: approved`), then run the merge-gate's conflict-detection function (`find_rejected_review_artifact_conflicts` or equivalent) directly (or via `spec-kitty merge --dry-run` if the test harness supports it) and assert no conflict is reported for that WP.
  2. Add a negative-control test confirming the gate still correctly blocks when the latest artifact genuinely is `rejected` (no regression to the existing, correct blocking behavior).
- **Files**: `tests/post_merge/test_review_artifact_consistency.py`
- **Parallel?**: No — depends on T001-T005.
- **Notes**: This is the acceptance test for spec.md User Story 1, Acceptance Scenario 2.

## Test Strategy

- `pytest tests/review/test_cycle.py tests/post_merge/test_review_artifact_consistency.py -v`
- `mypy --strict src/specify_cli/review/cycle.py src/specify_cli/review/artifacts.py src/specify_cli/cli/commands/agent/tasks_move_task.py`
- Full scoped regression before marking done: `pytest tests/review/ tests/post_merge/ tests/agent/ -q` (NFR-001 — zero regressions in these packages)
- **NFR-003 coverage** (an `/spec-kitty.analyze` gap found this was otherwise uncovered): the new work per
  write is one filesystem write plus one `commit_artifact` call — the same shape the existing rejection
  path already performs today. Add a simple timing assertion in `tests/review/test_cycle.py` wrapping a
  `create_rejected_review_cycle` call (either verdict) in `time.perf_counter()` and asserting it completes
  within a generous fixed budget (e.g., under 2 seconds on CI hardware) rather than building a full
  before/after benchmark harness — a fixed-budget check is proportionate for a mission whose new work is
  one additional git commit, and avoids the flakiness of comparing against a "pre-mission baseline" that
  would need its own separate measurement run.

## Risks & Mitigations

- **Commit-step threading risk**: adding a commit call inside `create_rejected_review_cycle` may require a new parameter (a ports/commit-function argument) that ripples into its one existing call site. Mitigate by making the new parameter optional with a sensible default that preserves today's behavior for any caller that doesn't pass it explicitly (though the production call site in `_mt_finalize_plan` must always pass it — do not silently skip committing there).
- **Provenance guard false positives**: an overly aggressive content-match could reject legitimate rejections that happen to reuse similar wording. Mitigate with the documented exact-match-after-normalization boundary (T003), not a fuzzy/similarity heuristic.
- **Backward compatibility**: any change to `create_rejected_review_cycle`'s signature or `validate_review_artifact`'s check risks breaking an untested caller. Mitigate by running the full `tests/review/` and `tests/post_merge/` suites (not just the new tests) before marking this WP done.

## Review Guidance

- Confirm T004's commit step is real — the reviewer should independently verify (e.g., `git log` in a test fixture) that a write actually lands as a commit, not just that no exception was raised.
- Confirm the provenance guard (T003) rejects the exact-path case, the renamed/duplicate-content case, AND the path-only case (T006 step 2) — a common shortcut is to implement only the path check, or only content-matching, and call it done since either alone happens to satisfy the two originally-pinned tests.
- Confirm `test_new_cycle_body_never_duplicates_a_prior_cycle_file` was actually rewritten to `pytest.raises` (per T003's note), not left in its pre-mission-design, non-raising form with a shortcut implementation bolted on to turn it green.
- Confirm no existing caller of `create_rejected_review_cycle` or `validate_review_artifact` needed changes to keep passing — this is the backward-compatibility bar C-002 and NFR-001 set.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-02T16:42:46Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

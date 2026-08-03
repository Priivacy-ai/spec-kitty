# Mission Specification: Review Verdict Write Integrity

**Mission Branch**: `research/3044-review-artifact-topology-seam`
**Created**: 2026-08-02
**Status**: Draft
**Input**: GitHub issue #3044 ("Epic: review-artifact integrity — approval must write a real verdict, and no cycle may fabricate one"), scoped by the pre-spec research at `docs/plans/investigations/review-artifact-write-integrity-3044.md`, revised by a post-spec adversarial squad, and revised again by a post-plan adversarial squad. Corroborated scope: add a missing approved-verdict writer that is **durably committed, not merely written** (closes #2275's residual gap + #2996(a) + #2697 — a post-plan squad found live that the writer never committed its output under any topology, a pre-existing gap this mission now closes rather than inherits); harden the rejected-verdict writer's feedback-source provenance validation against both fabrication and content-wrapping (closes #2996(b) and #990 — folded in after the post-spec squad found both are the identical mechanism); verify #2646 closes as a side effect of the durable-commit fix above, building a targeted fix only if that verification fails (a post-plan squad found live evidence #2646's original coord/primary read split was already closed by an earlier, separately-merged mission, and that the fix this spec originally proposed for it was type-shape broken). #1817 was verified and closed as a stale duplicate of the already-fixed #1924 directly on the tracker — it is not mission scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A rejected work package reaches a durable, committed approval (Priority: P1)

A work package (WP) is rejected on review cycle N. The implementer fixes it, and a reviewer re-reviews and approves it. Today, `move-task --to approved` accepts the transition and advances the WP's status, but persists no artifact recording that decision — cycle N's `rejected` verdict remains the highest-numbered, authoritative artifact. Every downstream terminal gate (`move-task --to done`, `spec-kitty merge`) reads that stale artifact and refuses, forcing the reviewer or operator to reach for `--skip-review-artifact-check` — a flag intended for genuine arbiter overrides — just to get an ordinary approval to stick. A post-plan adversarial squad additionally found, via live reproduction, that the underlying writer (shared by both the rejected and the new approved path) never git-commits its output at all — it lands as an untracked file wherever the invoking checkout's HEAD happens to be. "Durable" in this story therefore means committed, not merely written to disk.

**Why this priority**: This is the mission's P0-rated core defect (#2275's residual gap, #2996(a)). Without it, no other requirement in this mission matters — the escape hatch remains mandatory for the normal path, and every terminal gate keeps trusting evidence no reviewer actually wrote. The commit-durability half additionally closes #2697 (no single canonical *committed* rejection record) as the same underlying gap, not a separate mechanism.

**Independent Test**: Reject a WP (cycle 1, `rejected`), then approve it via the normal `move-task --to approved` path with no override flag. Confirm a new highest-numbered `review-cycle-(N+1).md` exists with `verdict: approved`, a real `reviewer_agent`, that it is committed (not merely present as an untracked file), and that `spec-kitty merge --dry-run` no longer blocks on `REJECTED_REVIEW_ARTIFACT_CONFLICT` for that WP.

**Acceptance Scenarios**:

1. **Given** a WP whose highest-numbered review-cycle artifact has `verdict: rejected`, **When** a reviewer transitions it to `approved` through the normal review path, **Then** a new review-cycle artifact is persisted with `verdict: approved`, a real (non-`unknown`) `reviewer_agent`, and the next sequential cycle number.
2. **Given** that newly-approved artifact exists, **When** `spec-kitty merge --dry-run` runs, **Then** it reports no conflict for that WP and no `--skip-review-artifact-check` override is needed.
3. **Given** a WP approved directly to `--to done` (skipping an intermediate `approved` lane) from a rejected-latest state, **When** the transition completes, **Then** the same approved-artifact persistence occurs — the write is not conditional on which terminal lane is the target.
4. **Given** either a rejection or an approval write (both verdicts, same underlying writer), **When** the transition completes, **Then** the resulting `review-cycle-N.md` is committed to the mission's authoritative branch — `git status` shows it tracked, not untracked — closing #2697's "no single canonical committed record" gap.

---

### User Story 2 - A rejection cycle cannot be filed as someone else's fabricated or wrapped review (Priority: P1)

Creating a rejection artifact accepts any file as the "feedback source" without checking what it actually is. If that source is itself a prior cycle's own review artifact for the same WP — whether by tooling error, manual mistake, or a renamed/copied variant of that prior artifact's content — the new cycle is filed as a duplicate of the old one, with fresh (often synthetic `reviewer_agent: unknown`) frontmatter wrapped around it. The artifact reads as though a second, independent review happened when none did.

**Why this priority**: This is #2996(b) and #990 — the fabrication and content-wrapping halves of the P0 epic, confirmed by a post-spec code trace to be the **identical mechanism** in the identical function (`create_rejected_review_cycle`'s unvalidated `feedback_source` read), not two separate defects. Both are reproducible today: `tests/review/test_cycle.py::test_self_referential_feedback_source_is_rejected` and `::test_new_cycle_body_never_duplicates_a_prior_cycle_file` are currently RED on `main`.

**Independent Test**: Attempt to create a rejection review-cycle artifact whose `feedback_source` is a prior `review-cycle-N.md` for the same WP (exact path, or a renamed/copied file carrying that prior cycle's content). Confirm the operation is refused rather than silently writing a duplicate/wrapped artifact under synthetic frontmatter.

**Acceptance Scenarios**:

1. **Given** WP02 already has `review-cycle-1.md`, **When** a rejection is filed with `--review-feedback-file` pointing at that same `review-cycle-1.md`, **Then** the operation fails with a clear error instead of writing a `review-cycle-2.md` that duplicates cycle 1's body under synthetic frontmatter.
2. **Given** a feedback source whose *content* (not just its path) is a copy of a prior cycle's frontmatter+body — e.g. a renamed duplicate of `review-cycle-1.md` — **When** a rejection is filed against it, **Then** the operation is refused on the same grounds as scenario 1; detection is not defeated by a simple rename.
3. **Given** a genuine, distinct feedback file, **When** a rejection is filed normally, **Then** the artifact is created exactly as before — the new validation does not reject legitimate rejections.

---

### User Story 3 - #2646's stale-verdict display is verified closed, not assumed fixed (Priority: P3)

A post-plan adversarial squad found, via live reproduction, that #2646's originally-reported symptom (an approved WP still displaying a stale `rejected` warning in `agent tasks status`) reproduces today for a simpler reason than its own report describes: no code path writes an approved verdict artifact at all yet (the User Story 1 gap), so the scan always finds the last real artifact, which is `rejected`. The squad further found that #2646's *originally-reported mechanism* — a coord/primary read-authority split — already appears closed by an earlier, separately-merged mission (the placement-seam unification), independent of this mission's work. This story replaces the "build a coord-authority read-router" design this spec originally committed to (which a squad also found was type-shape broken — `ReviewOverride` carries no verdict field) with a verify-first approach.

**Why this priority**: Demoted from P2 to P3 after the post-plan squad's finding that the fix may already be a free side effect of User Story 1, not separate work. Verification is still required — "probably already fixed" is not evidence, and this mission already found that exact assumption wrong once for #2646/#2697 pre-plan.

**Independent Test**: After User Story 1 lands, drive a `lanes_with_coord` mission's WP through reject→approve using only the shipped writer, then run `agent tasks status --json` and confirm no stale-verdict warning — with **zero changes to `agent_utils/status.py`**. Only if that verification fails does this story include building a targeted fix to that module.

**Acceptance Scenarios**:

1. **Given** User Story 1's writer has landed, **When** a `lanes_with_coord` mission's WP is rejected then approved through the normal path, **Then** `agent tasks status --json` reports the WP correctly with no stale-verdict warning, verified by a checked-in regression test — with no code change to `agent_utils/status.py` required to make it pass.
2. **Given** that verification fails (the stale-verdict warning still fires after User Story 1 lands), **When** the residual mechanism is traced, **Then** a targeted, minimal fix is scoped and implemented against the actual observed failure — not against this spec's original (superseded) coord-authority-router design.
3. **Given** a flat/single-branch mission, **When** the same transitions run, **Then** behavior is unchanged from today — this story does not alter non-coord topology either way.

### Edge Cases

- What happens when a WP has gone through many rejection cycles (cycle N is large) before finally being approved? The approved artifact must still land at the correct next sequential cycle number, not collide with or skip any prior cycle.
- How does the system handle a genuine arbiter/operator override (`--skip-review-artifact-check`) after User Story 1 ships, for a case where an actual code concern is being knowingly waived rather than worked around? The override mechanism itself is out of this mission's rebuild scope (already fixed per #1924, confirmed live in code) — it must continue to work unchanged for genuine override use, now simply no longer *needed* for the ordinary reject→fix→approve path.
- What happens if the new commit step (User Story 1) needs to commit to a different branch/worktree depending on topology (coord vs. flat)? The commit step reuses the existing, already-tested `commit_artifact` port capability rather than inventing new branch-resolution logic — it commits to whatever authority that capability already resolves for the mission's topology.
- #1817 is not an edge case of this mission: it was verified as a stale duplicate of #1924 and closed directly on the tracker before planning began.
- The plan-phase claim that User Story 1 and (the now-superseded) User Story 3 design shared commit-target-resolution surface was itself found stale by the post-plan squad and dropped — see Assumptions.

## Domain Language

- **Review-cycle artifact**: the durable, per-WP, per-cycle record of a review decision (`review-cycle-N.md`: cycle number, verdict, reviewer, affected files, body). The highest-numbered artifact for a WP is the one every terminal gate treats as authoritative.
- **Verdict**: the recorded outcome of a review cycle — `approved`, `rejected`, or `changes_requested`. Avoid "status" as a synonym; status/lane refers to the WP's separate lifecycle-lane state.
- **Override annotation**: an operator/arbiter-authored addendum (`review_artifact_override_*` frontmatter) recording a deliberate decision to treat a rejected-verdict artifact as the approval record. Distinct from an ordinary review decision — reserved for genuine arbitration, not a workaround for a missing writer.
- **Terminal gate**: a transition or merge-time check (`move-task --to approved/--to done`, `spec-kitty merge`'s `REJECTED_REVIEW_ARTIFACT_CONFLICT` invariant) that reads the highest-numbered review-cycle artifact as ground truth.
- **Coordination authority**: for `lanes_with_coord` missions, the coordination branch/worktree that is canonical for lifecycle events; distinct from the PRIMARY partition some artifact kinds resolve to unconditionally.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Persist a real, committed approved-verdict artifact on approval | As a reviewer/operator, I want approving a previously-rejected WP to durably persist AND commit a new highest-numbered review-cycle artifact with `verdict: approved` and a real `reviewer_agent`, so that terminal gates see an honest, committed recorded decision instead of a stale rejection or an untracked file. Includes adding a commit step (via the existing `commit_artifact` port capability) to the shared writer used by both verdicts — closing #2697 as the same underlying gap. | High | Open |
| FR-002 | Refuse rejection artifacts fabricated or wrapped from prior-cycle content | As a reviewer, I want the system to refuse creating a rejection artifact whose feedback source is itself (by path or by content) a prior cycle's own artifact for the same WP, so that a cycle number never implies an independent review that didn't happen and no cycle ever wraps another cycle's material. | High | Open |
| FR-003 | Verify #2646 closes via FR-001; fix only if verification fails | As a maintainer, I want #2646 re-driven against the shipped FR-001 writer and confirmed closed by a checked-in regression test with zero changes to `agent_utils/status.py`, so I don't build a fix for an already-closed defect — and I want a targeted, minimal fix built only if that verification actually fails. | Medium | Open |
| FR-004 | Annotate #2275 with its corrected residual scope | As a maintainer, I want #2275 commented on to record that its read-side split is already fixed in code and that this mission closes its remaining write-side gap, so future readers aren't misled by the issue's original wording. *(Completed pre-plan: comment posted, see Assumptions.)* | Low | Done |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No regression to existing review/merge-gate behavior | 100% of pre-existing tests under `tests/review/` and `tests/post_merge/` pass unchanged after this mission's changes. | Reliability | High | Open |
| NFR-002 | Red-then-green coverage for every new behavior | Each of FR-001 through FR-003 has at least one regression test that fails without its fix and passes with it. FR-002's coverage includes the two pre-existing tests already RED on `main` (`test_self_referential_feedback_source_is_rejected`, `test_new_cycle_body_never_duplicates_a_prior_cycle_file`). | Reliability | High | Open |
| NFR-003 | No meaningful performance regression on the approval/merge path | `move-task --to approved` and `spec-kitty merge --dry-run` show no more than 5% wall-clock regression versus pre-mission baseline on a representative multi-WP mission. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No general topology-seam re-architecture | This mission does not re-architect the `PlacementSeam` program itself. #2275/#2996's residual gap needs no topology-seam change — its placement routing is already correct. FR-001's commit step reuses the existing `commit_artifact` port capability as-is; FR-003 is verify-first and, if a fix is needed at all, must be minimal and targeted — neither is a general re-architecture of the seam. | Technical | High | Open |
| C-002 | Verdict vocabulary and cycle numbering unchanged; verdict validator scope is explicit | The set of valid verdicts (`approved`/`rejected`/`changes_requested`) and the sequential review-cycle numbering scheme are unchanged. `validate_review_artifact` currently hardcodes a rejected-only check (`src/specify_cli/review/cycle.py:184-188`) and must be loosened as part of FR-001 — this is in-scope schema-validation work, not a vocabulary change. | Technical | High | Open |
| C-003 | No relitigating the coord/primary partition | Consistent with #3044's own non-goal: nothing in this mission is an argument to change the coordination-branch/worktree topology itself. FR-001's commit step lands on whatever authority the existing `commit_artifact` capability already resolves for the mission's topology — it does not redesign that resolution. | Technical | Medium | Open |
| C-004 | This mission closes all of #3044's children, but not #1817/#2646/#2697 as epic members | With #990 folded into FR-002, this mission's completion closes all three of #3044's native children (#2275, #2996, #990). #1817 (already closed, duplicate-of-#1924), #2697 (closed by FR-001's commit step), and #2646 (verified/fixed by FR-003) are independent issues, not #3044 children — their resolution is bundled into this mission for efficiency, not because they are epic scope. | Process | Medium | Open |

### Key Entities

- **Review-Cycle Artifact**: the durable per-WP, per-cycle record of a review decision (cycle number, verdict, reviewer, affected files, body). The highest-numbered one is authoritative for terminal gates.
- **Work Package (WP)**: the unit under review; owns a directory of review-cycle artifacts under its mission.
- **Override Annotation**: an operator/arbiter-authored addendum recording a deliberate decision to treat a rejected-verdict artifact as the approval record, distinct from an ordinary review decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every WP that moves from a rejected-latest state to `approved`/`done` has a highest-numbered review-cycle artifact whose verdict is `approved` before any merge is attempted — zero false-positive `REJECTED_REVIEW_ARTIFACT_CONFLICT` blocks on the ordinary reject→fix→approve path.
- **SC-002**: In this mission's regression suite, no test exercising the ordinary reject→fix→re-review→approve path passes by invoking `--skip-review-artifact-check` — the flag appears only in tests that explicitly construct a genuine arbiter-override scenario.
- **SC-003**: Every review-cycle artifact write (both verdicts) is committed, not merely present as an untracked file — verified by a regression test asserting `git status` shows it tracked immediately after the write. #2697 is closed by this same evidence. #2646 is closed by a passing regression test showing zero `agent_utils/status.py` changes were needed (or, if verification fails, by a targeted fix plus its own regression test). #2275 carries its clarifying comment (posted); #1817 is closed as a duplicate (done, pre-plan).
- **SC-004**: `test_self_referential_feedback_source_is_rejected` and `test_new_cycle_body_never_duplicates_a_prior_cycle_file` (currently RED, reproducing #2996(b) and #990's identical mechanism) both turn green with no new test needed for #990 specifically.

## Assumptions

- #1817 was verified against current `main`, confirmed to be a stale, never-cross-referenced duplicate of the already-fixed-and-closed #1924, and closed directly on the tracker (comment + close) before this mission's planning began. It carries no FR and no mission scope.
- #2275 was verified, confirmed to have its read-side split already fixed in code, and commented on directly (see FR-004, status Done) — the comment is complete; FR-001 in this mission closes its residual write-side gap.
- #990 is folded into FR-002 rather than kept as a separate fast-follow: a post-spec code trace found it and #2996(b) are the identical mechanism in the identical function, with existing regression tests already reproducing both as RED.
- #2646/#2697 were reassessed after a post-spec code trace corrected the original assumption that they were "already closed by the same seam-routing fix that closed #2275's read-side split" — that first correction was itself incomplete. A post-plan adversarial squad, working from live reproduction rather than static reading, found: (a) the writer shared by both verdicts never git-commits its output under any topology — a real, pre-existing gap this mission now closes via FR-001 rather than inheriting silently, and the same gap #2697 was reporting all along; (b) #2646's reproduction today is caused simply by FR-001 not existing yet, not by a live coord/primary read split — that split appears already closed by an earlier, separately-merged mission (the placement-seam unification) — so FR-003 is verify-first, not a committed redesign; (c) this spec's originally-planned FR-003 mechanism (routing `agent_utils/status.py` through `resolve_snapshot_review`) was independently found type-shape broken (`ReviewOverride` carries no `verdict` field) and has been dropped.
- FR-003's dependency on FR-001's commit-target-resolution surface (flagged during `/spec-kitty.plan`) was resolved by research to be unnecessary — the post-plan squad found FR-001's writer needs no branch-checkout hardening at all (only the commit step above), so FR-001 and FR-003 touch disjoint files and can be implemented as independent, parallel-safe work packages.

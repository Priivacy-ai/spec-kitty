# Tasks — Investigate canary follow-ups #1142 and #1141

**Mission**: `investigate-canary-followups-1142-1141-01KS02TV`
**Mission ID**: `01KS02TVCYPQXQ9DX1Z39SXZ6K`
**Date**: 2026-05-19
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Quickstart**: [quickstart.md](./quickstart.md)

This mission is an investigation/runbook. The deliverables are GitHub issue comments + one cross-branch markdown edit per issue. No spec-kitty source code is modified.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Pre-flight repo state verification (FR-008) | WP01 | — |
| T002 | Verify `NEXT-AGENT-HANDOFF.md` is absent (FR-009) | WP01 | — |
| T003 | Snapshot issue #1142 body to `research/issue-1142-snapshot.json` | WP01 | — |
| T004 | Execute #1142 H1 clean-venv repro (NFR-004 ≤ 15 min) | WP01 | — |
| T005 | Execute #1142 H2 emitter walk (only if H1 RED; FR-004) | WP01 | — |
| T006 | Compose + post #1142 substantive comment per `contracts/issue-comment-shape.md` (FR-002, NFR-003) | WP01 | — |
| T007 | Close #1142 with fix-pattern comment (only if H1 CONFIRMED; FR-003) | WP01 | — |
| T008 | Update `mission-exception.md ## Follow-up` row for #1142 on focused-PR branch (FR-007, C-001) | WP01 | — |
| T009 | Snapshot issue #1141 body to `research/issue-1141-snapshot.json` | WP02 | — |
| T010 | Execute #1141 H4 (fixture state) cheapest-first check | WP02 | — |
| T011 | Execute #1141 H3 (sequencing race) if H4 ruled out | WP02 | — |
| T012 | Execute #1141 H2 (payload shape comparison) if H3 ruled out | WP02 | — |
| T013 | Execute #1141 H1 (CLI regression via `git log`) if H2 ruled out | WP02 | — |
| T014 | Compose + post #1141 substantive comment with A/B/C recommendation (FR-006) | WP02 | — |
| T015 | Update `mission-exception.md ## Follow-up` row for #1141 on focused-PR branch (FR-007, C-001) | WP02 | — |

`[P]` markers are intentionally omitted; the cross-branch `mission-exception.md` is touched by both WPs, so WP02 is sequenced after WP01 to keep the focused-PR-branch edit single-threaded.

---

## Work Package 1 — #1142 investigation (7-day window)

**Priority**: P0 (operator-committed window is shorter)
**Goal**: Investigate #1142 cheapest-first (H1 → H2 → H3), post a substantive comment, close with fix-pattern if H1 confirms, and record the outcome in `mission-exception.md` `## Follow-up`.
**Window deadline**: 2026-05-26 (UTC end-of-day)
**Estimated prompt size**: ~420 lines (8 subtasks, conditional branches)

### Independent test

A reviewer can copy the Commands section from the posted #1142 comment, run them on a fresh canary venv, and reach the same conclusion within 15 minutes (NFR-003).

### Included subtasks

- [x] T001 Pre-flight repo state verification (FR-008) (WP01)
- [x] T002 Verify `NEXT-AGENT-HANDOFF.md` is absent (FR-009) (WP01)
- [x] T003 Snapshot issue #1142 body (WP01)
- [x] T004 Execute #1142 H1 clean-venv repro (WP01)
- [x] T005 Execute #1142 H2 emitter walk (conditional) (WP01)
- [x] T006 Compose + post #1142 substantive comment (WP01)
- [x] T007 Close #1142 with fix-pattern (conditional) (WP01)
- [x] T008 Update `mission-exception.md ## Follow-up` row for #1142 (WP01)

### Implementation sketch

1. **Pre-flight (T001 + T002)**. Run the four-command pre-flight from `quickstart.md` Step 0. Halt and report drift if any check fails.
2. **Snapshot (T003)**. `gh issue view 1142 --json title,body,labels,state > research/issue-1142-snapshot.json` so the hypothesis numbering is pinned.
3. **H1 repro (T004)**. Follow `quickstart.md` Step 1 verbatim. Capture three logs: `/tmp/h1-pip-canary.log`, `/tmp/h1-pip-spec-kitty.log`, `/tmp/h1-run.log`. Copy them under `research/` for the comment evidence.
4. **Branch on result**:
   - **H1 GREEN twice in a row** → T006 with `Conclusion: CONFIRMED — H1 (stale canary venv)`, then T007 closes with fix-pattern wording.
   - **H1 RED** → T005 (emitter walk per `research.md` R3). If a non-conforming emitter is found, open a **separate** 1-WP follow-up mission via `/spec-kitty.specify` (do not patch in this mission — C-003). Then T006 with `Conclusion: RULED_OUT` + linked follow-up.
5. **Cross-branch follow-up (T008)**. Per `contracts/follow-up-update-shape.md` and `quickstart.md` Step 6. Default branch `kitty/pr/unblock-sync-identity-boundary-canary-01KRZJ07-to-main`; fallback to `main` if PR #1143 already merged.

### Dependencies

- None.

### Risks

- `gh` token scope insufficient → fix via `unset GITHUB_TOKEN` per CLAUDE.md.
- PR #1143 merged mid-investigation → fallback path in `quickstart.md` Step 6.
- H1 false-positive single run → mandate "green twice in a row" before declaring `CONFIRMED`.

---

## Work Package 2 — #1141 investigation (14-day window)

**Priority**: P1
**Goal**: Investigate #1141 cheapest-first (H4 → H3 → H2 → H1), post a substantive comment with a Recommendation (A/B/C), and record the outcome in `mission-exception.md` `## Follow-up`.
**Window deadline**: 2026-06-02 (UTC end-of-day)
**Estimated prompt size**: ~380 lines (7 subtasks, conditional branches)

### Independent test

A reviewer can read the posted #1141 comment, follow its Commands section to the same file/line citations in `tests/identity_boundary/test_scenario_4_review_rejection_contract.py` and `src/specify_cli/status/{lifecycle_events,store}.py`, and arrive at the same conclusion within 15 minutes (NFR-003).

### Included subtasks

- [x] T009 Snapshot issue #1141 body (WP02)
- [x] T010 Execute #1141 H4 (fixture state) (WP02)
- [x] T011 Execute #1141 H3 (sequencing race) — conditional (WP02)
- [x] T012 Execute #1141 H2 (payload shape comparison) — conditional (WP02)
- [x] T013 Execute #1141 H1 (CLI regression) — conditional (WP02)
- [x] T014 Compose + post #1141 substantive comment with A/B/C recommendation (WP02)
- [x] T015 Update `mission-exception.md ## Follow-up` row for #1141 (WP02)

### Implementation sketch

1. **Snapshot (T009)**. `gh issue view 1141 --json title,body,labels,state > research/issue-1141-snapshot.json`.
2. **Hypothesis sweep (T010 → T013)**. Per `quickstart.md` Step 4, in order H4 → H3 → H2 → H1. Stop at the first hypothesis that explains the failure. Each hypothesis check's evidence (file/line refs, log excerpts, git log slices) goes under `research/h4-evidence-1141.md` (etc.).
3. **Comment (T014)**. Per `contracts/issue-comment-shape.md`, the comment MUST include the `### Recommendation` heading with one of A / B / C. Save the comment body to `research/comment-1141.md` first; post via `gh issue comment 1141`.
4. **Cross-branch follow-up (T015)**. Same as WP01-T008 but for the #1141 row.

### Dependencies

- Depends on **WP01** to keep the cross-branch `mission-exception.md` edit single-threaded (avoid file-level merge conflicts on the focused-PR branch).

### Risks

- Hypothesis sweep mis-orders (skipping H4) → wasted operator time on H1/H2. Mitigated by the cheapest-first rule (C-004).
- Recommendation A/B/C decision ambiguous → comment includes rationale; reviewer can override after merge.
- WP01 outcome not yet committed when WP02 starts → operator stages both follow-up rows on the focused-PR branch in one commit.

---

## MVP Scope

**WP01 is the MVP.** #1142's 7-day window is the tighter operator commitment and most-likely (H1) ends with a 10-minute confirmation + closing comment. Even if WP02 slips inside its 14-day window, WP01 delivered alone discharges the more time-sensitive commitment.

## Parallelization

These WPs are issue-independent but file-coupled on `mission-exception.md`. They are sequenced (WP02 → after → WP01) to keep a single-threaded edit on the focused-PR branch. If two operators must run in parallel, they MUST agree on a single rebase point for the cross-branch markdown edit.

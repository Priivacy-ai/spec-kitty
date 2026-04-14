---
work_package_id: WP08
title: FR-020 Approve-Output Source-Lane Anomaly Investigation
dependencies: []
requirement_refs:
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
phase: Phase 0 — Parallel investigation
agent: "claude:sonnet-4.6:implementer:implementer"
shell_pid: "57529"
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/research/
execution_mode: planning_artifact
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/research/fr020-investigation.md
tags: []
wp_code: WP08
---

# Work Package Prompt: WP08 — FR-020 Approve-Output Source-Lane Anomaly Investigation

## Implementation Command

```bash
spec-kitty agent action implement WP08 --agent <your-agent-name> --mission 01KP54ZW
```

No dependencies. Runs in the planning repo (no code worktree) — execution mode `planning_artifact`.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Planning artifact — edits happen directly in the main repo; no worktree.

---

## Objective

Determine whether the secondary anomaly reported in Priivacy-ai/spec-kitty#589 (approve transition reports `from in_progress` instead of `from for_review`) is:
- (a) a display bug in the approve output path, or
- (b) a deliberate consequence of how `spec-kitty agent action review` advances the lane state (review-claim does not advance to `in_review`), or
- (c) a reducer anomaly in `specify_cli/status/reducer.py`.

Produce an investigation report. If a code fix is warranted, document it and file a follow-up issue rather than smuggling the fix into this WP (ownership isolation).

---

## Context

- Issue #589 reported the anomaly on WP02 of mission 025:

  > When `move-task --to approved --force` succeeds, the output reports a transition from `in_progress` rather than `for_review`: ... But the reviewer had successfully transitioned the WP to `for_review` earlier.

- The lane state machine is documented in `CLAUDE.md` (section "Status Model Patterns"). Key files: `src/specify_cli/status/models.py`, `reducer.py`, `emit.py`, `lane_reader.py`.
- The review-claim action lives in `src/specify_cli/cli/commands/agent/workflow.py` (review function around line 982 `_resolve_review_context` and line 1136 `_find_first_for_review_wp`).
- FR-020: either fix the reporting so output matches lane history, OR document why the observed output is correct.

---

## Subtask Guidance

### T032 — Investigate the lane-state chain

**Files**: `kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/research/fr020-investigation.md` (new)

**What**: Produce a focused investigation following these steps:

1. **Read `spec-kitty agent action review` flow**: does it call `emit_status_transition` to advance the lane from `for_review` to `in_review`? If not, why not? Locate the code and record the exact call chain.

2. **Read `move-task --to approved`**: what does it use as the `from_lane` in the status event it emits? Does it read from the event log (correct), from frontmatter (wrong post-3.0), or from some in-memory variable?

3. **Reproduce the sequence**: in a test fixture, replay the exact transitions: `planned → claimed → in_progress → for_review → review-claim → approved`. Observe the emitted `from_lane` on the approved event.

4. **Verdict**:
   - If review-claim DOES advance to `in_review` but approved still reports `in_progress`, this is a display bug somewhere in the emit pipeline. Classify the exact bug.
   - If review-claim does NOT advance (lane remains at `for_review` during review), then `approved` reporting `in_progress` means some OTHER code path is setting the `from_lane` incorrectly. Classify.
   - If review-claim does not advance AND approved reports `from for_review`, there is no bug at all and Kent's report was based on a misreading. Publish a clarification.

Document findings in `research/fr020-investigation.md`. Include code references with file:line anchors, the reproduction steps, and the verdict.

---

### T033 — Publish the investigation outcome and escalate

**Files**: `kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/research/fr020-investigation.md`

**What**:

Based on T032's verdict:

- **If bug confirmed and fix is small + isolated**: append a "Recommended Fix" section that names the code change. File a follow-up issue in the main repo titled `"Fix approve-output from-lane reporting (FR-020 of mission 01KP54ZW)"` linking back to this investigation document. Close this WP once the follow-up issue is filed. Do NOT implement the fix in this WP — ownership isolation.

- **If bug confirmed but fix spans multiple files in other WPs' ownership**: same as above. File the follow-up issue with a scoped description.

- **If behaviour is correct but the output was misleading**: add a section to `docs/status-model.md` (requires coordinating with whichever WP owns that file — if none, add to the investigation doc itself and reference it from the CHANGELOG entry that WP09 produces).

- **If the original report was based on a misreading**: document the correct behaviour in the investigation doc and note that no code change is needed. Surface the finding in the #589 issue comment (via WP09).

Regardless of outcome, the investigation doc must end with a clear "Verdict" section stating which of the four outcomes applies and what the next step is.

---

## Definition of Done

- [ ] `research/fr020-investigation.md` exists and is committed.
- [ ] The document contains: reproduction steps, code references with file:line anchors, and a Verdict section.
- [ ] If a fix is needed, a follow-up issue is filed in Priivacy-ai/spec-kitty linking back to the investigation document.
- [ ] If documentation is needed, the content is either committed to `docs/status-model.md` (coordinated with its owner) or to the investigation doc itself.
- [ ] No code changes in WP-owned-by-others files are made as part of this WP.

## Risks

- **Ownership crossover**: the investigation may point at code in `reducer.py`, `emit.py`, or `workflow.py`, all of which are owned by other WPs or untouched by this mission. DO NOT edit them. File a follow-up issue and note the overlap.
- **Investigation scope creep**: stay narrowly focused on the `from_lane` reporting question. Do not expand into general lane-state model critique.

## Reviewer Guidance

- Verify the investigation document is thorough: code anchors are accurate, reproduction steps are complete, verdict is unambiguous.
- Verify NO code was edited outside `kitty-specs/.../research/`.
- Verify that if a follow-up issue was filed, it links back to this document and has a clear scope.

## Activity Log

- 2026-04-14T05:51:00Z – claude:sonnet-4.6:implementer:implementer – shell_pid=57529 – Started implementation via action command

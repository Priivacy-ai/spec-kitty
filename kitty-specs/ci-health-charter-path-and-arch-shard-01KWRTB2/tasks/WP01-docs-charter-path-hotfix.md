---
work_package_id: WP01
title: Docs charter-path hotfix
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
merge_target_branch: tidy/ci-docs-charter-path-and-arch-adversarial-shard
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-docs-charter-path-and-arch-adversarial-shard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-docs-charter-path-and-arch-adversarial-shard unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
phase: Phase 1 - CI health fixes
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1755910"
history:
- at: '2026-07-05T10:59:34Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/guides/contributing.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/guides/contributing.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Docs charter-path hotfix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- `main` is currently red on `fast-tests-docs` because `docs/guides/contributing.md:394` still references the retired `memory/charter.md` path. Fix the one offending line so the guard test passes.
- Success = `pytest tests/docs/test_current_charter_paths.py -q` is green, verified by running the guard — not by eyeballing the fixed line.

## Context & Constraints

- Charter: `.kittify/charter/charter.md`.
- Mission plan: `kitty-specs/ci-health-charter-path-and-arch-shard-01KWRTB2/plan.md` (Concern A / IC-01), `research.md` (R1), `spec.md` (FR-001, FR-002, Scenario A).
- This is a single-line, mechanically verified fix — R1 in `research.md` already confirmed a live grep across all four guarded roots (`docs/context`, `docs/guides`, `docs/api`, `spec-driven.md`) turns up exactly one offender. No design decisions remain.
- The canonical charter path today is `.kittify/charter/charter.md` — confirm this is what other correct references in the repo use (e.g. `docs/index.md`, `docs/llms.txt`) before writing the replacement text.
- Do **not** touch `docs/archive/1x/*` or `docs/adr/2.x/.../dual-repository-pattern.md` — these retain `.kittify/memory/charter.md` deliberately as explicit legacy/historical snapshots, out of the guarded roots and out of this WP's scope (confirmed by the post-plan brownfield squad).

## Branch Strategy

- **Strategy**: single lane, no worktree isolation required beyond the standard per-WP lane (this WP owns exactly one file, no overlap with WP02/WP03).
- **Planning base branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`
- **Merge target branch**: `tidy/ci-docs-charter-path-and-arch-adversarial-shard`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T001 – Fix the stale charter-path reference

- **Purpose**: Remove the sole surviving `memory/charter.md` reference from the guarded doc roots.
- **Steps**:
  1. Open `docs/guides/contributing.md` and locate line 394 (Development workflow numbered list, item 4):
     ```
     4. Ensure memory files (`memory/charter.md`) are updated if major process changes are made
     ```
  2. Replace the parenthetical with the canonical path. Keep the surrounding sentence's intent (updating the charter when major process changes happen) — only the path reference is stale, not the guidance itself. Suggested replacement:
     ```
     4. Ensure the project charter (`.kittify/charter/charter.md`) is updated if major process changes are made
     ```
  3. Re-read the full numbered list (items 1-4, lines ~391-394) to confirm the replacement reads naturally in context.
- **Files**: `docs/guides/contributing.md` (one line changed).
- **Parallel?**: N/A — single subtask block, sequential with T002.
- **Notes**: Do not rename "memory files" to something else if it changes meaning elsewhere in the doc — check whether "memory files" as a phrase appears elsewhere in `contributing.md` with a different (still-valid) meaning before deciding whether to keep or drop that phrase. If in doubt, keep the sentence structure and only swap the path.

### T002 – Verify via the guard itself, not inspection

- **Purpose**: Prove zero offenders remain across all four guarded roots — the spec's exception clause explicitly requires verifying via the guard, not by checking the one known line.
- **Steps**:
  1. Run the guard test:
     ```bash
     pytest tests/docs/test_current_charter_paths.py -q
     ```
     Expect: 1 passed.
  2. As a belt-and-suspenders sanity check, re-grep the four guarded roots directly:
     ```bash
     grep -rn "memory/charter.md" docs/context docs/guides docs/api spec-driven.md
     ```
     Expect: no output (empty).
  3. Record both outcomes in the Activity Log below.
- **Files**: none changed (verification only).
- **Parallel?**: No — depends on T001.
- **Notes**: If the guard still fails after T001, do not assume a second offender exists in a file you haven't checked — the test failure output lists every offending path; read it and fix exactly what it names.

## Test Strategy

- `pytest tests/docs/test_current_charter_paths.py -q` is the mandatory, sufficient test for this WP. No new tests are needed — the guard already exists and already covers the exception clause (all four roots, both `memory/charter.md` and `.kittify/memory/charter.md` substrings).

## Risks & Mitigations

- **Risk**: Rewriting the sentence changes meaning or breaks a cross-reference elsewhere in the doc. **Mitigation**: keep the edit minimal (path substring only) unless the surrounding sentence genuinely reads wrong afterward.
- **Risk**: A second, previously-unnoticed offender surfaces once the guard runs. **Mitigation**: T002 runs the guard (not a manual grep-and-trust) precisely to catch this; if it happens, fix the newly-named file(s) too before marking this WP done.

## Review Guidance

- Confirm the guard test output is included in the Activity Log (pass, not just claimed).
- Confirm the diff touches only `docs/guides/contributing.md` and only the one line/sentence.
- Confirm no legacy/archive doc was touched (out of scope, per Context & Constraints above).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-05T10:59:34Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
- 2026-07-05T11:27:35Z – claude:opus:python-pedro:implementer – shell_pid=1743821 – Assigned agent via action command
- 2026-07-05T11:31:22Z – claude:opus:python-pedro:implementer – shell_pid=1743821 – T001 done: edited docs/guides/contributing.md line 394, replacing 'Ensure memory files (memory/charter.md) are updated...' with 'Ensure the project charter (.kittify/charter/charter.md) is updated...'. T002 done: pytest tests/docs/test_current_charter_paths.py -q -> 1 passed in 42.57s; grep -rn memory/charter.md across docs/context docs/guides docs/api spec-driven.md -> empty (zero offenders). Diff scoped to docs/guides/contributing.md only. Committed as 599c949f3.
- 2026-07-05T11:31:29Z – claude:opus:python-pedro:implementer – shell_pid=1743821 – Ready for review: fixed stale charter-path reference, guard test passes, zero offenders confirmed across all 4 guarded roots
- 2026-07-05T11:31:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=1755910 – Started review via action command
- 2026-07-05T11:36:19Z – user – shell_pid=1755910 – Review passed: diff scoped to single line in docs/guides/contributing.md, canonical .kittify/charter/charter.md path confirmed, pytest tests/docs/test_current_charter_paths.py -q -> 1 passed (verified live), grep memory/charter.md across guarded roots empty (verified live), archive/1x and dual-repository-pattern ADR untouched, FR-001/FR-002 satisfied. Filled issue-matrix.md verdicts (#2397 in-mission, #2391 verified-already-fixed) to unblock the FR-037 approval gate.

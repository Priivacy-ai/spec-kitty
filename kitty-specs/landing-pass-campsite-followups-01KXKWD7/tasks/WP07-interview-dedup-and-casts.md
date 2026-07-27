---
work_package_id: WP07
title: Interview-helper de-dup + config-verified casts (#2675)
dependencies: []
requirement_refs:
- C-001
- FR-010
- NFR-003
- NFR-005
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T060
- T061
- T062
phase: Phase 2 - Type-debt disjoint
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3700776"
shell_pid_created_at: "1784158387.03"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/plan/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/missions/plan/specify_interview.py
- src/specify_cli/missions/plan/plan_interview.py
- src/specify_cli/widen/interview_helpers.py
- src/specify_cli/missions/_read_path_resolver.py
- src/specify_cli/status/emit.py
- src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Interview-helper de-dup + config-verified casts (#2675)

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

De-duplicate the byte-identical `decision_id` interview block — the block whose stored-bool
narrowing causes an identical `str | None → str` mypy error in **both** interview files — into a
single shared narrow-once helper, and drop the three in-scope config-verified redundant casts.

This WP is part of #2675 and is **disjoint from the Lane work**, so it is a safe parallel lane —
it shares no `owned_files` with the sibling WPs.

**Complete when:**

- The `decision_id` block lives in exactly ONE shared home at
  `src/specify_cli/widen/interview_helpers.py` (not a copy per interview file). The duplication is
  gone.
- Both `specify_interview.py` and `plan_interview.py` route through that shared seam, and mypy
  carries the `None` narrowing through to the `render_already_widened_prompt(decision_id: str)`
  call — so **both** interview-file `str | None → str` errors disappear.
- The three redundant casts are dropped, their stale `follow_imports=skip` rationale comments are
  deleted **together with** the casts, and any now-unused `cast` import is removed.
- `uv run mypy` over all six owned files reports **0 errors** with **0 new suppressions**
  (no new `# type: ignore`, no new `[[tool.mypy.overrides]]`).
- Existing interview tests still pass.

## Context & Constraints

Governing docs: `.kittify/charter/charter.md`,
`kitty-specs/landing-pass-campsite-followups-01KXKWD7/plan.md` (IC-06),
`kitty-specs/landing-pass-campsite-followups-01KXKWD7/tasks.md`,
`research-notes-csf-2670.md`.

Binding constraints:

- **RED-FIRST (C-005)** — a failing gate/test must exist and be seen failing BEFORE the fix.
- **fix-not-suppress (C-001)** — resolve the type error by fixing the code, never by adding a
  suppression, per-file ignore, or override.

Verified facts from research (confirm each against the live tree before acting — line numbers
and file locations may have drifted):

- `src/specify_cli/missions/plan/specify_interview.py:181` and
  `src/specify_cli/missions/plan/plan_interview.py:181` each pass `current_decision_id`
  (type `str | None`) into `render_already_widened_prompt(decision_id: str)`.
- The `is not None` guard **exists**, but its result is captured into an intermediate bool
  (`_already_widened`). mypy cannot carry a narrowing through a stored bool, so the narrowing
  is lost and both call sites raise `str | None → str`.
- The two files carry **byte-identical** blocks (~lines 175–185). This is logical duplication:
  the same latent bug lives in both, which is exactly why a shared seam — not two parallel
  patches — is the correct fix.
- **The canonical helper ALREADY EXISTS at `src/specify_cli/widen/interview_helpers.py`.**
  `render_already_widened_prompt` is defined there (around line 224), and BOTH interview files
  already import it —
  `from specify_cli.widen.interview_helpers import render_already_widened_prompt, run_end_of_interview_pending_pass`
  at `specify_interview.py:110` and `plan_interview.py:110`. This WP **EDITS** that existing file
  to add the narrow-once consolidation — it does **NOT** create a new helper, and there is no
  `create_intent`. **Do NOT create a duplicate seam.** During implementation, trace first to
  confirm the existing home (`src/specify_cli/widen/interview_helpers.py`) and the duplicated
  block, then consolidate INTO that existing helper.

Three config-verified redundant-cast drops:

- `src/specify_cli/missions/_read_path_resolver.py:1473` — cast to `Path`.
- `src/specify_cli/status/emit.py:302` — cast to `tuple[int, int]`.
- `src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py:78` — cast to `str`.

**CAUTION on the casts:**

- The `_read_path_resolver.py` and `emit.py` casts carry inline rationale comments tying them to
  `pyproject.toml [[tool.mypy.overrides]] follow_imports=skip`. A **different** mypy config can
  flip `redundant-cast` into `no-any-return` — so **reproduce the `redundant-cast` verdict under
  the CANONICAL mypy invocation** (below) BEFORE dropping any cast.
- When you drop a cast, **delete the now-stale rationale comment together with it** — do not leave
  an orphaned `follow_imports=skip` justification pointing at code that no longer exists.
- After removing casts, **watch for a now-unused `cast` import** in each touched module and remove
  it if nothing else in the file uses `cast`.

Full detail: `research-notes-csf-2670.md`, plan IC-06.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T060 – RED: prove the narrowing error exists on both interview files

- **Purpose**: Establish the failing baseline (C-005) BEFORE any fix. Two guarantees must be
  pinned: (a) the `decision_id` narrowing error exists on **both** interview files today, and
  (b) the consolidated helper narrows **once**.
- **Steps**:
  1. Run the canonical mypy invocation (see Test Strategy) against
     `specify_interview.py` and `plan_interview.py` and capture the two `str | None → str`
     errors. This is your RED evidence — record it in the Activity Log.
  2. Add or extend a test (or, if a runtime test is impractical, a mypy-assertion note) that
     asserts the narrowing behaviour: the shared helper must narrow `str | None` to `str` a
     single time, and both interviews must be free of the error after wiring.
  3. **If a runtime test is impractical**, encode the RED as a mypy-clean gate over the two
     interview files that **currently fails** (because the errors exist) and will pass only once
     T061 lands.
- **Files**: test surface under `tests/` and/or a mypy-gate note; the two interview files as the
  gate targets.
- **Parallel?**: Must precede T061.
- **Notes**: Do not fix the code in this subtask — only make the failure visible and reproducible.

### Subtask T061 – Consolidate the `decision_id` block into one narrow-once seam

- **Purpose**: Remove the logical duplication AND both mypy errors in a single structural move.
- **Steps**:
  1. **Trace first**: confirm the existing home of `render_already_widened_prompt` and of the
     byte-identical `decision_id` block. The canonical helper ALREADY EXISTS at
     `src/specify_cli/widen/interview_helpers.py` (both interviews already import
     `render_already_widened_prompt` from it at line 110). Consolidate INTO that existing file —
     do NOT create a duplicate seam.
  2. In the existing `src/specify_cli/widen/interview_helpers.py`, add the shared narrow-once
     helper. Structure it so the `None` check gates the
     `render_already_widened_prompt(decision_id: str)` call **directly** (not via a stored bool),
     letting mypy carry the narrowing to the call.
  3. Consolidate the duplicated block from **both** interviews into that helper.
  4. Route both `specify_interview.py` and `plan_interview.py` through the shared seam; delete the
     now-dead local blocks from each.
  5. Confirm the T060 gate/test flips to GREEN and both `str | None → str` errors are gone.
- **Files**: `src/specify_cli/widen/interview_helpers.py` (EDIT the existing file),
  `src/specify_cli/missions/plan/specify_interview.py`,
  `src/specify_cli/missions/plan/plan_interview.py`.
- **Parallel?**: Depends on T060; independent of T062 (may be done in either order).
- **Notes**: The success signal is ONE seam with the narrowing done once — not two parallel
  patches that each fix a copy. Reviewer will reject a per-file duplicate fix.

### Subtask T062 – Drop the three config-verified redundant casts

- **Purpose**: Remove verified dead casts and their stale justifications.
- **Steps**:
  1. Reproduce the `redundant-cast` verdict for each of the three casts under the CANONICAL mypy
     invocation (see Test Strategy). Only drop a cast whose `redundant-cast` verdict you have
     actually observed — a different config can flip the diagnosis.
  2. Remove the cast at each site:
     - `src/specify_cli/missions/_read_path_resolver.py:1473` (cast to `Path`)
     - `src/specify_cli/status/emit.py:302` (cast to `tuple[int, int]`)
     - `src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py:78` (cast to `str`)
  3. For the `_read_path_resolver.py` and `emit.py` sites, **delete the stale
     `follow_imports=skip` rationale comment together with the cast**.
  4. In each touched module, check whether `cast` is still used; if not, remove the now-unused
     `cast` import.
- **Files**: `src/specify_cli/missions/_read_path_resolver.py`,
  `src/specify_cli/status/emit.py`,
  `src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py`.
- **Parallel?**: Independent of T060/T061.
- **Notes**: Do not touch `pyproject.toml` mypy overrides in this WP — only remove the
  now-orphaned inline rationale comments. If dropping a cast turns the line into a
  `no-any-return`, STOP: the cast was not truly redundant under canonical config — leave it and
  note the finding in the Activity Log rather than suppressing.

## Test Strategy

Canonical mypy invocation (0 errors, 0 new suppressions):

```bash
uv run mypy \
  src/specify_cli/missions/plan/specify_interview.py \
  src/specify_cli/missions/plan/plan_interview.py \
  src/specify_cli/missions/_read_path_resolver.py \
  src/specify_cli/status/emit.py \
  src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
```

- Before the fix, this run MUST show the two `str | None → str` errors on the interview files
  (T060 RED evidence).
- After T061 + T062, this run MUST report **0 errors** and introduce **0 new suppressions**.
- Existing interview tests MUST still pass — run the relevant `tests/` covering
  `specify_interview` / `plan_interview` and confirm green.
- Also run `uv run ruff check` over the six owned files to catch a stray unused `cast` import.

## Risks & Mitigations

- **Config-sensitive casts** — a non-canonical mypy config can flip `redundant-cast` into
  `no-any-return`. Mitigation: reproduce the `redundant-cast` verdict under the canonical
  invocation before dropping any cast; back out and note if the diagnosis flips.
- **Shared-helper location drift** — the canonical helper ALREADY EXISTS at
  `src/specify_cli/widen/interview_helpers.py`; blindly creating a new one (e.g. under
  `missions/plan/widen/`) would produce a duplicate seam. Mitigation: trace and confirm the
  existing home of `render_already_widened_prompt` and the block FIRST; EDIT that existing file,
  do not create a duplicate.
- **Orphaned rationale comments** — dropping a cast but leaving its `follow_imports=skip`
  justification produces stale, misleading provenance. Mitigation: delete the comment with the
  cast in the same edit.
- **Unused import residue** — removing the last `cast` in a module leaves an unused import that
  trips ruff. Mitigation: audit `cast` usage per module and remove the import if orphaned.

## Review Guidance

- Verify ONE shared narrow-once seam in the existing `src/specify_cli/widen/interview_helpers.py`
  (no new duplicate helper created) — reject any per-file duplicate patch that fixes two copies
  instead of consolidating.
- Confirm the `None` check gates the `render_already_widened_prompt` call directly (mypy carries
  the narrowing), not via a stored bool.
- Confirm the stale `follow_imports=skip` rationale comments were deleted **with** the casts, and
  that no now-unused `cast` import remains.
- Confirm **0 new suppressions** were introduced (no new `# type: ignore`, no new
  `[[tool.mypy.overrides]]`).
- Confirm the RED evidence (both interview-file errors pre-fix) is recorded and now GREEN.

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

**Why this matters**: The acceptance system reads the LAST activity log entry as the current
state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-15T22:32:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

### Optional Phase Subdirectories

For large features, organize prompts under `tasks/` to keep bundles grouped while maintaining lexical ordering.
- 2026-07-15T23:17:23Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Assigned agent via action command
- 2026-07-15T23:32:26Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – T060-T062 done. T061: consolidated the byte-identical decision_id block into a new resolve_already_widened_prompt() narrow-once seam in widen/interview_helpers.py; both specify_interview.py and plan_interview.py now route through it (local _is_already_widened duplicates removed). RED confirmed via git-stash before/after: 2x str|None->str arg-type errors on specify_interview.py:181/plan_interview.py:181 under mypy including widen/interview_helpers.py explicitly on the command line (required — the blanket specify_cli.* follow_imports=skip override otherwise hides the bug when the helper is only imported). GREEN after fix: 0 errors on all 3 files. T062: only the _read_path_resolver.py:1473 cast was genuinely redundant (confirmed via RED/GREEN mypy) and was dropped along with its rationale comment and the now-unused cast import. IMPORTANT FINDING: the emit.py:302 and m_2_1_4_enforce_command_file_state.py:78 casts are NOT redundant under canonical mypy -- removing either flips it to a no-any-return error (verified by temporarily removing each and re-running mypy), matching the WP's own STOP condition in T062 Notes. Left both casts + their follow_imports=skip rationale comments in place; no suppression added. Net: mypy over the 6 owned files went from 11 errors to 8 (all 8 remaining are pre-existing emit.py/m_2_1_4 no-any-return/misc errors unrelated to any in-scope cast or the decision_id block -- out of scope for T060-T062). Added 2 new RED-first mypy-gate regression tests: tests/specify_cli/widen/test_interview_decision_id_narrowing_gate.py and tests/specify_cli/missions/test_read_path_resolver_redundant_cast_gate.py. ruff check clean on all changed files. Full interview test suite green (uv run pytest tests/ -k interview -q -> 173 passed).
- 2026-07-15T23:33:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=3700776 – Started review via action command
- 2026-07-15T23:41:28Z – user – shell_pid=3700776 – Review passed (code): decision_id narrow-once seam consolidated into existing widen/interview_helpers.py; 3 in-scope mypy errors cleared (baseline 11->8 pre-existing); 2 retained casts verified load-bearing (flip to no-any-return); 0 new suppressions; ruff clean; 2 RED-first gate tests + 421 runtime tests green.

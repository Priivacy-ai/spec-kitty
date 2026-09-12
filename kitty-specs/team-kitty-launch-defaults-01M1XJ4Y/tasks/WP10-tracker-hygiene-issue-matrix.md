---
work_package_id: WP10
title: Tracker hygiene and issue matrix
dependencies:
- WP09
requirement_refs:
- C-006
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
phase: Phase 4 - Hygiene
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: planner-priti
authoritative_surface: kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/
create_intent:
- kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json
execution_mode: planning_artifact
model: ''
owned_files:
- kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json
- kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/traces/tooling-friction.md
- kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/traces/approach.md
- kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/traces/design-decisions.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP10 – Tracker hygiene and issue matrix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `planner-priti`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
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

## Read Before Anything Else

- `docs/context/team-kitty.md` — the hosted model. "Sync" is a retired transport; the live thing is Zeitgeist. Never phrase code, docs, tests, or commit messages in sync vocabulary.
- `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/spec.md`, `plan.md` (Implementation Concern Map), `research.md`, `data-model.md`, `contracts/*.md`, `occurrence_map.yaml`.
- `.kittify/charter/charter.md` §Quality standing orders: red-first through the pre-existing entry point (DIRECTIVE_041), campsite-clean the surfaces you touch first, canonical sources only, terminology canon.
- Test policy in `CLAUDE.md`: `make test-fast` baseline plus the test files of every module you touch; `tests/architectural/` in full when you touch `core/env.py`, `tests/conftest.py`, or any registry.

## Objectives & Success Criteria

- `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json` exists with a row per issue this mission claims (#1621, #3980, #2875, #2695) and per issue it references without closing (#3154, #3892, #3277), each with `verdict`, `evidence_ref` (commit or test id from WP09), `fr`/`nfr`/`sc`, and `wp`.
- Each claimed issue carries a GitHub comment naming the mission and is assigned to the Human-in-Charge (DIR-012); the referenced issues carry a pointer comment.
- Tracer files under `traces/` carry the implementation-phase entries.

## Context & Constraints

- Shape: copy the field set from an existing matrix, e.g. `kitty-specs/accept-path-remediation-honesty-01M0TWZP/issue-matrix.json` (`rows` keyed by `#n` with `evidence_ref, fr, nfr, repo, sc, scope, source_file, title, verdict, wp`).
- Charter mission hygiene: "every addressed issue gets an issue-matrix row + claim + tracker comment naming the mission"; `Pre-existing Failure Reporting Rule`.
- GitHub access: `unset GITHUB_TOKEN; gh ...` per `CLAUDE.md`; never use `Fixes #` in PR text before the matrix verdicts are filled.
- This is a planning-artifact WP: it edits only this mission's dossier.

## Subtasks & Detailed Guidance

### Subtask T048 – Issue matrix

- **Steps**: Create the file with rows: `#1621` (closes; FR-001..FR-006, SC-001..SC-003; WP02/WP03/WP06), `#3980` (closes; execution plan; all WPs), `#2875` (closes; FR-013, SC-004; WP04/WP06/WP09), `#2695` (closes; FR-013; WP04/WP06), `#3154` (refs; C-002), `#3892` (refs), `#3277` (refs; C-004 out of scope). Fill `verdict` from WP09 evidence (`met` / `partial` / `not_met`) and `evidence_ref` with the acceptance test ids and commit SHAs.
- **Files**: `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json`.
- **Parallel?**: No.

### Subtask T049 – Claims and assignments

- **Steps**: For each claimed issue: assign the HiC (`gh issue edit <n> --add-assignee <hic-login>`) and comment "Claimed by mission team-kitty-launch-defaults-01M1XJ4Y (WP list); evidence: …". For referenced issues: comment the pointer. Record the comment URLs in the matrix `evidence_ref` or in the Activity Log.
- **Parallel?**: Yes.

### Subtask T050 – Tracer files

- **Steps**: Append dated entries to `traces/tooling-friction.md`, `approach.md`, `design-decisions.md` from the implementation lanes' Activity Logs (friction, approach changes, decisions); this feeds the retrospective.
- **Files**: `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/traces/*.md`.
- **Parallel?**: Yes.

## Test Strategy

- `python -c "import json; json.load(open('kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/issue-matrix.json'))"`; mission-state audit `spec-kitty doctor mission-state --audit --fail-on teamspace-blocker --mission team-kitty-launch-defaults-01M1XJ4Y`.

## Risks & Mitigations

- Claiming issues before the evidence exists creates a false record: this WP depends on WP09 and fills verdicts from its Activity Log.

## Review Guidance

- Every row has a non-`unknown` verdict and a checkable evidence ref; GitHub comments exist.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP10 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP10 --to for_review`, from the workspace the implement command gave you.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-09-07T10:00:36Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.

---
work_package_id: WP03
title: Terminology gate lock + out-of-scope preservation proof
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
- FR-005
tracker_refs: []
planning_base_branch: mission/codebase-sanitization-1060-1622
merge_target_branch: mission/codebase-sanitization-1060-1622
branch_strategy: Planning artifacts for this mission were generated on mission/codebase-sanitization-1060-1622. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/codebase-sanitization-1060-1622 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
phase: Phase 2 - Regression lock
assignee: ''
agent: claude
history:
- at: '2026-06-15T12:04:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/contract/
create_intent:
- tests/contract/test_feature_alias_scope.py
execution_mode: code_change
owned_files:
- tests/contract/test_terminology_guards.py
- tests/contract/test_feature_alias_scope.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Terminology gate lock + out-of-scope preservation proof

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Lock the removal in with a machine-enforced gate and prove the deferred
out-of-scope commands are untouched.

**Done when:**
- The terminology guard fails CI if ANY `--feature` Typer option (hidden or
  visible) is declared in one of the 10 in-scope command files.
- A regression test proves an out-of-scope command (e.g. `merge`) still accepts
  the hidden `--feature` alias.
- FR-003 is confirmed: no `src/doctrine/` source passes `--feature` to an
  in-scope command.
- Full contract + architectural suites pass.

## Context & Constraints

- Spec FR-003, FR-004, FR-005. Plan IC-01. Research R4.
- **Depends on WP01 + WP02** — only run once both removals are merged, otherwise
  the new in-scope rule is red.
- Keep the EXISTING global rule (`test_no_visible_feature_alias_in_cli_commands`:
  `--feature` must be `hidden=True`) intact for the out-of-scope files — do not
  weaken it.
- Do NOT touch `src/` command code here (that's WP01/WP02). This WP is tests-only.

## Branch Strategy

- **Strategy**: lane-per-WP from `lanes.json`
- **Planning base branch**: `mission/codebase-sanitization-1060-1622`
- **Merge target branch**: `mission/codebase-sanitization-1060-1622`
- **Implement command**: `spec-kitty agent action implement WP03 --agent claude --base mission/codebase-sanitization-1060-1622`
  — `--base` REQUIRED (stale `mission_branch` in `lanes.json`; flatten note).

## Subtasks & Detailed Guidance

### Subtask T013 – In-scope absent-rule
- **Purpose**: Forbid the alias entirely on the in-scope cluster.
- **Steps**: In `tests/contract/test_terminology_guards.py`, add a new test (e.g.
  `test_no_feature_alias_in_internal_command_cluster`) that, for the explicit list
  of in-scope files, fails if the literal `--feature` appears **anywhere** in the
  file (NOT only inside `typer.Option` blocks). This is critical: a residual
  `alias_flag="--feature"` inside a `resolve_selector(...)` call is not a Typer
  block but IS a forbidden survivor — it must fail this gate, matching the
  occurrence_map `acceptance_check` (`git grep -- '--feature' <files>` → 0).
  Define the in-scope list as a module constant.
- **Files**: `tests/contract/test_terminology_guards.py`
- **Scope note**: the in-scope list is `agent/{status,tasks,workflow,context}.py`
  + `charter/lint.py` + `materialize.py` + `validate_encoding.py` +
  `validate_tasks.py` + `verify.py`. **`agent/mission.py` has no `--feature`
  option** (only a help string fixed in WP01) — you MAY include it (post-WP01 it
  is clean) but the out-of-scope user-facing commands must NOT be in the list
  (they still legitimately carry the hidden alias). Keep the existing global
  `test_no_visible_feature_alias_in_cli_commands` (hidden-only rule) intact for
  those.

### Subtask T014 – Out-of-scope preservation regression
- **Purpose**: Prove FR-005 (no regression to deferred commands).
- **Steps**: Add `tests/contract/test_feature_alias_scope.py` with a test that
  invokes an out-of-scope command with `--feature` (e.g. `merge --feature <slug>`
  via the Typer CliRunner or an arg-parse assertion) and asserts the alias is
  still accepted and resolves to the same value as `--mission` (canonical wins on
  conflict). Keep it loopback/offline — no network.
- **Files**: `tests/contract/test_feature_alias_scope.py`

### Subtask T015 – FR-003 first-party-caller check
- **Purpose**: Confirm no first-party source passes `--feature` to an in-scope
  command.
- **Steps**: Either add an assertion in `test_feature_alias_scope.py` that greps
  `src/doctrine/` for `--feature` invocations of in-scope commands and expects
  none, OR document the manual confirmation in the WP activity log citing
  research.md R3 (the 3 existing `src/doctrine/` hits are out-of-scope-command
  prose). Prefer the automated assertion.
- **Files**: `tests/contract/test_feature_alias_scope.py`

### Subtask T016 – Suites
- **Steps**: `PWHEADLESS=1 pytest tests/contract/ tests/architectural/ -q`.
  Also confirm `tests/architectural/test_no_legacy_terminology.py` stays green.
- **Validation**:
  - [ ] In-scope gate fails when a `--feature` option is re-added to any in-scope file (verify by a temporary local re-add, then revert)
  - [ ] Out-of-scope `--feature` still resolves
  - [ ] FR-003 assertion/doc in place
  - [ ] contract + architectural suites green

## Definition of Done
- All 4 subtasks complete; gate proven (red on reintroduction, green now);
  out-of-scope preserved; suites pass.

## Reviewer Guidance
- Confirm the in-scope list is exactly the 10 files and the global hidden-only
  rule is unchanged for out-of-scope. Confirm the preservation test actually
  exercises an out-of-scope command. Confirm no `src/` command edits here.

## Activity Log

- 2026-06-15T14:41:41Z – user – Review passed (renata, off-lane consolidation): see review evidence; code on mission/
- 2026-06-15T14:41:47Z – user – Done override: Code consolidated onto mission/ (49f4b93ef + e9c311b9b); per-WP renata-approved; PR to upstream pending

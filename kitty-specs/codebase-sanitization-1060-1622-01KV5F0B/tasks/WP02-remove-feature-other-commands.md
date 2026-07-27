---
work_package_id: WP02
title: Remove --feature from non-agent in-scope commands
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-008
tracker_refs: []
planning_base_branch: mission/codebase-sanitization-1060-1622
merge_target_branch: mission/codebase-sanitization-1060-1622
branch_strategy: Planning artifacts for this mission were generated on mission/codebase-sanitization-1060-1622. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/codebase-sanitization-1060-1622 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Alias removal
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "285959"
history:
- at: '2026-06-15T12:04:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/charter/lint.py
- src/specify_cli/cli/commands/materialize.py
- src/specify_cli/cli/commands/validate_encoding.py
- src/specify_cli/cli/commands/validate_tasks.py
- src/specify_cli/cli/commands/verify.py
- tests/specify_cli/cli/commands/test_materialize.py
- tests/specify_cli/cli/commands/test_charter_lint.py
- tests/cross_cutting/encoding/test_encoding_validation_cli.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – Remove `--feature` from non-agent in-scope commands

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

Remove the hidden `--feature` alias + plumbing from `charter lint`, `materialize`,
`validate_encoding`, `validate_tasks`, and `verify`. `--mission` behavior
unchanged.

**Done when:**
- `git grep -- '--feature'` over those 5 files → 0.
- Each command still resolves `--mission`; `--feature` now errors as unknown.
- ruff + mypy clean; targeted tests green.

## Context & Constraints

- Spec FR-001, FR-002, FR-008. Plan IC-03. Bulk-edit map cs-006..010, cli-006..010.
- Mirror WP01's 3-layer removal recipe (param + `explicit_feature` + resolver
  alias args). Switch each `resolve_selector` call to the mission-only path.
- **DO NOT TOUCH** (FR-008/NFR-001): `selector_resolution.py`,
  `_legacy_aliases.py`, `status/`, `task_utils/`, `legacy_detector.py`, and the
  out-of-scope user-facing commands (`implement`, `merge`, `next_cmd`, `research`,
  `context`, `accept`, `lifecycle`, `mission_type`).
- These files have only 1–2 hits each — uniform, low-risk.

## Branch Strategy

- **Strategy**: lane-per-WP from `lanes.json`
- **Planning base branch**: `mission/codebase-sanitization-1060-1622`
- **Merge target branch**: `mission/codebase-sanitization-1060-1622`
- **Implement command**: `spec-kitty agent action implement WP02 --agent claude --base mission/codebase-sanitization-1060-1622`
  — `--base` REQUIRED (stale `mission_branch` in `lanes.json`; flatten note).

## ⚠️ The removal recipe per file (verified against code)

`resolve_selector(*, alias_value, alias_flag, ...)` has **no defaults** for the
alias kwargs — you cannot drop them, and must NOT leave `alias_flag="--feature"`.
For these single-caller commands the fix is to **remove the `resolve_selector`
call entirely and use `mission` directly**. Do NOT blindly swap to
`resolve_mission_handle` (it returns a `ResolvedMission` and `exit(2)`s on error —
different semantics).

## Subtasks & Detailed Guidance

### Subtask T007 [P] – `charter/lint.py`
- **Reality**: NO resolver — `lint.py:108` is a plain ternary
  `scope = mission if mission is not None else feature`.
- **Steps**: Remove the `feature` `--feature` option (~L84-89), delete the related
  comment (~L107), change L108 to `scope = mission`.
- **Files**: `src/specify_cli/cli/commands/charter/lint.py`

### Subtask T008 [P] – `materialize.py`
- **Steps**: Remove the `--feature` option; the single `resolve_selector` call
  (~L71-78) — drop the call and use `mission` directly (`mission_slug = mission`).
- **Files**: `src/specify_cli/cli/commands/materialize.py`

### Subtask T009 [P] – `validate_encoding.py` + `validate_tasks.py`
- **Steps**: Same single-call removal (`validate_encoding.py:79`,
  `validate_tasks.py:106`) — remove option + call, use `mission` directly.
- **Files**: `src/specify_cli/cli/commands/validate_encoding.py`,
  `src/specify_cli/cli/commands/validate_tasks.py`

### Subtask T010 [P] – `verify.py`
- **Steps**: Remove the `--feature` option + the `resolve_selector` call (~L69-78);
  use `mission` directly. The internal `feature=mission_slug` kwarg passed to
  `_run_diagnostics_mode` (~L80) is a DIFFERENT, out-of-scope param name — leave it.
- **Files**: `src/specify_cli/cli/commands/verify.py`

### Subtask T011 – Update existing tests
- **Steps**: Switch the in-scope `--feature` invocations to `--mission` in the
  owned test files (`test_materialize.py`, `test_charter_lint.py`,
  `tests/cross_cutting/encoding/test_encoding_validation_cli.py`) and confirm
  `--mission` still passes. **Do not create new test files here** — the
  behavioral `--feature`-rejection proof for all 10 in-scope commands is
  centralized in WP03 (`test_feature_alias_scope.py`). If `validate_tasks`/`verify`
  have no `--feature` test today, no test edit is needed for them beyond the
  removal itself.
- **Files**: the three owned test files above.

### Subtask T012 – Gates
- **Steps**: ruff + mypy on changed files; run the targeted tests.
- **Validation**:
  - [ ] `git grep -- '--feature'` over the 5 command files → 0
  - [ ] resolver / `_legacy_aliases.py` / out-of-scope commands untouched
  - [ ] ruff + mypy clean; targeted tests green

## Definition of Done
- All 6 subtasks complete; validation passes; no out-of-scope edits.

## Reviewer Guidance
- Confirm zero `--feature` in the 5 files, `--mission` unchanged, FR-008 surfaces
  intact, tests prove rejection + `--mission`.

## Activity Log

- 2026-06-15T13:02:26Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Assigned agent via action command
- 2026-06-15T13:09:20Z – user – shell_pid=225207 – Moved to claimed
- 2026-06-15T13:09:29Z – user – shell_pid=225207 – Moved to in_progress
- 2026-06-15T13:10:48Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Ready: non-agent --feature removed; gates green
- 2026-06-15T13:14:21Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Orchestrator sync (flatten misfires lane-purity guard on planning branch); code done+green on lane branch
- 2026-06-15T13:15:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=285959 – Started review via action command
- 2026-06-15T13:20:09Z – user – shell_pid=285959 – Review passed (renata): all 6 criteria met — no residual --feature/alias_flag, resolve_selector calls removed, charter/lint ternary→scope=mission, NFR-001 surfaces untouched, 33 tests green, mypy untyped-decorator pre-existing. Lane-purity guard false-positive forced.
- 2026-06-15T14:41:46Z – user – shell_pid=285959 – Done override: Code consolidated onto mission/ (49f4b93ef + e9c311b9b); per-WP renata-approved; PR to upstream pending

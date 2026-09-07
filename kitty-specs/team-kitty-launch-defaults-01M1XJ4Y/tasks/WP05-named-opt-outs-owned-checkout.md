---
work_package_id: WP05
title: Named opt-outs and owned-checkout moves
dependencies: []
requirement_refs:
- C-002
- FR-007
- FR-008
- FR-011
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 1 - Switches
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/env.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/env.py
- src/specify_cli/status/adapters.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/charter/offering/skills/spk-run-implement-review/SKILL.md
- docs/api/skills/spk-run-implement-review.md
- tests/specify_cli/core/test_env.py
- tests/specify_cli/cli/commands/agent/conftest.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/help/move-task.help
- tests/integration/test_owned_checkout_mark_status.py
- tests/integration/test_explicit_checkout_commands.py
- tests/next/test_internal_runtime_coverage.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Named opt-outs and owned-checkout moves

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
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

- `core/env.py` exposes `is_pre_review_gate_skipped()` (reads `SPEC_KITTY_SKIP_PRE_REVIEW_GATE`) and `moment_handlers_disabled()` (reads `SPEC_KITTY_NO_MOMENT_HANDLERS`); `SYNC_DISABLE_ENV_VARS` and `first_set_sync_disable_env` are deleted.
- `status/adapters.py` registers moment handlers at import unless `moment_handlers_disabled()`.
- `agent tasks move-task` skips the pre-review gate on `--skip-pre-review-gate` or the new env name; help text says so.
- Owned-checkout `move-task` and `mark-status` never refuse because hosted features are present: `OWNED_SYNC_UNSUPPORTED` is gone, and an owned move with a resolvable fake capability fans out exactly once.

## Context & Constraints

- `src/specify_cli/core/env.py`: `SYNC_DISABLE_ENV_VARS` tuple and `first_set_sync_disable_env(environ=None)`; consumers: `cli/commands/agent/tasks_move_task.py::_mt_pre_review_gate_env_disable_reason` (~1204–1210) and `core/saas_sync_config.py::sync_active` (deleted by WP04 — do not touch that module here).
- `src/specify_cli/status/adapters.py:358–365`: import tail `if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")): ensure_zeitgeist_moment_handlers()`; comments reference the deleted sync package.
- `tasks_move_task.py::_mt_preflight_owned_request` (~359–372) raises `ActionContextError("OWNED_SYNC_UNSUPPORTED", …)` when `sync_active()`; `tasks_mark_status.py` (~182–188) has the twin. Delete both branches and their imports.
- `agent/tasks.py` (~720–731): `--skip-pre-review-gate` help mentions the retired names; `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/help/move-task.help` pins the help text.
- Tests: `tests/specify_cli/core/test_env.py` (asserts the tuple), `tests/specify_cli/cli/commands/agent/conftest.py` and `test_tasks_move_task_pre_review_gate_observability.py` (opt-out behavior), `tests/next/test_internal_runtime_coverage.py` (references the import gate), `tests/integration/test_owned_checkout_mark_status.py` and `test_explicit_checkout_commands.py` (owned checkout flows).
- Vocabulary (C-002): the two new names are final; no `SYNC_` anywhere.

## Subtasks & Detailed Guidance

### Subtask T020 – Red-first tests

- **Purpose**: Witness the old names being honored and the owned-checkout refusal.
- **Steps**:
  1. `tests/specify_cli/core/test_env.py`: replace the tuple assertions with tests for the two accessors (truthy grammar via `is_truthy`; unset → False; `environ` injection kept for testability).
  2. `tests/integration/test_owned_checkout_mark_status.py` / `test_explicit_checkout_commands.py`: with a monkeypatched `fire_saas_fanout` recorder and a resolvable credential stub (see `tests/zeitgeist_client/test_resolution.py` fakes), an owned-checkout `move-task --to for_review` and `mark-status` succeed and the recorder sees exactly one call; on the base these raise `OWNED_SYNC_UNSUPPORTED` once the flag is armed — arm it in the red run via the still-existing name, and note in the Activity Log that the arming line is removed when WP04 lands.
  3. `test_tasks_move_task_pre_review_gate_observability.py`: `SPEC_KITTY_SKIP_PRE_REVIEW_GATE=1` skips the gate with the reason text naming that variable; the old names have no effect.
- **Files**: the four test files.
- **Parallel?**: No.

### Subtask T021 – `core/env.py`

- **Purpose**: Two single-purpose accessors replace the shared tuple.
- **Steps**: Add `PRE_REVIEW_GATE_SKIP_ENV_VAR = "SPEC_KITTY_SKIP_PRE_REVIEW_GATE"`, `MOMENT_HANDLERS_DISABLED_ENV_VAR = "SPEC_KITTY_NO_MOMENT_HANDLERS"`, `is_pre_review_gate_skipped(environ=None) -> bool`, `moment_handlers_disabled(environ=None) -> bool`; delete the tuple and the old accessor; update the module docstring; keep `__all__` in sync (dead-symbol gate).
- **Files**: `src/specify_cli/core/env.py`.
- **Parallel?**: No.

### Subtask T022 – `status/adapters.py`

- **Purpose**: The import gate has an honest name.
- **Steps**: Replace the import-tail condition with `if not moment_handlers_disabled(): ensure_zeitgeist_moment_handlers()`; rewrite the comment block (~356–363) and the module docstring lines that reference the deleted sync package / daemon (~41–42, ~80) in Zeitgeist terms; keep behavior otherwise identical. Run `tests/status/` and `tests/next/test_internal_runtime_coverage.py`.
- **Files**: `src/specify_cli/status/adapters.py`.
- **Parallel?**: Yes, after T021.

### Subtask T023 – Owned-checkout refusals and the gate opt-out

- **Purpose**: FR-007/FR-008 and the re-key.
- **Steps**:
  1. `tasks_move_task.py`: in `_mt_preflight_owned_request`, delete the `sync_active()` import and the `OWNED_SYNC_UNSUPPORTED` raise; keep `require_unstaged_index` and the lane checks. In `_mt_pre_review_gate_env_disable_reason`, return `f"{PRE_REVIEW_GATE_SKIP_ENV_VAR} is set"` when `is_pre_review_gate_skipped()`; update the docstrings (#2573 references stay).
  2. `tasks_mark_status.py`: delete the twin refusal (~182–188) and its import.
  3. `git grep OWNED_SYNC_UNSUPPORTED` → empty (also in `docs/`; leave docs to WP08 but list hits in the Activity Log).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`, `src/specify_cli/cli/commands/agent/tasks_mark_status.py`.
- **Parallel?**: No.

### Subtask T024 – Help text and agent test fixtures

- **Purpose**: Operator-facing text and fixtures follow.
- **Steps**: `agent/tasks.py` help for `--skip-pre-review-gate`: "also honored via SPEC_KITTY_SKIP_PRE_REVIEW_GATE"; regenerate/edit `move-task.help`; update `tests/specify_cli/cli/commands/agent/conftest.py` (isolation fixture that set the old names → set the two new ones where isolation is intended) and `tests/next/test_internal_runtime_coverage.py`.
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/help/move-task.help`, `tests/specify_cli/cli/commands/agent/conftest.py`, `tests/next/test_internal_runtime_coverage.py`.
- **Parallel?**: Yes, after T021.

### Subtask T025 – Skill and skill doc

- **Purpose**: The implement-review skill tells orchestrators the right name.
- **Steps**: `src/charter/offering/skills/spk-run-implement-review/SKILL.md` (~28–40) and `docs/api/skills/spk-run-implement-review.md`: the process-wide opt-out is `SPEC_KITTY_SKIP_PRE_REVIEW_GATE`; remove the "legacy-compatible gate opt-outs" sentence. Run `tests/docs/` subset and `tests/architectural/test_no_legacy_terminology.py`.
- **Files**: the two files.
- **Parallel?**: Yes.

## Test Strategy

- Red-first files above; blast radius `tests/specify_cli/core/ tests/specify_cli/cli/commands/agent/ tests/status/ tests/next/ tests/integration/test_owned_checkout_mark_status.py tests/integration/test_explicit_checkout_commands.py` plus `make test-fast`; `tests/architectural/` full because `core/env.py` is cross-cutting.

## Risks & Mitigations

- Per-test isolation that relied on the old names silently stops isolating: the conftest update in T024 is mandatory, and WP04's guard catches stragglers.
- The dead-symbol gate (`tests/architectural/test_no_dead_symbols.py`) tracks `env.py` exports: update `__all__` and its census if it lists the deleted names.

## Review Guidance

- Both refusals deleted; owned-checkout fan-out test present and red-first.
- Grep proves no `SYNC_DISABLE`/`MINIMAL_IMPORT` remains under `src/specify_cli/core`, `status/adapters.py`, `cli/commands/agent/`.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP05 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP05 --to for_review`, from the workspace the implement command gave you.

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

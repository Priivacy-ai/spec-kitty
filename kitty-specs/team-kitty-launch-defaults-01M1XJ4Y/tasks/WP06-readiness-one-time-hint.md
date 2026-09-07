---
work_package_id: WP06
title: Readiness always on, one-time sign-in hint
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-010
- FR-013
- NFR-003
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
phase: Phase 1 - Switches
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/readiness/
create_intent:
- src/specify_cli/readiness/hint_state.py
- tests/readiness/test_hint_state.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/readiness/coordinator.py
- src/specify_cli/readiness/render.py
- src/specify_cli/readiness/hint_state.py
- src/specify_cli/readiness/__init__.py
- src/specify_cli/cli/helpers.py
- src/specify_cli/cli/commands/_auth_logout.py
- tests/readiness/test_auth_coordinator_matrix.py
- tests/readiness/test_coordinator_suppression_matrix.py
- tests/readiness/test_coordinator_caching.py
- tests/readiness/test_coordinator_nag_passthrough.py
- tests/readiness/test_auth_renderer.py
- tests/readiness/test_hint_state.py
- tests/cli/commands/test_auth_logout.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Readiness always on, one-time sign-in hint

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

- `readiness/coordinator.py` has no "disabled" path and no import of the enable gate; every invocation runs the auth probe.
- A machine with no session (`AuthStatus.NOT_IN_TEAMSPACE`) sees one non-blocking sign-in hint, once per machine, only when the output policy is interactive; JSON, `--quiet`, `--help`, `--version`, and non-TTY invocations print nothing new.
- `LOGGED_OUT_IN_TEAMSPACE` guidance (connected team, logged out) is unchanged.
- `auth logout` resets the hint marker.

## Context & Constraints

- Identifiers such as `AuthStatus.LOGGED_OUT_IN_TEAMSPACE`, `NOT_IN_TEAMSPACE`, and the stderr line `logged_out_on_connected_teamspace` are compatibility identifiers (#3154); keep them verbatim — the canonical prose term is "team workspace".
- `src/specify_cli/readiness/coordinator.py::_evaluate_uncached` (~225–300): the disabled branch returns `enabled=False` and only invokes the legacy nag; the enabled branch probes, renders guidance only for `LOGGED_OUT_IN_TEAMSPACE`, then `_invoke_upgrade_ux`. `AuthStatus` enum at ~50.
- `readiness/render.py::render_auth_guidance` renders the connected-team case for INTERACTIVE and NON_INTERACTIVE policies; the structured stderr line `logged_out_on_connected_teamspace` must stay byte-identical (CI classifies on it).
- `cli/helpers.py::_render_nag_if_needed` (~173–240) is the compat nag with its own `NagCache`; do not reuse it for the hint — the hint has different semantics (once per machine, reset on logout). Put the marker in a new small module `readiness/hint_state.py` using the runtime state root (`get_runtime_root()` / the same root the stored session uses) and an atomic write (`core/atomic.py` has `atomic_write`).
- `_auth_logout.py` (~79–86) clears the session via `tm.clear_session()`; reset the marker right after, best-effort (never fail logout because the marker could not be removed).
- Tests: `tests/readiness/test_auth_coordinator_matrix.py`, `test_coordinator_suppression_matrix.py`, `test_coordinator_caching.py`, `test_coordinator_nag_passthrough.py`, `test_auth_renderer.py`, `tests/cli/commands/test_auth_logout.py`.

## Subtasks & Detailed Guidance

### Subtask T026 – Red-first readiness tests

- **Purpose**: Pin the hint contract and the always-on coordinator.
- **Steps**:
  1. Coordinator matrix: with no flag set at all, `evaluate_readiness` returns `enabled=True, ran=True` (today returns the disabled result).
  2. Hint: `NOT_IN_TEAMSPACE` + INTERACTIVE → one hint line on stderr; second call in a new process with the marker present → nothing; MACHINE_OUTPUT / NON_INTERACTIVE / help / version → nothing; `LOGGED_OUT_IN_TEAMSPACE` unchanged.
  3. `test_auth_logout.py`: after logout the marker file is absent; logout still succeeds if the marker removal raises.
  4. Use an isolated runtime root fixture (the readiness tests already isolate `SPEC_KITTY_HOME`).
- **Files**: the readiness test files and `tests/cli/commands/test_auth_logout.py`.
- **Parallel?**: No.

### Subtask T027 – `readiness/hint_state.py`

- **Purpose**: One tiny, testable state holder.
- **Steps**: `hint_marker_path() -> Path` under the runtime state root (e.g. `<root>/readiness/sign-in-hint.json`), `hint_was_shown() -> bool`, `record_hint_shown(now) -> None` (atomic write of `{"shown_at": iso}`), `reset_hint() -> None` (remove, ignore missing). Never raise to callers: wrap I/O and degrade to "not shown"/"no-op". Add it to the package `__all__` if the package exports.
- **Files**: `src/specify_cli/readiness/hint_state.py` (new, ~60 lines).
- **Parallel?**: No.

### Subtask T028 – Coordinator

- **Purpose**: FR-005/FR-006/FR-013.
- **Steps**:
  1. Delete the `is_saas_sync_enabled` import and the disabled branch; `AuthStatus.DISABLED` stays in the enum for compatibility but is no longer produced (document it like `NOT_CHECKED`).
  2. After the probe: if `auth_status == NOT_IN_TEAMSPACE` and `output_policy == INTERACTIVE` and not help/version and `not hint_was_shown()`: render the hint (T029) and `record_hint_shown(now_utc())`. Keep the `LOGGED_OUT_IN_TEAMSPACE` block as is.
  3. Everything remains exception-wrapped; the coordinator never raises.
  4. Update the module and function docstrings (WS1/WS2/WS3 history stays; "hosted-enabled path" wording goes).
- **Files**: `src/specify_cli/readiness/coordinator.py`.
- **Parallel?**: No.

### Subtask T029 – Renderer

- **Purpose**: One sentence, stderr, no color when not a TTY.
- **Steps**: Add `render_sign_in_hint(command_name)` to `readiness/render.py`: e.g. `Team Kitty: run 'spec-kitty auth login' to share moments with your team (shown once).` on stderr via the CLI console; NON_INTERACTIVE and MACHINE_OUTPUT policies are never called for the hint (coordinator guards), but the function itself must be a no-op for them too.
- **Files**: `src/specify_cli/readiness/render.py`.
- **Parallel?**: Yes, after T027.

### Subtask T030 – Logout reset and helpers cleanup

- **Purpose**: `auth logout` is the off switch; the hint returns on the next interactive run.
- **Steps**: In `_auth_logout.py` after `tm.clear_session()` succeeds, call `reset_hint()` (best-effort). In `cli/helpers.py` replace the comment at ~267–276 ("First-gated on is_saas_sync_enabled(); no-ops when hosted mode is disabled") with the always-on description; no behavior change there.
- **Files**: `src/specify_cli/cli/commands/_auth_logout.py`, `src/specify_cli/cli/helpers.py`.
- **Parallel?**: Yes, after T027.

## Test Strategy

- Red-first in `tests/readiness/`; blast radius `tests/readiness/ tests/cli/commands/test_auth_logout.py tests/cli/test_top_level_group_empty_invocation.py` plus `make test-fast`.

## Risks & Mitigations

- The coordinator now runs the auth probe for every command on every machine: the probe is local-only (session file read); confirm no network call is introduced (`tests/readiness/test_auth_probe.py`).
- Concurrent first runs print the hint twice: acceptable; the marker write is atomic so the state converges.

## Review Guidance

- No disabled path remains; `AuthStatus.DISABLED` is not produced.
- Hint suppression matrix covered by tests; the structured `logged_out_on_connected_teamspace` line is byte-identical to before.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP06 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP06 --to for_review`, from the workspace the implement command gave you.

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

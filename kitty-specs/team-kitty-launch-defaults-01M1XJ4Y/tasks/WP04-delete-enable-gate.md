---
work_package_id: WP04
title: Delete the enable gate
dependencies:
- WP02
- WP05
- WP06
requirement_refs:
- C-001
- FR-009
- FR-012
- FR-013
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
phase: Phase 2 - Gate removal
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/saas_sync_config.py
- src/specify_cli/tracker/feature_flags.py
- src/specify_cli/tracker/__init__.py
- src/specify_cli/cli/commands/tracker.py
- src/specify_cli/cli/commands/mission_type.py
- tests/conftest.py
- tests/e2e/conftest.py
- tests/integration/conftest.py
- tests/architectural/test_saas_sync_gate_selection_invariance.py
- tests/agent/cli/commands/test_tracker.py
- tests/agent/cli/commands/test_tracker_discover.py
- tests/agent/cli/commands/test_tracker_status.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Delete the enable gate

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

- `src/specify_cli/core/saas_sync_config.py` and `src/specify_cli/tracker/feature_flags.py` no longer exist; `git grep -n "is_saas_sync_enabled\|sync_active\|saas_sync_disabled_message\|SAAS_SYNC_ENV_VAR" src tests` is empty.
- The `tracker` command group and `mission create --from-ticket` run for everyone; when logged out they fail with the sign-in guidance (`_auth_recovery.py` structured message / readiness ladder), never with "Hosted SaaS sync is not enabled".
- The test suite arms no flag: `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/integration/conftest.py` no longer set or delete `SPEC_KITTY_ENABLE_SAAS_SYNC`; an architectural guard asserts no test sets the retired name.

## Context & Constraints

- **Order matters**: WP02 (saas_readiness), WP05 (agent tasks, env), WP06 (readiness coordinator) remove their imports first; this WP deletes the module and the remaining consumers. If any of them is not approved, stop and wait.
- Consumers to remove here: `cli/commands/tracker.py::tracker_callback` (~396–409) and `issue_search_command` (~417–420); `cli/commands/mission_type.py` (~287–295); `tracker/__init__.py` re-export; `cli/helpers.py` only if a comment references the flag (WP06 owns that file — leave a note instead of editing).
- `tests/conftest.py:230–243` sets the flag collection-wide (#3213) and `:460` in a fixture; `tests/architectural/test_saas_sync_gate_selection_invariance.py` pins that authority. Replace that test with `test_no_retired_hosted_flag_in_tests.py`-style guards (same file, rewritten): (1) `SPEC_KITTY_ENABLE_SAAS_SYNC` is not present in `os.environ` at collection; (2) no test module contains the retired name.
- Tracker tests: `tests/agent/cli/commands/test_tracker.py`, `test_tracker_discover.py`, `test_tracker_status.py` assert the disabled message; `mission create --from-ticket` tests live near `tests/specify_cli/cli/commands/` — grep `from-ticket`.
- Keep `contracts/saas_rollout.md` under `kitty-specs/082-…` untouched (archive); `core/saas_sync_config.py` cites it in its docstring, which disappears with the module.

## Subtasks & Detailed Guidance

### Subtask T015 – Red-first: guidance instead of "not enabled"

- **Purpose**: Witness the current refusal and pin the new behavior.
- **Steps**:
  1. In `tests/agent/cli/commands/test_tracker.py` (and status/discover where they assert the message): with no session and no flag, invoking `spec-kitty tracker status` must exit non-zero and print the sign-in guidance (`run spec-kitty auth login` wording produced by `_auth_recovery`/readiness), and must not contain "not enabled".
  2. Same for `mission create --from-ticket linear:PRI-1` in the mission-type command tests.
  3. Record the failing counts.
- **Files**: `tests/agent/cli/commands/test_tracker.py`, `test_tracker_discover.py`, `test_tracker_status.py`, and the `--from-ticket` test file (declare it in the Activity Log if outside the owned list).
- **Parallel?**: No.

### Subtask T016 – Remove the command gates

- **Purpose**: Hosted commands are always present; auth decides.
- **Steps**:
  1. `tracker.py`: delete the `tracker_callback` gate body (keep the callback if Typer needs it for the group; make it a no-op with a docstring "readiness and auth decide per command") and the `issue_search_command` gate; the existing `_check_readiness(...)` ladder returns the auth guidance.
  2. `mission_type.py`: delete the gate lines ~293–295; the tracker client's auth error path renders guidance.
  3. Remove the now-unused imports.
- **Files**: `src/specify_cli/cli/commands/tracker.py`, `src/specify_cli/cli/commands/mission_type.py`.
- **Parallel?**: No.

### Subtask T017 – Delete the gate module and re-export

- **Purpose**: No second reading of "is hosted on".
- **Steps**: `git rm src/specify_cli/core/saas_sync_config.py src/specify_cli/tracker/feature_flags.py`; update `src/specify_cli/tracker/__init__.py` (drop the re-export from `__all__`); `git grep` for any remaining importer and fix it (files owned by other WPs should already be clean — if not, stop and report). Run `tests/architectural/test_no_dead_symbols.py` and `test_layer_rules.py`.
- **Files**: the two deleted modules, `src/specify_cli/tracker/__init__.py`.
- **Parallel?**: No.

### Subtask T018 – Test-suite flag arming and the architectural guard

- **Purpose**: The suite must not depend on a name the product no longer knows.
- **Steps**:
  1. `tests/conftest.py`: remove the `pytest_configure` `setdefault("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")` block (~230–243) and the fixture `setenv` at ~460 (read the surrounding fixture; if it exists to simulate "hosted on", replace it with an authenticated stub or delete it if the flag was its only purpose).
  2. `tests/e2e/conftest.py` (~58–64) and `tests/integration/conftest.py` (~23): remove the `delenv`/notes.
  3. Rewrite `tests/architectural/test_saas_sync_gate_selection_invariance.py` into a guard that (a) the retired name is absent from `os.environ` at collection and (b) no file under `tests/` mentions it (allow the guard file itself); keep the #3213 history in the docstring as context for why collection-time authority mattered.
- **Files**: `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/integration/conftest.py`, `tests/architectural/test_saas_sync_gate_selection_invariance.py`.
- **Parallel?**: Yes.
- **Notes**: Guard (b) will red until WP08 finishes the fixture sweep; mark it `xfail(strict=True)` with the WP08 reference only if the mission's lane order forces it, and say so in the Activity Log.

### Subtask T019 – Witness and blast radius

- **Purpose**: Prove nothing reads the retired name.
- **Steps**: `git grep -n "SPEC_KITTY_ENABLE_SAAS_SYNC\|is_saas_sync_enabled\|sync_active(" src/ tests/` → empty except the guard; run `tests/agent/cli/commands/ tests/specify_cli/cli/commands/ tests/architectural/test_no_dead_symbols.py tests/architectural/test_layer_rules.py tests/architectural/test_no_retired_subsystems.py` and `make test-fast`; record counts.
- **Files**: none.
- **Parallel?**: No.

## Test Strategy

- Red-first in the tracker tests; full `tests/architectural/` because `tests/conftest.py` is cross-cutting.

## Risks & Mitigations

- Import-time `skipif` gates keyed on the flag elsewhere in tests (#3213 class): the new guard's file scan finds them; convert each to a session/auth-based skip or delete it.
- Deleting the module while another lane still imports it: the dependency order above prevents it; verify with `git grep` before `git rm`.

## Review Guidance

- Both modules deleted; no importer remains; tracker/from-ticket logged-out output is the sign-in guidance.
- `tests/conftest.py` sets no hosted flag; the architectural guard exists and is not vacuous (it must fail if a test file mentions the name — prove with a temporary probe in the Activity Log).

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP04 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP04 --to for_review`, from the workspace the implement command gave you.

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

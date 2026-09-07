---
work_package_id: WP03
title: Target visibility in auth commands
dependencies:
- WP02
requirement_refs:
- FR-004
- NFR-004
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Target
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/_auth_
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/_auth_saas_target.py
- src/specify_cli/cli/commands/_auth_login.py
- src/specify_cli/cli/commands/_auth_status.py
- src/specify_cli/cli/commands/_auth_whoami.py
- src/specify_cli/cli/commands/_auth_doctor.py
- tests/cli/commands/test_auth_status.py
- tests/cli/commands/test_auth_login.py
- tests/auth/test_auth_doctor_report.py
- docs/api/auth-whoami-output.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Target visibility in auth commands

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

- `auth status`, `auth whoami`, `auth doctor`, and `auth login` print one line naming the resolved hosted target and its source, e.g. `SaaS: https://team.spec-kitty.ai (packaged default)`, through the single printer in `_auth_saas_target.py`.
- The "not configured — set SPEC_KITTY_SAAS_URL (or [sync].server_url …)" branch is gone; `packaged default` is a first-class provenance.
- `--json` output of status/whoami/doctor carries `target.url` and `target.source`; no token, session, or capability value appears in any new output (NFR-004).

## Context & Constraints

- `src/specify_cli/cli/commands/_auth_saas_target.py`: `print_saas_endpoint()` resolves with `process_wide_override=False`, renders split-brain descriptively, and today prints "not configured" on `ConfigurationError`; `format_saas_provenance(target)` and `saas_source_name(target)` derive the provenance text from `ResolvedServerTarget` fields — extend them with the `source` field WP02 added.
- `_auth_login.py::login_impl` calls `resolve_server_target()` at ~line 71 before the flow; print the target line first via `print_saas_endpoint()` (or a shared helper that takes the already-resolved target so the resolver runs once).
- `_auth_status.py`, `_auth_whoami.py`, `_auth_doctor.py`: find where the SaaS line and the JSON payload are built; add `target` fields from `target.to_diagnostics_dict()` (url + source only — never the raw env/config values if they could carry secrets; they do not, but keep the payload minimal).
- Rich escaping rule (#182): every rendered URL and provenance string goes through `escape(sanitize_terminal_text(...))`.
- Tests: `tests/cli/commands/test_auth_status.py` (covers the printer), `tests/cli/commands/test_auth_login.py`, `tests/auth/test_auth_doctor_report.py`; `docs/api/auth-whoami-output.md` documents whoami output.

## Subtasks & Detailed Guidance

### Subtask T010 – Red-first visibility tests

- **Purpose**: Pin the line, the source names, and the JSON fields.
- **Steps**:
  1. `test_auth_status.py`: with an isolated `SPEC_KITTY_HOME` and no config, `auth status` output contains the packaged default URL and `packaged default`; with `[team_kitty] server_url`, contains `config.toml [team_kitty] server_url`; with the env var, contains `SPEC_KITTY_SAAS_URL`; split-brain still renders the descriptive line; `--json` has `target.url` / `target.source`.
  2. `test_auth_login.py`: the target line is printed before any flow output (use the existing login test harness that stubs the device/browser flow).
  3. `tests/auth/test_auth_doctor_report.py`: report carries the target and source.
  4. Add a redaction assertion: with `SPEC_KITTY_SAAS_TOKEN=secret-xyz` set, no rendered output contains `secret-xyz`.
- **Files**: the three test files.
- **Parallel?**: No.

### Subtask T011 – The printer

- **Purpose**: One rendering for every command.
- **Steps**:
  1. `saas_source_name(target)`: map `target.source` to `SPEC_KITTY_SAAS_URL`, `config.toml [team_kitty] server_url`, `packaged default`; `format_saas_provenance` composes the parenthetical.
  2. Delete the `except ConfigurationError` "not configured" branch and the `[sync].server_url` remedy text; keep the split-brain branch.
  3. Keep the `_SAAS_STATUS_LABEL` alignment; docstrings drop the D-5 sentences and cite the WP01 ADR.
- **Files**: `src/specify_cli/cli/commands/_auth_saas_target.py`.
- **Parallel?**: No.

### Subtask T012 – `auth login` prints the target

- **Purpose**: FR-004: the user sees where sign-in goes before it starts.
- **Steps**: In `login_impl`, print the target line (same printer) immediately after resolution and before the device/browser flow; on split-brain the existing error path stays. Headless mode prints the same line to stderr-safe console.
- **Files**: `src/specify_cli/cli/commands/_auth_login.py`.
- **Parallel?**: No.

### Subtask T013 – JSON fields and redaction

- **Purpose**: Machine consumers get the same truth.
- **Steps**: In `_auth_status.py`, `_auth_whoami.py`, `_auth_doctor.py`, add `"target": {"url": ..., "source": ...}` to the JSON payloads (and the doctor report model if typed). Run the redaction assertion from T010 and `tests/specify_cli/core/test_secret_redaction.py` unchanged.
- **Files**: `src/specify_cli/cli/commands/_auth_status.py`, `_auth_whoami.py`, `_auth_doctor.py`.
- **Parallel?**: Yes, after T011.

### Subtask T014 – Documentation of the output

- **Purpose**: `docs/api/auth-whoami-output.md` is the reference for the output shape.
- **Steps**: Document the target line and the JSON `target` object with the three source values; remove any mention of "not configured" and of `SPEC_KITTY_ENABLE_SAAS_SYNC`; keep the description within the docs gate band.
- **Files**: `docs/api/auth-whoami-output.md`.
- **Parallel?**: Yes.

## Test Strategy

- Red-first files above; blast radius `tests/cli/commands/test_auth_*.py tests/auth/ tests/specify_cli/core/test_secret_redaction.py` plus `make test-fast`; `tests/docs/` subset for the doc page.

## Risks & Mitigations

- Double resolution (login resolves, then the printer resolves again): pass the resolved target into a helper to keep one resolution per command.
- Fixture captures of terminal width (`tests/cli/commands/fixtures/render_width_3115/*`) may include the old "not configured" line; those fixtures belong to WP08's sweep — note in the Activity Log if they red.

## Review Guidance

- Exactly one place formats the target; grep for `resolved_server_url` in `cli/commands/`.
- Redaction assertion present and passing; JSON fields present on all three commands.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP03 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP03 --to for_review`, from the workspace the implement command gave you.

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

---
work_package_id: WP07
title: Provisioning, redaction, completion, env docs
dependencies:
- WP05
requirement_refs:
- C-002
- FR-011
- FR-014
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
phase: Phase 2 - Registries
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/migrations/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/upgrade/migrations/m_3_2_8_provision_kitty_env.py
- src/specify_cli/core/secret_redaction.py
- src/specify_cli/completion.py
- docs/api/environment-variables.md
- .github/workflows/ci-windows.yml
- tests/specify_cli/upgrade/migrations/test_provision_kitty_env.py
- tests/specify_cli/core/test_secret_redaction.py
- tests/specify_cli/bootstrap/test_env_file_loader.py
- tests/docs/test_env_var_scope_warning.py
- tests/specify_cli/cli/commands/test_completion_fast_path.py
- tests/specify_cli/invocation/cli/test_complete.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – Provisioning, redaction, completion, env docs

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

- `m_3_2_8_provision_kitty_env.py::GOVERNED_OPERATOR_VARS` lists `SPEC_KITTY_SKIP_PRE_REVIEW_GATE` and `SPEC_KITTY_NO_MOMENT_HANDLERS` and none of `SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_SYNC_DISABLE`, `SPEC_KITTY_SYNC_MINIMAL_IMPORT`; the migration never seeds a retired name and never invents a value.
- `core/secret_redaction.py` printable allowlist and `completion.py` env-var listing match `contracts/environment-and-config.md`.
- `docs/api/environment-variables.md` documents launch behavior: packaged default, precedence, `[team_kitty] server_url`, the two opt-outs, and that authentication is the switch; no retired name remains.
- `.github/workflows/ci-windows.yml` no longer sets the retired variable.

## Context & Constraints

- Depends on WP05 for the two new names in `core/env.py` (import the constants; do not restate strings).
- `m_3_2_8_provision_kitty_env.py` (~139–160): `GOVERNED_OPERATOR_VARS` and `GOVERNED_SECRET_VARS`; the module docstring's C-MIG rules (seed only observed values; secrets as blank template lines) must be honored; older migrations are historical (`manual_review` in the occurrence map — leave them).
- `core/secret_redaction.py` (~30–45): printable allowlist mirrors the operator vars.
- `completion.py` (~186): lists env vars for shell completion.
- `docs/api/environment-variables.md`: sections around lines 150–220 and 290–310 describe the flag and `SPEC_KITTY_SAAS_URL`; `tests/docs/test_env_var_scope_warning.py` checks the scope-warning prose.
- `bootstrap/env_file.py` may mention the vars in comments only; if so, fix the comment (out-of-map with rationale).
- Tests: `tests/specify_cli/upgrade/migrations/test_provision_kitty_env.py`, `tests/specify_cli/core/test_secret_redaction.py`, `tests/specify_cli/bootstrap/test_env_file_loader.py`, `tests/docs/test_env_var_scope_warning.py`, `tests/specify_cli/cli/commands/test_completion_fast_path.py`, `tests/specify_cli/invocation/cli/test_complete.py`.

## Subtasks & Detailed Guidance

### Subtask T031 – Red-first registry tests

- **Purpose**: Pin the var lists and the never-seed rule.
- **Steps**: In the migration tests, assert the generated `.kitty.env` scaffold names the two new opt-outs (as commented, unset lines when not present in the environment) and never names a retired one even when the live environment has it set; in the redaction tests, assert the new names are printable and retired names are absent from the allowlist; in the env-file loader tests, drop the retired names from fixtures; in `test_env_var_scope_warning.py`, adjust to the rewritten section.
- **Files**: the six test files.
- **Parallel?**: No.

### Subtask T032 – Provisioning migration

- **Purpose**: FR-014.
- **Steps**: Replace the three retired entries in `GOVERNED_OPERATOR_VARS` with the two new constants imported from `core/env.py`; keep ordering stable; update the docstring table if it enumerates the vars; add a one-line note in the migration docstring that older `.kitty.env` files carrying retired names are left untouched (the CLI ignores unknown names).
- **Files**: `src/specify_cli/upgrade/migrations/m_3_2_8_provision_kitty_env.py`.
- **Parallel?**: No.

### Subtask T033 – Redaction and completion

- **Purpose**: Registries agree.
- **Steps**: `secret_redaction.py` allowlist and `completion.py` listing follow the contract table; run `tests/architectural/test_no_dead_symbols.py` if it censuses these.
- **Files**: `src/specify_cli/core/secret_redaction.py`, `src/specify_cli/completion.py`.
- **Parallel?**: Yes, after T032.

### Subtask T034 – Environment-variable reference

- **Purpose**: The user-facing source of truth.
- **Steps**: Rewrite the hosted section: "Team Kitty target" (packaged default, `[team_kitty] server_url`, `SPEC_KITTY_SAAS_URL` override, split-brain rule, `auth status` shows the source), "Authentication is the switch" (no enable flag; `auth login`/`auth logout`; service token counts), the two opt-outs with their exact scope, and remove every `SPEC_KITTY_ENABLE_SAAS_SYNC` / `SYNC_*` mention including the `.kitty.env` examples (~172–178, ~293–294). Keep the description within the docs band; bump `updated`. If `tests/docs/test_docs_index_freshness.py` reds for this page, regenerate `docs/development/3-2-docs-retrieval-index.yaml` and log the out-of-map edit with a one-line rationale.
- **Files**: `docs/api/environment-variables.md`.
- **Parallel?**: Yes.

### Subtask T035 – CI workflow

- **Purpose**: CI must not arm a name the product ignores.
- **Steps**: Remove the retired variable from `.github/workflows/ci-windows.yml`; confirm no other workflow sets it (`git grep -n ENABLE_SAAS_SYNC .github`).
- **Files**: `.github/workflows/ci-windows.yml`.
- **Parallel?**: Yes.

## Test Strategy

- Red-first files above; `tests/docs/test_docs_seo.py tests/docs/test_description_length_gate.py` for the doc; `tests/architectural/test_no_dead_symbols.py`.

## Risks & Mitigations

- The migration must not rewrite existing `.kitty.env` files to remove retired lines (out of scope; operators' files are theirs). Prove with a test that an existing file is left byte-identical.

## Review Guidance

- Var lists match the contract table exactly; doc has zero retired names; workflow clean.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP07 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP07 --to for_review`, from the workspace the implement command gave you.

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

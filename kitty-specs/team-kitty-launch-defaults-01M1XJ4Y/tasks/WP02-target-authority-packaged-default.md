---
work_package_id: WP02
title: Target authority with packaged default
dependencies:
- WP01
requirement_refs:
- C-001
- FR-001
- FR-002
- FR-003
- FR-012
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
- T007
- T009
phase: Phase 1 - Target
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/auth/config.py
- src/specify_cli/auth/server_target.py
- src/specify_cli/saas_client/auth.py
- src/specify_cli/tracker/saas_readiness.py
- tests/auth/test_server_target.py
- tests/integration/test_spec_kitty_home_cli.py
- tests/tracker/test_server_target_fail_closed.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Target authority with packaged default

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

- `resolve_server_target()` never raises for "no target": with nothing configured it returns the packaged default `https://team.spec-kitty.ai` with `source = packaged_default`.
- It reads `config.toml [team_kitty] server_url`, never `[sync]`; precedence env > configuration > packaged default; env-vs-config disagreement still raises `ServerTargetSplitBrainError`.
- `ResolvedServerTarget` carries `source` (`environment | configuration | packaged_default`) and exposes it in `to_diagnostics_dict()`.
- `get_saas_base_url()` returns the env value or `None`. (`tracker/saas_readiness.py` is untouched here: WP04 removes its gate and `MISSING_HOST_CONFIG` once this resolver lands.)
- Every test in `contracts/target-resolution.md` is red on the base and green at head.

## Context & Constraints

- Read `src/specify_cli/auth/server_target.py` end to end. Today: `_read_configured_server_url()` reads `data.get("sync")` from `get_runtime_root().base / "config.toml"`; `resolve_server_target` raises `ConfigurationError(_NO_TARGET_MESSAGE)` when both sources are absent; `_classify_override` and `_guard_split_brain` implement the disagreement rule; `_warn_process_override` logs with `[sync].server_url` wording.
- `src/specify_cli/auth/config.py`: `EXAMPLE_HOSTED_SAAS_URL` is example-only per D-5; `get_saas_base_url()` raises `ConfigurationError` when the env var is unset. WP01's ADR supersedes D-5; update the module docstring to cite it.
- `src/specify_cli/saas_client/auth.py::_server_target_url` and `load_auth_context` consume the resolver for the stored-session bridge. `tracker/saas_readiness.py::_probe_host_config` calls `get_saas_base_url()`; with the accessor returning `None` instead of raising it still yields `MISSING_HOST_CONFIG` until WP04 removes that state — verify `tests/tracker/test_server_target_fail_closed.py` and adjust only that file.
- Existing tests: `tests/auth/test_server_target.py`, `tests/integration/test_spec_kitty_home_cli.py` (expects `ConfigurationError` when `SPEC_KITTY_HOME` has no config — that expectation flips), `tests/tracker/test_server_target_fail_closed.py`.
- C-001: this file stays the only resolver; do not add a second reading in `saas_client`, `readiness`, or `zeitgeist_client`.

## Subtasks & Detailed Guidance

### Subtask T005 – Red-first resolver tests

- **Purpose**: Witness each cell of the precedence matrix failing on the base.
- **Steps**:
  1. In `tests/auth/test_server_target.py`, add parametrized cases for the six rows of `contracts/target-resolution.md`: (unset, unset) → packaged default + `source == "packaged_default"`; (unset, dev) → dev + `configuration`; (env, unset) → env + `environment`; (env, same) → env + `environment`, override mode NONE; (env, different) → `ServerTargetSplitBrainError` naming both; (unset, malformed/blank) → packaged default.
  2. Add a case proving `[sync].server_url` in `config.toml` is ignored (resolves to the packaged default, no warning).
  3. Add `to_diagnostics_dict()` includes `source`.
  4. Use the existing fixtures in that file for `SPEC_KITTY_HOME` and `config.toml` writing; run the file and record the failing count.
- **Files**: `tests/auth/test_server_target.py`.
- **Parallel?**: No.

### Subtask T006 – `auth/config.py`

- **Purpose**: The packaged default has one home and the accessor stops raising.
- **Steps**:
  1. Rename `EXAMPLE_HOSTED_SAAS_URL` to `DEFAULT_HOSTED_SAAS_URL = "https://team.spec-kitty.ai"`; keep a module-level alias only if a grep shows other importers (`grep -rn EXAMPLE_HOSTED_SAAS_URL src tests`) and update them instead of aliasing.
  2. `get_saas_base_url() -> str | None`: return the stripped env value with trailing slashes removed, or `None`; delete the `ConfigurationError` raise and the "no fallback" wording; rewrite the module docstring to cite the WP01 ADR.
  3. Check `ConfigurationError` still has other producers (split-brain path uses its own error); if none remain, keep the class (public surface) but do not delete it in this WP.
- **Files**: `src/specify_cli/auth/config.py`.
- **Parallel?**: No.

### Subtask T007 – `auth/server_target.py`

- **Purpose**: Single authority implements the contract.
- **Steps**:
  1. `_read_configured_server_url()`: read `data.get("team_kitty")`, key `server_url`; malformed/blank → `None`; do not read `sync`.
  2. Add `source: str` (or a small `StrEnum` `TargetSource`) to `ResolvedServerTarget`; include in `to_diagnostics_dict()`.
  3. `resolve_server_target`: when both sources are `None`, resolve to `DEFAULT_HOSTED_SAAS_URL` with `source = packaged_default`, override mode NONE; delete `_NO_TARGET_MESSAGE`; otherwise unchanged classification, with `source` set from which value won.
  4. `_warn_process_override` and `_SPLIT_BRAIN_MESSAGE`: replace `[sync].server_url` with `[team_kitty] server_url` in wording; keep the warning semantics.
  5. Update the module docstring (no more "fails closed on no target").
  6. Run `tests/auth/test_server_target.py` (green) and `mypy src/specify_cli/auth/server_target.py`.
- **Files**: `src/specify_cli/auth/server_target.py`.
- **Parallel?**: No.
- **Notes**: Keep `process_wide_override` semantics untouched; `_auth_saas_target.py` (WP03) relies on `process_wide_override=False` to surface split-brain descriptively.

### Subtask T009 – Downstream consumers and integration test

- **Purpose**: Callers that treated "no target" as an error path follow the new contract.
- **Steps**:
  1. `src/specify_cli/saas_client/auth.py`: `_server_target_url` and the stored-session bridge no longer need the `ConfigurationError` catch for "no target"; keep the split-brain handling; `SaasAuthError` for "no SaaS URL supplied by any source" (D-5 wording in the `load_auth_context` docstring) becomes unreachable — remove that branch and the D-5 sentence.
  2. `tests/integration/test_spec_kitty_home_cli.py`: the case that expects `ConfigurationError` when `SPEC_KITTY_HOME` has no config now expects the packaged default with `source == "packaged_default"`; keep the case proving the config is read only under `SPEC_KITTY_HOME`, re-keyed to `[team_kitty]`.
  3. Run: `tests/auth/`, `tests/integration/test_spec_kitty_home_cli.py`, `tests/tracker/`, `tests/zeitgeist_client/test_resolution.py`, `tests/specify_cli/saas_client/`.
- **Files**: `src/specify_cli/saas_client/auth.py`, `tests/integration/test_spec_kitty_home_cli.py`.
- **Parallel?**: Yes, after T007.

## Test Strategy

- Red-first file: `tests/auth/test_server_target.py`. Blast radius: `tests/auth/ tests/tracker/ tests/integration/test_spec_kitty_home_cli.py tests/zeitgeist_client/test_resolution.py tests/specify_cli/saas_client/` plus `make test-fast`.

## Risks & Mitigations

- A caller somewhere still catches `ConfigurationError` to mean "hosted off": `git grep -n "ConfigurationError" src/` before deleting the raise; each catch must be reasoned about, not removed blindly.
- Windows path handling for `config.toml` is unchanged; do not touch `get_runtime_root`.

## Review Guidance

- Matrix tests exist and were red on the base (commit order proves it).
- No second resolver appeared; `git grep -n '"sync"' src/specify_cli/auth` is empty.
- `tracker/saas_readiness.py` is not in the diff (WP04 owns it).

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP02 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP02 --to for_review`, from the workspace the implement command gave you.

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

---
work_package_id: WP06
title: Regression guard, CLI integration, docs
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-010
- FR-013
tracker_refs: []
planning_base_branch: fix/spec-kitty-home-isolation
merge_target_branch: fix/spec-kitty-home-isolation
branch_strategy: Planning artifacts for this mission were generated on fix/spec-kitty-home-isolation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spec-kitty-home-isolation unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Harden & Document
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "77280"
history:
- at: '2026-06-26T11:06:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/audit/
create_intent:
- tests/integration/test_spec_kitty_home_cli.py
execution_mode: code_change
model: ''
owned_files:
- tests/audit/test_no_legacy_path_literals.py
- src/doctrine/skills/spk-team-upsun-cli-sync/SKILL.md
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Regression guard, CLI integration, docs

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Close out the mission: an architectural guard so the literal can't re-scatter, an end-to-end CLI isolation test mirroring the issue repro, the in-repo skill doc update, and a CHANGELOG entry. Covers FR-010 (guard), FR-013 (docs), and validates SC-001..SC-004.

- **DONE when**: the guard fails on any hand-rolled `Path.home() / ".spec-kitty"` in global-state modules; the CLI test proves all state lands under `SPEC_KITTY_HOME` with the default home clean; full suite + `ruff` + `mypy --strict` + terminology guard are green.

## Context & Constraints

- Depends on **WP01–WP05** (all reroutes done).
- `.venv` is warm — use `.venv/bin/...`.
- Existing guards to build on: `tests/audit/test_no_legacy_path_literals.py` and `tests/architectural/test_real_home_isolation_guard.py`.
- Sibling `spec-kitty-saas` runbooks are **out of scope** (C-002) — only the in-repo `SKILL.md`.

## Branch Strategy

- **Strategy**: shared-feature-branch
- **Planning base branch**: fix/spec-kitty-home-isolation
- **Merge target branch**: fix/spec-kitty-home-isolation

## Subtasks & Detailed Guidance

### Subtask T021 – Architectural guard

- **Purpose**: Enforce FR-010 — no module recomputes the home for global state.
- **Steps**: Extend `tests/audit/test_no_legacy_path_literals.py` to scan `src/specify_cli/{sync,auth,tracker,state}` for the literal pattern `Path.home() / ".spec-kitty"` (and the bare string `".spec-kitty"` used as a home child) and fail if found. **Allowlist**:
  - the keystone `src/specify_cli/paths/windows_paths.py` (and platformdirs fallback),
  - asset-home modules (`runtime/home.py`, `kernel/paths.py` — they use `.kittify`),
  - migration code (`paths/windows_migrate.py`),
  - worktree-local `review/lock.py` (uses `worktree / ".spec-kitty"`, not home).
- **Files**: `tests/audit/test_no_legacy_path_literals.py`
- **Notes**: First run it red (confirm it would have caught the bug), then green after WP02–WP05.

### Subtask T022 – CLI integration test

- **Purpose**: SC-001/SC-002 — the issue repro, inverted.
- **Steps**: Add `tests/integration/test_spec_kitty_home_cli.py`:
  - Set distinct temp `HOME` and `SPEC_KITTY_HOME` (+ `SPEC_KITTY_ENABLE_SAAS_SYNC=1`).
  - Invoke the sync-server path through the CLI entrypoint (CliRunner or subprocess).
  - Assert `config.toml` exists under `SPEC_KITTY_HOME` and `$HOME/.spec-kitty/config.toml` is absent.
  - Add a no-env case asserting POSIX fallback to `~/.spec-kitty` (use a temp HOME).
- **Files**: `tests/integration/test_spec_kitty_home_cli.py`
- **Notes**: If this touches real ports/daemon, keep it lightweight (config write only) or mark for serial `-n0` per CLAUDE.md.

### Subtask T023 [P] – Update SKILL.md

- **Purpose**: FR-013 / DIRECTIVE_037 — docs match true behavior.
- **Steps**: In `src/doctrine/skills/spk-team-upsun-cli-sync/SKILL.md`, correct any claim that overstated/understated isolation. State that `SPEC_KITTY_HOME` now isolates **all** local state (sync/auth/tracker/daemon). Add a verification snippet (from `quickstart.md` step 1) showing where state landed. Keep terminology canon (Mission, not feature).
- **Files**: `src/doctrine/skills/spk-team-upsun-cli-sync/SKILL.md`
- **Parallel?**: Yes.

### Subtask T024 [P] – CHANGELOG entry

- **Purpose**: DIR-009 — record the fix and the Windows path normalization.
- **Steps**: Add a `CHANGELOG.md` entry: `SPEC_KITTY_HOME` now isolates all POSIX/Windows sync/auth/tracker/daemon state (fixes #2171); note the Windows surfaces normalized onto the platformdirs base and that no automatic migration of existing `~/.spec-kitty` data is performed.
- **Files**: `CHANGELOG.md`
- **Parallel?**: Yes.
- **Notes**: Only bump `pyproject.toml` version if `src/specify_cli/__init__.py` was modified (it is not in this mission's scope) — otherwise a CHANGELOG entry suffices.

### Subtask T025 – Full verification

- **Steps**: Run the full suite + lint + types + terminology guard:
  - `PWHEADLESS=1 .venv/bin/pytest tests/ -n auto --dist loadfile -p no:cacheprovider`
  - serial daemon/real-port pass if affected: `PWHEADLESS=1 .venv/bin/pytest tests/sync/test_orphan_sweep.py -n0 -q`
  - `.venv/bin/ruff check .` and `.venv/bin/mypy src/specify_cli`
  - `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -q` (SKILL.md prose)
  - `.venv/bin/pytest tests/audit/test_no_legacy_path_literals.py tests/architectural/test_real_home_isolation_guard.py -q`
- **Files**: none (verification).

## Test Strategy

- Guard + integration + full suite as above. All green is the gate.

## Risks & Mitigations

- **Guard false positives** → keep the allowlist precise (keystone, asset-home, migration, worktree-lock).
- **Terminology gate** runs only in CI's misc job → run it locally before finishing (CLAUDE.md).
- **Real-port tests** → serial `-n0`.

## Review Guidance

- Confirm the guard would have caught the original bug (temporarily reintroduce a literal to verify red, then revert).
- Confirm the CLI test asserts both presence under `SPEC_KITTY_HOME` and absence under default home.
- Confirm SKILL.md no longer claims isolation the code doesn't provide, and CHANGELOG documents the Windows normalization.

## Activity Log

- 2026-06-26T11:06:32Z – system – Prompt created.

### Updating Status

Use `spec-kitty agent tasks move-task WP06 --to <status>`.
- 2026-06-26T12:34:39Z – claude:opus:python-pedro:implementer – shell_pid=88364 – Assigned agent via action command
- 2026-06-26T13:06:27Z – claude:opus:python-pedro:implementer – shell_pid=88364 – Ready (forced past known coord/primary subtask-gate): WP06 gates green
- 2026-06-26T13:06:40Z – claude:opus:reviewer-renata:reviewer – shell_pid=77280 – Started review via action command
- 2026-06-26T13:13:58Z – user – shell_pid=77280 – Review passed: guard verified red/green (clean GREEN -> injected Path.home()/'.spec-kitty' in sync/config.py RED -> revert GREEN), allowlist precise (5 files; reroute dirs sync/auth/tracker/state NOT exempt), CLI isolation test exercises real Typer app via CliRunner with unset-fallback case, SKILL.md+CHANGELOG accurate (Windows normalization + no-auto-migration), terminology canon preserved. ruff clean; mypy 19 pre-existing only (none in reroute files); integration subset 613 passed/10 skipped + 18 acceptance passed.

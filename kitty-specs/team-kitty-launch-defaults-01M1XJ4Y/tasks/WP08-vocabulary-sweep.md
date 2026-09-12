---
work_package_id: WP08
title: Vocabulary sweep under the occurrence map
dependencies:
- WP03
- WP04
- WP07
requirement_refs:
- C-002
- C-003
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
phase: Phase 3 - Sweep
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/context/
create_intent:
- docs/context/team-kitty.md
execution_mode: code_change
model: ''
owned_files:
- src/charter/offering/skills/spk-team-sync/SKILL.md
- src/charter/offering/skills/spk-team-auth/SKILL.md
- src/charter/offering/skills/spk-team-tracker/SKILL.md
- src/charter/offering/skills/spec-kitty-mission-review/SKILL.md
- src/specify_cli/__init__.py
- src/runtime/next/_internal_runtime/events.py
- docs/context/team-kitty.md
- docs/guides/project-sync-consent.md
- docs/operations/internal-hosted-readiness.md
- docs/operations/manual-test-plan.md
- docs/operations/stale-lane-seed.md
- docs/operations/start-branch-coord-divergence.md
- docs/operations/sync-daemon-orphan-cleanup.md
- docs/operations/sync-drain.md
- docs/development/contributing.md
- docs/development/reference/known-friction-points.md
- docs/development/reference/process-global-inventory-3115.md
- docs/development/testing/testing-flakiness.md
- docs/migrations/cross-repo-e2e-gate.md
- docs/migrations/teamspace-mission-state-920-closeout.md
- docs/migrations/tracker-egress-refusal.md
- docs/development/3-2-docs-retrieval-index.yaml
- CHANGELOG.md
- tests/agent/test_agent_feature.py
- tests/architectural/census/spec_kitty_home_pin_tombstones.yaml
- tests/architectural/test_docs_cli_reference_parity.py
- tests/architectural/test_no_retired_subsystems.py
- tests/auth/concurrency/test_incident_regression.py
- tests/cli/commands/fixtures/render_width_3115/capture_pinned.txt
- tests/cli/commands/fixtures/render_width_3115/capture_width80.txt
- tests/cli/test_top_level_group_empty_invocation.py
- tests/docs/test_build_cli_reference.py
- tests/docs/test_check_cli_reference_freshness.py
- tests/docs/test_check_docs_freshness.py
- tests/docs/test_docs_index_freshness.py
- tests/docs/test_rulers_blocking.py
- tests/e2e/test_worktree_owned_root_concurrency.py
- tests/fixtures/setup_plan_pre_mission_replay.py
- tests/integration/test_colliding_mission_flow.py
- tests/integration/test_json_envelope_strict.py
- tests/next/test_query_mode_unit.py
- tests/reliability/fixtures/README.md
- tests/reliability/fixtures/__init__.py
- tests/specify_cli/cli/commands/agent/test_2861_causation_repro.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Vocabulary sweep under the occurrence map

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

- No live source, skill, doc, or test fixture names `SPEC_KITTY_ENABLE_SAAS_SYNC`, `SPEC_KITTY_SYNC_DISABLE`, `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, `OWNED_SYNC_UNSUPPORTED`, `is_saas_sync_enabled`, `sync_active`, or `[sync]` outside the occurrence-map exceptions; `git grep` proves it (A10).
- Pages that describe the deleted transport as live are superseded (banner + `doc_status: deprecated`) or rewritten; `docs/context/team-kitty.md`'s "What the flag still gates" section is replaced by the launch state; `CHANGELOG.md` carries the entry.
- The docs retrieval index is regenerated; `tests/docs/` and the terminology guard are green.

## Context & Constraints

- Governed by `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/occurrence_map.yaml`: `user_facing_strings: rename_if_user_visible`, `tests_fixtures: rename`, `cli_commands: do_not_change`, `logs_telemetry: do_not_change`; exceptions: `kitty-specs/**`, `kitty-ops/**`, `docs/adr/**`, `docs/archive/**`, `docs/changelog/**` (never edit), `CHANGELOG.md` (append only).
- Files owned by WP02–WP07 and WP09 are theirs; if one still carries a retired name after they landed, report it in the Activity Log and to the reviewer rather than editing it.
- Inventory (live, non-archive) at planning time: skills `src/charter/offering/skills/{spk-team-sync,spk-team-auth,spk-team-tracker,spec-kitty-mission-review}/SKILL.md`; source comments `src/specify_cli/__init__.py`, `src/runtime/next/_internal_runtime/events.py`; docs `docs/context/team-kitty.md`, `docs/guides/project-sync-consent.md`, `docs/operations/{internal-hosted-readiness,manual-test-plan,stale-lane-seed,start-branch-coord-divergence,sync-daemon-orphan-cleanup,sync-drain}.md`, `docs/development/{contributing.md,reference/known-friction-points.md,reference/process-global-inventory-3115.md,testing/testing-flakiness.md}`, `docs/migrations/{cross-repo-e2e-gate,teamspace-mission-state-920-closeout,tracker-egress-refusal}.md`, `docs/development/3-2-docs-retrieval-index.yaml` (regenerated), `CHANGELOG.md`; test fixtures listed in T038. Re-run the inventory yourself — it moves as other lanes land:
  `git grep -l -e SPEC_KITTY_ENABLE_SAAS_SYNC -e SPEC_KITTY_SYNC_DISABLE -e SPEC_KITTY_SYNC_MINIMAL_IMPORT -e OWNED_SYNC_UNSUPPORTED -e is_saas_sync_enabled -e sync_active -e '\[sync\]' -- src docs tests packs Makefile pyproject.toml .github ':!docs/adr' ':!docs/archive' ':!docs/changelog' ':!kitty-specs' ':!kitty-ops'`
- Terminology guard: `tests/architectural/test_no_legacy_terminology.py` bans exactly `ceremony` and `status-writing` (never write those); the Mission-vs-feature canon is review-enforced.
- Docs gates: descriptions 50–180 chars; `updated:` bumped on every touched page; the retrieval index regenerated with `PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write`.

## Subtasks & Detailed Guidance

### Subtask T036 – Skills and source comments

- **Purpose**: Agents read skills first; a skill that says "set SPEC_KITTY_ENABLE_SAAS_SYNC" re-teaches the dead model.
- **Steps**:
  1. `spk-team-sync/SKILL.md`: this skill frames "sync" as a live capability. Rewrite it as the Team Kitty / Zeitgeist skill (or retire it with a pointer if the repo's skill registry allows deletion — check `.kittify/command-skills-manifest.json` and `tests/architectural/` skill census before deleting; prefer rewrite). Content: what a moment is, that authentication is the switch, `auth status` shows the target, no opt-in, troubleshooting = admission/membership.
  2. `spk-team-auth/SKILL.md` (~23) and `spk-team-tracker/SKILL.md` (~22): remove flag guidance; state that tracker commands need a session.
  3. `spec-kitty-mission-review/SKILL.md` (~529–695): replace flag-based instructions with session-based ones.
  4. `src/specify_cli/__init__.py` (~26) and `src/runtime/next/_internal_runtime/events.py`: comments only; reword.
- **Files**: as listed.
- **Parallel?**: Yes.

### Subtask T037 – Docs pages, context page, changelog

- **Purpose**: `code is the source of truth and docs mirror shipped behavior`.
- **Steps**:
  1. Already-deprecated pages (`sync-drain.md`, `project-sync-consent.md`, `internal-hosted-readiness.md` if deprecated): add/keep a superseded banner pointing to `docs/context/team-kitty.md`; remove instructions that set retired names; do not expand them.
  2. Active pages (`contributing.md`, `testing-flakiness.md`, `known-friction-points.md`, `process-global-inventory-3115.md`, `manual-test-plan.md`, `stale-lane-seed.md`, `start-branch-coord-divergence.md`, the three `docs/migrations/*` pages): replace flag/`[sync]` references with the launch behavior or with "authenticated session"; where a page documents the retired daemon as history, label the paragraph historical instead of deleting it.
  3. `docs/context/team-kitty.md`: replace "What `SPEC_KITTY_ENABLE_SAAS_SYNC` still gates" with "Launch state: authentication is the switch" (list the two opt-outs, `[team_kitty] server_url`, packaged default, `auth status` provenance); update "Stale surfaces you will meet"; bump `updated`.
  4. `CHANGELOG.md`: append an Unreleased entry under the existing format: packaged default; `[team_kitty] server_url`; enable flag, `SYNC_*` names, `[sync]` table and `OWNED_SYNC_UNSUPPORTED` removed with no alias; two new opt-outs; one-time sign-in hint; cite #1621/#3980.
- **Files**: as listed.
- **Parallel?**: Yes.

### Subtask T038 – Remaining test fixtures

- **Purpose**: `tests_fixtures: rename` — fixtures that arm or assert the retired names.
- **Steps**: Run the inventory command restricted to `tests/`; exclude files owned by WP02–WP07/WP09; for each remaining file: delete `setenv`/`delenv`/`setdefault` of retired names (they are no-ops now); rewrite assertions that expected the "not enabled" message to expect sign-in guidance; update `tests/architectural/census/spec_kitty_home_pin_tombstones.yaml` prose; regenerate width-capture fixtures under `tests/cli/commands/fixtures/render_width_3115/` with the tool that produced them (see the fixture README) rather than hand-editing. Known list at planning: `tests/agent/test_agent_feature.py`, `tests/architectural/test_docs_cli_reference_parity.py`, `tests/architectural/test_no_retired_subsystems.py`, `tests/auth/concurrency/test_incident_regression.py`, `tests/cli/test_top_level_group_empty_invocation.py`, `tests/docs/test_build_cli_reference.py`, `test_check_cli_reference_freshness.py`, `test_check_docs_freshness.py`, `test_docs_index_freshness.py`, `test_rulers_blocking.py`, `tests/e2e/test_worktree_owned_root_concurrency.py`, `tests/fixtures/setup_plan_pre_mission_replay.py`, `tests/integration/test_colliding_mission_flow.py`, `test_json_envelope_strict.py`, `tests/next/test_query_mode_unit.py`, `tests/reliability/fixtures/README.md`, `tests/reliability/fixtures/__init__.py`, `tests/specify_cli/cli/commands/agent/test_2861_causation_repro.py`, plus roughly thirty more the inventory will list.
- **Files**: the listed test files (declared as owned below) and any further inventory hits with a one-line rationale each.
- **Parallel?**: Yes.

### Subtask T039 – Regenerate the retrieval index and run the docs gates

- **Steps**: `PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write`; `PWHEADLESS=1 .venv/bin/python -m pytest tests/docs/ -q`; fix findings on your files.
- **Files**: `docs/development/3-2-docs-retrieval-index.yaml`.
- **Parallel?**: No (last).

### Subtask T040 – A10 witness

- **Steps**: Run the inventory command; paste the (empty) result into the Activity Log with the commit SHA; run `tests/architectural/test_no_legacy_terminology.py` and `tests/architectural/test_no_retired_subsystems.py`.
- **Files**: none.
- **Parallel?**: No.

## Test Strategy

- `tests/docs/` full, `tests/architectural/test_no_legacy_terminology.py`, `test_no_retired_subsystems.py`, and every test file you edited; `make test-fast`.

## Risks & Mitigations

- Editing an archive by accident: the review diff-compliance check blocks `do_not_change` paths; keep `git status` scoped.
- Width-capture fixtures: regenerate, never hand-edit, or the render test will red for whitespace.

## Review Guidance

- Inventory command returns nothing; every touched doc has a bumped `updated`; CHANGELOG entry appended, not inserted into a released section.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP08 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP08 --to for_review`, from the workspace the implement command gave you.

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

---
work_package_id: WP01
title: Remove --feature from agent-namespace commands
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
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Alias removal
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "394714"
history:
- at: '2026-06-15T12:04:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/context.py
- src/specify_cli/cli/commands/agent/mission.py
- tests/specify_cli/cli/commands/agent/**
- tests/e2e/test_feature_alias_smoke.py
- tests/cross_cutting/misc/test_tasks_cli_commands.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Remove `--feature` from agent-namespace commands

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

Remove the hidden, deprecated `--feature` Typer alias (and its plumbing) from the
five agent-namespace commands, so the terminology canon (`--mission`) is the only
selector for them. `--mission` behavior is byte-for-byte unchanged.

**Done when:**
- No `--feature` token remains in `agent/{status,tasks,workflow,context,mission}.py`
  (`git grep -- '--feature' <those files>` → 0).
- Each affected command still resolves `--mission` exactly as before.
- `spec-kitty agent tasks status --feature X` now errors with Typer's "no such
  option"; `--mission X` succeeds.
- ruff + mypy clean on changed files; targeted tests green.

## Context & Constraints

- Spec: [spec.md](../spec.md) FR-001, FR-002, FR-008. Plan: [plan.md](../plan.md)
  IC-02. Bulk-edit map: [occurrence_map.yaml](../occurrence_map.yaml) (cs-001..005,
  cli-001..005).
- This is a **bulk_edit / remove** operation. Honor the occurrence map: in-scope
  removal only.
- **DO NOT TOUCH** (FR-008, NFR-001): `src/specify_cli/cli/selector_resolution.py`,
  `src/specify_cli/missions/_legacy_aliases.py`, anything under
  `src/specify_cli/status/`, `task_utils/`, or `legacy_detector.py`.
- **`agent/workflow.py` caveat**: it imports
  `merge_append_preserving_coordination_event_log_bytes` from `status_service` —
  that import is UNRELATED to the alias and MUST remain. Only remove `--feature`.
- The alias is plumbed in 3 layers per command (see research.md R2): the
  `feature: Annotated[..., typer.Option("--feature", hidden=True, ...)]` param,
  the `explicit_feature=feature` threading, and the `alias_value`/`alias_flag="--feature"`
  args at the `resolve_selector(...)` call. Remove all three; switch the call to
  the mission-only path (drop the alias args, or use `resolve_mission_handle`).

## Branch Strategy

- **Strategy**: lane-per-WP from `lanes.json` (computed at finalize-tasks)
- **Planning base branch**: `mission/codebase-sanitization-1060-1622`
- **Merge target branch**: `mission/codebase-sanitization-1060-1622`
- **Implement command**: `spec-kitty agent action implement WP01 --agent claude --base mission/codebase-sanitization-1060-1622`
  — the `--base` is **REQUIRED**: this mission was flattened and `lanes.json`
  records a stale `mission_branch` (a deleted coord branch); `--base` overrides it
  to the live target. Execution worktrees are allocated per lane; do not
  hand-create them.

## ⚠️ The removal recipe is NOT uniform (verified against code)

`resolve_selector(*, alias_value, alias_flag, ...)` has **no defaults** for
`alias_value`/`alias_flag` — you cannot just delete those kwargs (TypeError), and
you must **never leave `alias_flag="--feature"`** (forbidden token + keeps the
alias). Re-grep line numbers at WP start (the file has drifted).

## Subtasks & Detailed Guidance

### Subtask T001 – `agent/tasks.py`
- **Reality**: tasks.py does NOT call `resolve_selector` per command — there is
  ONE call inside the shared helper `_find_mission_slug` (~L745-752). Each command
  function passes `explicit_feature=feature`.
- **Steps**: (a) delete every `feature: Annotated[..., typer.Option("--feature", ...)]`
  command param; (b) delete every `explicit_feature=feature` call-site arg;
  (c) in `_find_mission_slug`, remove the `explicit_feature` param and the
  `alias_value`/`alias_flag` args from the single `resolve_selector` call (use the
  canonical `mission` value only). Keep the resolver import.
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`

### Subtask T002 [P] – `agent/status.py`
- **Reality**: status.py threads `explicit_feature` through TWO helpers —
  `_resolve_status_surface` (~L136-171) AND `_find_mission_slug` (~L84-89, the
  single resolve_selector call).
- **Steps**: Remove the command `--feature` params; remove `explicit_feature`
  from BOTH helper signatures and their call sites; strip the `alias_value`/
  `alias_flag` args in the resolve_selector call.
- **Files**: `src/specify_cli/cli/commands/agent/status.py`

### Subtask T003 [P] – `agent/workflow.py`
- **Steps**: Remove the `--feature` param(s) + the resolve_selector alias args.
  **Preserve** the `merge_append_preserving_coordination_event_log_bytes` import/
  usage (~L315) — unrelated to the alias.
- **Files**: `src/specify_cli/cli/commands/agent/workflow.py`

### Subtask T004 – `agent/context.py` + `agent/mission.py` (NOT a uniform "option removal")
- **`agent/context.py`**: uses `resolve_mission_handle(mission or feature)`
  (L123/126), NOT `resolve_selector`. Remove the `--feature` param and change
  `raw_handle = mission or feature` → `raw_handle = mission`.
- **`agent/mission.py`**: has **NO `--feature` typer.Option**. The lone hit is a
  help-HINT STRING at L3622 (`finalize-tasks --feature {mission_slug}`) → change
  to `--mission {mission_slug}`. **DO NOT** touch the `feature`-named params
  (they are bound to `--mission`) or the `--mission-type`/`--mission`
  `resolve_selector` call at L1484.
- **Files**: `src/specify_cli/cli/commands/agent/context.py`,
  `src/specify_cli/cli/commands/agent/mission.py`

### Subtask T005 – Update agent-namespace tests + the contradicting callers
- **Steps**:
  - In `tests/specify_cli/cli/commands/agent/**`, switch in-scope `--feature`
    invocations to `--mission`; `test_json_selector_errors.py` (which expects a
    "Conflicting selectors" error from `--mission X --feature Y`) must be updated —
    after removal that path exits 2 (unknown option), so re-target it.
  - `tests/e2e/test_feature_alias_smoke.py`: its `agent tasks status --feature`
    equivalence arm now CONTRADICTS the removal — convert that arm to assert
    rejection (leave any out-of-scope-command arms intact).
  - `tests/cross_cutting/misc/test_tasks_cli_commands.py` (L90/97/197): switch the
    in-scope `status --feature` / `verify --feature` calls to `--mission`.
- **Files**: the owned test files above.

### Subtask T006 – Gates
- **Steps**: `ruff check` + `mypy` on changed files (zero issues, no new
  suppressions). `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/ tests/e2e/test_feature_alias_smoke.py tests/cross_cutting/misc/test_tasks_cli_commands.py -q`.
- **Validation**:
  - [ ] `git grep -- '--feature' src/specify_cli/cli/commands/agent/{status,tasks,workflow,context,mission}.py` → 0 (incl. no residual `alias_flag="--feature"`)
  - [ ] resolve_selector / selector_resolution.py untouched; workflow.py status_service import intact
  - [ ] mission.py `--mission-type`/`--mission` resolver (L1484) and `--mission` params untouched
  - [ ] ruff + mypy clean; the three test targets green

## Definition of Done
- All 6 subtasks complete; validation checks pass; no out-of-scope files touched.

## Reviewer Guidance
- Confirm zero `--feature` in the 5 files; confirm `--mission` unchanged; confirm
  FR-008 surfaces (resolver, `_legacy_aliases.py`) and the workflow.py
  status_service import are intact; confirm tests prove rejection + `--mission`.

## Activity Log

- 2026-06-15T13:02:22Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Assigned agent via action command
- 2026-06-15T13:24:20Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Ready: agent-cmd --feature removed; gates green (ruff/mypy clean, 282 pass, 3 pre-existing failures)
- 2026-06-15T13:25:03Z – claude:sonnet:python-pedro:implementer – shell_pid=225207 – Ready: agent-cmd --feature removed; gates green (ruff/mypy clean, 282 pass, 3 pre-existing failures)
- 2026-06-15T13:53:03Z – user – shell_pid=225207 – Orchestrator sync: WP01 implementer completed in lane-a (282 pass / 3 claimed-pre-existing)
- 2026-06-15T13:54:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=394714 – Started review via action command
- 2026-06-15T14:00:57Z – user – shell_pid=394714 – Review passed (renata): --feature removed from all 5 agent-namespace files (git grep --feature=0). status/tasks/workflow recipes correct (explicit_feature + alias args dropped, no dangling alias_flag, resolve_selector import dropped where unused, resolve_mission_handle kept); workflow.py merge_append_preserving_coordination_event_log_bytes import INTACT; context.py raw_handle=mission; mission.py changed ONLY L3622 help string, L1484 resolver + --mission params untouched. NFR-001 frozen files zero-diff. Tests converted to assert exit-2 rejection (not deleted-to-pass). PRE-EXISTING-FAILURE PROOF: 282 pass/3 fail on lane; the 3 (test_wrapper_delegation acknowledge x2, test_acceptance_commands) reproduce IDENTICALLY on base (acceptance_commands fails L115 path-convention via standalone tasks_cli.py, unrelated to alias). mission.py 4 mypy errors pre-existing identical on base; WP01 cast FIXED context.py L87 (base 5->lane 4). ruff clean. NON-BLOCKING OBS: T005 left 6 --feature in test_tasks_cli_commands.py targeting separate tasks_cli.py script, out of WP01 typer scope.
- 2026-06-15T14:41:44Z – user – shell_pid=394714 – Done override: Code consolidated onto mission/ (49f4b93ef + e9c311b9b); per-WP renata-approved; PR to upstream pending

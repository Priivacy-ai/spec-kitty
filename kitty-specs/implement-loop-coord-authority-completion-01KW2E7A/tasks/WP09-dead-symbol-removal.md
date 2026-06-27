---
work_package_id: WP09
title: Remove dead symbol FEATURE_CONTEXT_UNRESOLVED_CODE
dependencies: []
requirement_refs:
- C-005
- FR-013
tracker_refs: []
planning_base_branch: design/coord-authority-remediation-2160
merge_target_branch: design/coord-authority-remediation-2160
branch_strategy: Planning artifacts for this mission were generated on design/coord-authority-remediation-2160. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-authority-remediation-2160 unless the human explicitly redirects the landing branch.
subtasks:
- T037
phase: Phase 3 - Closeout
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3940829"
history:
- at: '2026-06-26T18:29:45Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/missions/_read_path_resolver.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Remove dead symbol FEATURE_CONTEXT_UNRESOLVED_CODE

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

Remove the dead constant `FEATURE_CONTEXT_UNRESOLVED_CODE` (`_read_path_resolver.py:39`)
behavior-preservingly.

Done when: the constant is removed; a grep proves zero importers of the **constant**
(`FEATURE_CONTEXT_UNRESOLVED_CODE`); the bare string error code `"FEATURE_CONTEXT_UNRESOLVED"`
(a separate `ActionContextError` code) is **untouched**; ruff/mypy/suite green.

## Context & Constraints

- Spec FR-013, C-005. Verified by the campsite + brownfield squads: the `_CODE` constant has
  zero importers (only its own def); ~15 other hits are the bare string literal, independent.
- Behavior-preserving — do not touch the string-literal error code or any `ActionContextError`.

## Branch Strategy

- **Strategy**: already-confirmed
- **Planning base branch**: design/coord-authority-remediation-2160
- **Merge target branch**: design/coord-authority-remediation-2160

## Subtasks & Detailed Guidance

### Subtask T037 – Remove the dead constant
- **Steps**: `grep -rn "FEATURE_CONTEXT_UNRESOLVED_CODE" src/ tests/` to confirm zero
  importers of the constant (only the def). Remove the def at `:39`. Confirm it is not in
  `__all__`. Run `ruff check . && mypy src/specify_cli` and the suite.
- **Files**: `src/specify_cli/missions/_read_path_resolver.py`.
- **Notes**: If grep shows ANY importer, STOP and report — the premise is wrong.

## Test Strategy

`ruff check . && mypy src/specify_cli/missions/_read_path_resolver.py` and
`PWHEADLESS=1 pytest tests/ -k read_path_resolver -q` (or the relevant module tests) green.

## Risks & Mitigations

- **Confusing the constant with the string code** → removing the wrong thing. Mitigation:
  grep for the exact constant name `FEATURE_CONTEXT_UNRESOLVED_CODE`, not the substring.

## Review Guidance

- Confirm only the constant def was removed; the string error code remains.

## Activity Log

- 2026-06-26T18:29:45Z – system – Prompt created.
- 2026-06-26T19:02:22Z – claude:sonnet:python-pedro:implementer – shell_pid=3901291 – Assigned agent via action command
- 2026-06-26T19:07:24Z – user – shell_pid=3901291 – Moved to claimed
- 2026-06-26T19:07:30Z – user – shell_pid=3901291 – Moved to in_progress
- 2026-06-26T19:08:40Z – claude:sonnet:python-pedro:implementer – shell_pid=3901291 – Dead constant removed; zero importers confirmed; #2158 gate re-baselined (no census change needed — constant was not in __all__)
- 2026-06-26T19:18:49Z – claude:sonnet:python-pedro:implementer – shell_pid=3901291 – FR-013 dead-symbol removed; zero importers; gates green; flat execution
- 2026-06-26T19:19:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=3940829 – Started review via action command
- 2026-06-26T19:21:55Z – user – shell_pid=3940829 – Approved (flat execution): FR-013 dead-constant removal on design branch; zero importers; #2158 gates green (11 passed); ruff/mypy clean

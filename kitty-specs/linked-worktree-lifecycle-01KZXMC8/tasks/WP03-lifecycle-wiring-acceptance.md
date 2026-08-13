---
work_package_id: WP03
title: Full lifecycle wiring and acceptance
dependencies:
- WP02
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-002
- C-003
- C-004
planning_base_branch: codex/spec-kitty-worktree-mission-create
merge_target_branch: codex/spec-kitty-worktree-mission-create
branch_strategy: Planning artifacts for this mission were generated on codex/spec-kitty-worktree-mission-create. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/spec-kitty-worktree-mission-create unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
phase: Phase 3 - CLI lifecycle and acceptance
history:
- at: '2026-08-13T13:39:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/selector_resolution.py
create_intent:
- tests/integration/test_caller_owned_worktree_lifecycle.py
- tests/architectural/test_mission_operation_root_boundary.py
execution_mode: code_change
model: ''
owned_files:
- docs/changelog/CHANGELOG.md
- docs/codemap/codemap.html
- docs/codemap/codemap.json
- docs/codemap/codemap.lock
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/execution_context.py
- src/specify_cli/acceptance/gates_core.py
- src/specify_cli/cli/selector_resolution.py
- src/specify_cli/cli/commands/agent/context.py
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/agent/mission_feature_resolution.py
- src/specify_cli/cli/commands/agent/mission_setup_plan.py
- src/specify_cli/cli/commands/agent/mission_branch_context.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/cli/commands/agent/tasks_finalize.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/status/aggregate.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/workspace/context.py
- tests/integration/test_caller_owned_worktree_lifecycle.py
- tests/architectural/test_mission_operation_root_boundary.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- spklw-rhr
---

# WP03 — Full lifecycle wiring and acceptance

## Цель и критерии успеха

Все status/context/planning/tasks/action/next/accept команды получают один `MissionOperationContext` и не выполняют повторный root lookup. Полный production-CLI lifecycle работает в caller-owned linked worktree, primary branch/HEAD/tracked status не меняются.

## Контекст и ограничения

WP01–WP02 обязательны. Изменять только подтверждённые обходы общей boundary; не переписывать команды целиком. Сначала отдельный RED commit с production CLI acceptance.

## Подзадачи

### T011 — Зафиксировать RED полного lifecycle

Реальный временный Git linked worktree: create → status/context → setup-plan/tasks → implement/review transitions → next → accept. Снять branch/HEAD/status primary до и после. Добавить explicit root, два caller worktree и conflict CLI cases.

### T012 — Подключить selector, setup-plan и branch context

Resolve identity один раз, передать context в feature/read/commit path. Branch context показывает caller branch, не primary branch.

### T013 — Подключить status/tasks/action/next/accept

Заменить только подтверждённые entry-point обходы; существующая managed topology и diagnostics сохраняются.

### T014 — Добавить architectural guard

Repo-wide guard запрещает mission-scoped consumers повторно вызывать root lookup после получения context и фиксирует разрешённые foundation-callers.

### T015 — Финальная проверка и документация

Полный targeted/relevant suite, Ruff, mypy strict, cross-platform path cases, 100 повторов determinism, benchmark 100 Mission с p95 overhead ≤50 мс, `git diff --check`; краткая запись в CHANGELOG при observable fix.

## Риски и review

Риск — неполное покрытие команд и conflated commit target. Reviewer запускает production CLI из linked worktree и независимо проверяет primary через Git, а не через test fixture flags.

## Activity Log

- 2026-08-13T13:39:12Z – system – Prompt created.
- 2026-08-13T18:19:45Z – codex – shell_pid=20040 – Реализация завершена в lane-c: единый dual-root context проведён через status, setup, tasks, next, workflow и accept; RED f6368b27e, GREEN 512b3df33 + e16f5d355; 301 профильный тест, Ruff, mypy strict, py_compile, codemap 6/6 и diff-check прошли.

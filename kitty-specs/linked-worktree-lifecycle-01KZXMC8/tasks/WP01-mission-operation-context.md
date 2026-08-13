---
work_package_id: WP01
title: Mission-scoped checkout resolver
dependencies: []
requirement_refs:
- FR-001
- FR-005
- FR-006
- FR-007
- FR-008
- NFR-001
- NFR-003
- C-001
- C-002
planning_base_branch: codex/spec-kitty-worktree-mission-create
merge_target_branch: codex/spec-kitty-worktree-mission-create
branch_strategy: Planning artifacts for this mission were generated on codex/spec-kitty-worktree-mission-create. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/spec-kitty-worktree-mission-create unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-linked-worktree-lifecycle-01KZXMC8
base_commit: a2752629e21668e5e75b58f4078186dd6e10a6ef
created_at: '2026-08-13T13:56:49.963804+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Checkout resolution boundary
history:
- at: '2026-08-13T13:39:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: reviewer-renata
authoritative_surface: src/specify_cli/missions/operation_context.py
create_intent:
- src/specify_cli/missions/operation_context.py
- tests/specify_cli/missions/test_operation_context.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/missions/operation_context.py
- tests/specify_cli/missions/test_operation_context.py
role: reviewer
tags: []
task_type: implement
tracker_refs:
- spklw-rhr
---

# WP01 — Mission-scoped checkout resolver

## Цель и критерии успеха

Создать одну чистую boundary, которая возвращает `MissionOperationContext(repository_root, mission_anchor_root, identity, checkout_kind)` и ничего не пишет. Явный root остаётся авторитетным, managed checkout не переклассифицируется, caller-owned кандидат допускается только в том же Git common directory, split-brain завершается типизированной ошибкой.

## Контекст и ограничения

Прочитать `spec.md`, `plan.md`, `research.md`, `data-model.md` и `contracts/mission-operation-context.md`. Не менять глобальную семантику `locate_project_root()`/`get_main_repo_root()`. Переиспользовать существующую selector grammar. Сначала отдельный RED commit, затем production commit.

## Подзадачи

### T001 — Зафиксировать RED-контракты

Добавить production-path unit tests для caller-owned, explicit, managed, другого Git common directory, двух параллельных worktree и slug/ID split-brain. Коммит с тестами должен падать до production-кода.

### T002 — Ввести типы context и conflict

Реализовать immutable context, candidate kind и типизированную conflict-ошибку с безопасным диагностическим payload.

### T003 — Классифицировать candidate roots

Переиспользовать ближайший checkout и Git pointer primitives из `core/paths.py`; managed topology имеет приоритет, explicit root сужает множество до одного кандидата.

### T004 — Разрешить identity fail-closed

Использовать существующий Mission resolver на допустимых roots и дополнительно сверять совпадающий slug, чтобы full `mission_id` не скрывал конфликтующую копию.

### T005 — Проверить boundary

Targeted pytest, Ruff, mypy strict, determinism 100 повторов и `git diff --check`.

## Риски и review

Запрещены строковые проверки префикса пути вместо Git identity, silent fallback и новый selector parser. Reviewer должен удалить любую одну conflict-проверку и убедиться, что тест становится RED.

## Activity Log

- 2026-08-13T13:39:12Z – system – Prompt created.
- 2026-08-13T14:20:18Z – codex – shell_pid=28380 – Реализован read-only MissionOperationContext: отдельные RED-коммиты 3deb1c89a/a8dd239ef, production 1ba7e16f4; 71 targeted tests, Ruff и py_compile PASS; mypy нового модуля PASS, два baseline diagnostics core/paths без delta.
- 2026-08-13T14:33:03Z – codex – shell_pid=28380 – Исправлен pre-review blocker managed anchor: RED commit 53cbbb67e, GREEN ce5e94286; managed lane теперь сохраняет repository_root как PRIMARY anchor, current managed surface остаётся conflict-only probe; 71 targeted tests PASS.

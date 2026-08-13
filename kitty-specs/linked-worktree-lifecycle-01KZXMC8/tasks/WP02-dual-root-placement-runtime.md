---
work_package_id: WP02
title: Dual-root placement runtime
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-007
- NFR-001
- NFR-003
- C-002
- C-003
- C-004
planning_base_branch: codex/spec-kitty-worktree-mission-create
merge_target_branch: codex/spec-kitty-worktree-mission-create
branch_strategy: Planning artifacts for this mission were generated on codex/spec-kitty-worktree-mission-create. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/spec-kitty-worktree-mission-create unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Placement runtime
history:
- at: '2026-08-13T13:39:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/mission_runtime/resolution.py
create_intent:
- tests/mission_runtime/test_dual_root_mission_placement.py
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/architectural/test_single_mission_surface_resolver.py
- tests/mission_runtime/test_dual_root_mission_placement.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- spklw-rhr
---

# WP02 — Dual-root placement runtime

## Цель и критерии успеха

Провести два корня через существующий placement runtime: Git refs/topology/coord вычисляются от `repository_root`, PRIMARY metadata/planning — от `mission_anchor_root`, STATUS сохраняет stored topology. Managed behavior остаётся byte-identical.

## Контекст и ограничения

WP01 обязателен. Не создавать второй artifact partition или второй placement authority. `feature_dir` не может быть универсальным полем context. Сначала отдельный RED commit с тестами runtime.

## Подзадачи

### T006 — Зафиксировать RED placement matrix

Покрыть single-branch caller anchor, managed coord/lane, PRIMARY/STATUS kinds, conflict-free identity и отсутствие записи в repository-root checkout.

### T007 — Расширить placement seam dual-root входом

Сохранить совместимый default для существующих callers; новый context явно передаёт anchor. Не канонизировать anchor обратно через `get_main_repo_root()`.

### T008 — Провести dual-root через read/action runtime

Обновить `resolve_artifact_surface`, PRIMARY compose и action context так, чтобы topology использовала repository root, а PRIMARY — anchor root.

### T009 — Сохранить managed topology

Прогнать существующие coord/lane/read-path regressions; nested Mission create запрет остаётся прежним.

### T010 — Проверить runtime

Targeted и relevant regression pytest, Ruff, mypy strict, mutation удаления anchor-ветви, `git diff --check`.

## Риски и review

Главный риск — подмена одного корня другим внутри глубокой helper-цепочки. Reviewer проверяет PRIMARY и STATUS отдельно и подтверждает отсутствие нового raw path join.

## Activity Log

- 2026-08-13T13:39:12Z – system – Prompt created.
- 2026-08-13T15:26:59Z – codex – shell_pid=27296 – RED 4dc910b91: 4/4 dual-root production tests TypeError. GREEN fe14ed808 + architectural sanction 28a8b19ba: caller PRIMARY/flat STATUS остаются в mission anchor, repository_root владеет Git/topology. Проверки: 178 runtime, 51 read-path, 24 architectural, Ruff, py_compile, mypy strict, diff-check PASS. Mutation удаления anchor forwarding дал ожидаемый RED.

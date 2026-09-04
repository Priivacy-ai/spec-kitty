---
work_package_id: WP01
title: Изолировать проверку и сохранение документов
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-012
- FR-013
- FR-014
- FR-015
- FR-016
- FR-017
- FR-018
- FR-019
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
planning_base_branch: codex/explicit-worktree-repair
merge_target_branch: codex/explicit-worktree-repair
branch_strategy: Planning artifacts for this mission were generated on codex/explicit-worktree-repair. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/explicit-worktree-repair unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
- T015
- T016
- T017
phase: Локальный ремонт
history: []
authoritative_surface: src/specify_cli
create_intent:
- src/specify_cli/core/owned_mission.py
- tests/integration/test_explicit_checkout_commands.py
- tests/integration/test_owned_checkout_move_task.py
- tests/integration/test_owned_checkout_mark_status.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/accept.py
- src/specify_cli/acceptance/__init__.py
- src/specify_cli/acceptance/gates_core.py
- src/specify_cli/acceptance/execution_context.py
- src/specify_cli/migration/runtime_state_cutover.py
- src/specify_cli/migration/backfill_runtime_state.py
- src/specify_cli/core/owned_mission.py
- src/specify_cli/cli/commands/agent/mission_check_prerequisites.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/specify_cli/cli/commands/spec_commit_cmd.py
- src/mission_runtime/resolution.py
- src/specify_cli/coordination/commit_router.py
- src/specify_cli/coordination/status_transition.py
- src/specify_cli/coordination/transaction.py
- src/specify_cli/coordination/write_seam.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/acceptance/matrix.py
- src/specify_cli/tasks/issue_matrix.py
- src/specify_cli/status/bootstrap.py
- src/specify_cli/status/models.py
- tests/core/test_checkout_ownership.py
- tests/integration/test_explicit_checkout_commands.py
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_mark_status.py
- src/specify_cli/agent_tasks_ports.py
- src/specify_cli/task_utils/support.py
- src/specify_cli/cli/commands/agent/tasks_shared.py
- src/specify_cli/cli/commands/agent/tasks_parsing_validation.py
- src/specify_cli/workspace/context.py
- src/specify_cli/cli/commands/agent/tasks_materialization.py
- src/specify_cli/cli/commands/agent/tasks_finalize_validation.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- src/specify_cli/review/cycle.py
- src/specify_cli/status/emit.py
- tests/integration/test_owned_checkout_move_task.py
- tests/integration/test_owned_checkout_mark_status.py
- tests/specify_cli/cli/commands/test_tasks_move_task_cwd.py
- tests/specify_cli/cli/commands/agent/test_move_task_guard.py
- tests/specify_cli/cli/commands/agent/test_move_task_approval_evidence.py
- tests/specify_cli/cli/commands/agent/test_move_task_durability.py
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
- tests/specify_cli/cli/commands/agent/test_tasks_transition_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_mark_status.py
- tests/specify_cli/cli/commands/agent/test_tasks_mark_status_seam.py
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py
- tests/specify_cli/status/test_infer_subtasks_primary.py
- tests/specify_cli/cli/commands/agent/test_issue_2684_subtask_completion_event_sourced.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_baseline_read.py
- tests/specify_cli/cli/commands/agent/test_move_task_rollback_clears_claim.py
- tests/review/test_verdict_seam_reader_collapse.py
- tests/integration/test_2939_move_task_clean_tree_after_rejection.py
- docs/codemap/*
tags: []
task_type: implement
tracker_refs: []
---

# Изолировать проверку и сохранение документов

## Критерии

Все требования из spec.md. Реальная CLI проверка, отдельное сохранение и
обычная финализация завершаются в выбранном checkout. Ошибочные корни, ветки,
пути и неподдерживаемые сочетания отвергаются до записи.

## Порядок

T001 сохраняет исходные assertions Windows теста. T002 сначала доказывает
потерю корня существующей командой, а не только отсутствие нового CLI-флага.
T003 использует существующий canonical resolver и transaction.
T004 сравнивает неизменность primary и sibling и ловит значимую мутацию
ожидаемого пути. T005 требует отдельного reviewer и повторной проверки.

## Проверка

`python -m pytest tests/integration/test_explicit_checkout_commands.py
tests/core/test_checkout_ownership.py -q`

Дополнительно выполнить связанные тесты размещения, commits и статусов,
`ruff check`, `mypy` для изменённых модулей и `git diff --check`.
Нельзя считать пропуск тестов успешной проверкой. Не выполнять publish,
глобальный upgrade, ручной lifecycle-переход или обход защиты ветвей.

Расширение T006-T008: дополнительно требования FR-008..FR-010, SC-007..SC-008.
Затронутые проверки: `tests/specify_cli/acceptance/`,
`tests/specify_cli/cli/commands/test_accept*.py` и интеграционные тесты явного корня.

## Дополнение смены статуса для согласования

T009-T013 покрывают FR-011..FR-015 и SC-009..SC-012. Старое техническое ревью
не распространяется на будущий diff. Формальная приёмка находится за пределами
подзадач реализации и выполняется после канонического одобрения пакета.

1. T009 обновляет вместе JSON, HTML и lock карты кода. Затем отдельный commit
   сохраняет красный тест потери корня через `tasks.app`, не parser error.
2. T010 использует `OwnedMission`; отдельная проверенная ревизия сравнения
   нужна только для переходов с проверками реализации/актуальности ревью.
3. T011 проводит контекст через существующие writers, включая снятие назначения
   при `in_review -> planned` и компенсацию технического сбоя после verdict.
4. T012 запускает новый `tests/integration/test_owned_checkout_move_task.py`
   и перечисленные выше regression-файлы. Подмены writers/guards не являются
   единственным доказательством. Проверяются байты документов/событий/review,
   HEAD, index и статус всех рабочих копий, значимые annotations и отсутствие
   fallback при совпадающих именах. Сбой компенсации сообщает частичный результат.
5. T013 добавляет существенную мутацию root/base и отдельно одного ожидаемого
   статуса. Требуются содержательные падения и восстановленный зелёный набор,
   Ruff, mypy с отдельным учётом старых ошибок, независимый reviewer и повтор
   основной сессией. Цель покрытия нового кода: более 90 процентов.

Работать последовательно только в этом checkout. Новый command/runtime install,
изменение формата metadata, ослабление guards и изменения вне прямой цепочки
требуют отдельного согласования. Нельзя автоматически исправлять review base
самой ремонтной работы или проверять код переходами реального исходного навыка.

## Дополнение отметки подзадач для согласования

T014-T017 покрывают FR-016..FR-019 и SC-013..SC-015. T014 сохраняет карту и
реальный RED. T015 проводит проверенное владение только через read/context
границы. T016 использует существующий transactional annotation writer с
`effective_root`, не отдельный commit, и фиксирует честный partial result для
последовательного multi-WP batch. T017 проверяет real Git, fault injection,
содержательные мутации, совместимость и независимое ревью точного diff.

Ambient sync/history/error/dossier APIs не меняются и в owned-режиме не
вызываются. Формат status event и reducer не меняются. Код до отдельного
согласования этого дополнения не менять.

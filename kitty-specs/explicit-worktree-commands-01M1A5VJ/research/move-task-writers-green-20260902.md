# Writers выбранной рабочей копии

## Реализовано

- owned-режим поддерживает вход в ревью, одобрение и мотивированный возврат;
- status lock, verdict queue, review-cycle allocation, durable readback и
  компенсация используют выбранный корень;
- reviewer annotation сохраняет implementer assignment и отдельную роль
  reviewer;
- `in_review -> planned` сохраняет rejected review-cycle, сбрасывает подзадачи
  и снимает runtime claim;
- технический сбой после durable verdict удаляет verdict компенсационным
  коммитом в выбранной копии;
- глобальный error writer с неявным корнем не вызывается в owned-режиме;
- primary и соседняя рабочая копия остаются неизменными.

## Проверки

- RED-коммит `c38e261b6`: два новых writer-сценария падали с
  `OWNED_TRANSITION_UNSUPPORTED`;
- owned integration: исходный полный прогон **34 passed**; финальный повтор дал
  **33 passed, 1 setup error** на `git status` временного fixture-worktree, а
  изолированный повтор этого сценария — **1 passed**;
- прямые compatibility-сценарии verdict writers: **11 passed**;
- consolidated compatibility guard: **351 passed**;
- durability/rollback: **39 passed, 2 failed**; обе ошибки воспроизведены на
  RED-коммите и относятся к Windows-разделителям в `git show`;
- review-cycle regression: **51 passed, 7 failed**; те же семь ошибок
  воспроизведены на RED-коммите и зависят от CRLF/Windows path separators;
- pre-existing Windows-дефекты зарегистрированы в
  https://github.com/Priivacy-ai/spec-kitty/issues/3834 .
- `ruff` по изменённым source/test-файлам: успешно;
- `mypy --strict` по четырём source-модулям: одно известное базовое сообщение
  `tasks_move_task.py:1248 [no-any-return]`, новых сообщений нет.

T012 сохраняет ответственность за совокупную проверку всего lifecycle; T013 —
за смысловые мутации и независимое ревью. Установка, push и публикация патча не
разрешены.

# Контекст writers выбранной рабочей копии: RED

Дата: 2026-09-02. Аудитория: разработчик CLI.

Добавлены два реальных CLI-сценария для `move-task --owned-checkout`:

- цепочка `for_review -> in_review -> approved` должна сохранить status,
  reviewer annotation и review-cycle только в выбранной рабочей копии;
- сбой status transition после durable verdict должен компенсировать review-cycle
  в той же рабочей копии и оставить фактический статус `in_review`.

Изолированный запуск:

`pytest tests/integration/test_owned_checkout_move_task.py --confcutdir=tests/integration
-p no:cacheprovider -q -k 'owned_review_and_approval or
owned_approval_emit_failure'`

Результат: **2 failed, 31 deselected**. Оба теста падают на ожидаемом текущем
ограничении `OWNED_TRANSITION_UNSUPPORTED` при переходе в `in_review`, после
успешного входа в `for_review`. Это содержательный RED существующего entrypoint,
а не parser, fixture или import failure.

Рабочее поведение этим checkpoint не меняется. T011 остаётся открытой; push,
установка, публикация и переходы реальных пользовательских работ не выполнялись.

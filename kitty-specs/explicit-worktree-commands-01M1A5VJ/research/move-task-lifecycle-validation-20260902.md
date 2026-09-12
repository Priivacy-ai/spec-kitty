# Проверка lifecycle выбранной рабочей копии

## Покрытый контракт

- успешная последовательность событий:
  `planned -> claimed -> in_progress -> for_review -> in_review -> approved`;
- алиас `doing`, actor/assignment, PID, reviewer role и durable evidence;
- мотивированный `in_review -> planned` со снятием runtime claim;
- сбой перехода после verdict с успешной компенсацией;
- сбой самой компенсации с ненулевым кодом, `result=error`,
  `verdict_durably_persisted=true` и сохранённым фактическим evidence;
- сбой annotation без ложного сообщения об успехе;
- ранний отказ неверного корня, ветки, topology, staged index, active sync,
  `done`, force/skip и отключённого auto-commit;
- чистота выбранного Git-дерева и неизменность primary и соседней копии,
  включая index.

## Доказательства

- предыдущий полный owned integration на GREEN-коде T011 подтвердил все 34
  существовавших сценария; единичный поздний setup-сбой временного Git-worktree
  прошёл при изолированном повторе;
- новый owned compound-failure сценарий: **1 passed**;
- успешный lifecycle с точной последовательностью событий: **1 passed**;
- повтор назначения, успешной компенсации, возврата и annotation failure:
  **4 passed, 31 deselected**;
- consolidated compatibility guard: **351 passed**;
- `ruff` для изменённого integration-теста: успешно;
- `git diff --check`: успешно;
- предсуществующие Windows CRLF/path-separator сбои остаются отдельно в
  https://github.com/Priivacy-ai/spec-kitty/issues/3834 .

T012 не меняет product-код: добавлена только проверка неполной компенсации и
усилена проверка точной цепочки событий. T013 отвечает за смысловые мутации,
независимое ревью совокупного diff и финальный повтор. Push, установка и
публикация патча не выполнялись.

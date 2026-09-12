# План owned-режима `mark-status`

## Причина

После canonical bootstrap WP01 находится в `in_progress`, но T001-T013 всё ещё
`pending` в event-sourced состоянии. Текущий `mark-status` канонизирует worktree
в primary и не может безопасно завершить эти подзадачи в selected checkout.

## Baseline

- Добавить только `mark-status --owned-checkout` для `single_branch`.
- Проверять владение, mission, ветку, protection policy, index, auto-commit и
  inactive sync до чтения или записи.
- Читать TASKS_INDEX через `MissionHandle.effective_root`.
- Писать status только через
  `emit_inner_state_changed_transactional(..., effective_root=...)`; отдельный
  status commit не добавлять.
- Не вызывать ambient history, error-log и dossier hooks в owned-режиме.
- Для нескольких WP выполнять последовательные транзакции и при позднем сбое
  сообщать applied WP, event IDs, destination и фактическое состояние.
- Считать materialization/readback failure ошибкой, а не успехом со stale
  snapshot. Обычный режим и его patch seams не менять.

## Проверка плана

`check-prerequisites --owned-checkout --include-tasks` прошёл без ошибок и
предупреждений. `finalize-tasks --validate-only --owned-checkout` сначала точно
указал на отсутствующий `create_intent` нового integration-файла; после
исправления вернул `validation_passed`, без ownership и requirement warnings.
Независимый read-only аудит сначала вернул `CHANGES_REQUIRED`:
он отклонил обычный emitter плюс отдельный commit, потребовал существующий
transactional writer, точную multi-WP partial semantics и materialized tasks.
Все три замечания включены в итоговый baseline T014-T017.
Повторное независимое чтение исправленного baseline вернуло `APPROVE`.

## Gate

Реализация, реальные `mark-status` записи и дальнейший lifecycle не выполнялись.
Требуется отдельное согласование baseline. Push, PR, merge, install и publication
не разрешены этим планом.

# Финальная проверка расширения move-task

## Смысловые мутации

Проверки выполнены в отдельной временной рабочей копии на `4470f26c2`, после
чего она удалена штатным `git worktree remove` без `--force`.

- Замена выбранного `effective_root` на отсутствие корня дала осмысленный
  отказ `no_op_wrong_surface`: команда попыталась писать в защищённую `main`,
  а артефакт остался вне commit.
- Изменение ожидаемой lane с `approved` на `planned` дало сравнение фактической
  `approved` с мутированным ожиданием. Это подтверждает наблюдаемый lifecycle,
  а не только прохождение fixture или parser.

## Независимое ревью и ремонт

Первое независимое ревью совокупного diff вернуло `BLOCK` с тремя P1:

1. lifecycle-only commits могли считаться реализацией;
2. auto-commit мог захватить путь вне `owned_files`;
3. сбой annotation после durable transition откатывал уже referenced verdict и
   не сообщал частично применённое состояние.

Для каждого замечания сначала добавлен отдельный RED integration-сценарий.
Ремонт требует committed delta в authored `owned_files`, проверяет всю dirty
пачку до staging и отличает сбой до первого transition от сбоя после него.
После durable transition команда сохраняет referenced verdict и возвращает
`result=error`, `transition_applied=true` и фактические durability-поля.
Старый режим без `--owned-checkout` не изменён.

Повторное независимое read-only ревью точного diff от `4470f26c2` вернуло
`APPROVE`; блокирующих замечаний нет.

## Проверки

- полный owned integration: **38 passed**;
- новые guards, partial envelope и обе прежние компенсации: **6 passed**;
- повтор owned-сценариев после compatibility-ограничения: **4 passed**;
- compatibility identity surface: **361 passed**;
- расширенный compatibility/durability прогон: **362 passed**, два известных
  Windows backslash сбоя из issue #3834;
- Ruff для изменённых Python-файлов: успешно;
- `git diff --check`: успешно;
- `codemap.json` разбирается, SHA-256 JSON/HTML совпадают с `codemap.lock`;
- mypy для `tasks_move_task.py`: один прежний `no-any-return` в нетронутой
  функции, новых ошибок нет.

Остаточные неблокирующие пробелы: нет отдельного сценария для сложного
wildcard `owned_files` и multi-hop сбоя между переходами. Push, установка и
публикация не выполнялись.

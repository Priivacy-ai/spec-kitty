# Зелёная реализация owned mark-status

Дата: 2026-09-02

## Реализовано

- `mark-status` получил добавочный `--owned-checkout` для `single_branch` mission.
- До чтения и записи проверяются принадлежность checkout, точная target-ветка,
  topology, protected branch, staged index, активная синхронизация и обязательный
  auto-commit.
- `TASKS_INDEX` и `STATUS_STATE` разрешаются через один `effective_root`.
- Изменение каждой группы подзадач одного WP проходит через
  `emit_inner_state_changed_transactional`; выбранный checkout остаётся чистым.
- Успешный JSON содержит checkout, destination ref, commit, пути status,
  event IDs и применённые WP.
- При позднем multi-WP сбое JSON честно сообщает закоммиченный префикс через
  `state_applied`, `event_ids` и `applied_wps`.
- В owned-режиме не вызываются ambient history, error и dossier writers без
  explicit-root контракта. Путь без флага сохранён.

## Проверки

- `tests/integration/test_owned_checkout_mark_status.py`: 15 passed.
- Старые `mark-status`, seam, compatibility и event-sourced наборы: 404 passed.
- `ruff check` изменённых Python-файлов: passed.
- Real-Git проверки подтвердили неизменность primary и соседнего worktree,
  включая одноимённую теневую mission и запуск из соседнего cwd.
- Materialization fault откатывает event и snapshot побайтно; checkout чист.
- Инъекция сбоя второго WP оставляет только первый транзакционно закоммиченный
  WP и возвращает ненулевой структурированный результат.
- Первое независимое ревью выявило P2: общий filesystem scan мог приписать
  текущей команде событие конкурентного writer. Обычная ошибка теперь сообщает
  только события, возвращённые её транзакциями; recovery-after-commit читает
  новые event IDs только из точного `commit_sha` относительно его parent.
- Отдельные тесты подтверждают, что конкурентное событие не попадает в envelope,
  а точный post-commit recovery event сохраняется в нём.

## Оставшийся gate

T017 остаётся открытой до повторного независимого ревью исправления P2,
финального повтора проверок и применения нового CLI к canonical подзадачам этой
mission. Push, PR, merge, установка и публикация не разрешены.

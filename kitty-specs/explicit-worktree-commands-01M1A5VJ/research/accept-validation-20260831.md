# Проверка локального расширения приёмки

## Результат

`accept --owned-checkout` поддерживает проверенную single_branch работу.
Диагностика читает выбранные документы и не обновляет матрицу. Обычная приёмка
сохраняет матрицу, метаданные, события переноса статусов и итоговую отметку
в выбранном checkout; остаточные артефакты попадают в локальный commit.
Непустой index, неподходящие ветки, topology и внешние пути отклоняются.
Без флага сохранён прежний маршрут, включая best-effort финальную отметку.

Обнаруженный тестом повторный primary fold устранён в существующей цепочке
seed/verify/flip. Точное владение обоими каталогами проверяется до первой записи.
Общий canonicalizer, event store и reducer не менялись. Неуспех финальной отметки
в явном режиме теперь даёт ненулевой exit, а не ложное успешное завершение.

## Проверки

- RED сохранён коммитом `e6e791e04`: прежний entrypoint теряет работу; нового
  параметра ещё нет. Parser RED сам по себе не считается проверкой поведения.
- Финальный `tests/integration/test_explicit_checkout_commands.py`: **78 passed**.
  Полная приёмка проверяет commit, чистый index, реально добавленные события,
  `status_phase=1`, неизменность primary/sibling и повтор без дубликатов.
- Совместимость миграции и разделения остатков: **52 passed**.
  Файлы: `test_accept_residual_partition.py`, `test_runtime_state_cutover.py`,
  `test_runtime_state_cutover_placement.py`, `test_cutover_partition_decouple.py`,
  `test_backfill_cutover_guard.py` в `tests/specify_cli/`.
- Расширенная совместимость: **212 passed, 1 skipped**. Набор:
  `tests/specify_cli/acceptance/`, `test_accept_no_commit_readonly.py`, команды
  `test_accept_clean_tree.py`, `test_accept_readiness_no_write.py`,
  `test_accept_normalize_encoding.py`, `test_accept_residual_partition.py`,
  `test_accept_birth_cutover_seam.py`. Наборы частично пересекаются; пропуск
  не считается подтверждённым поведением.
- Значимая мутация только в памяти отдельного тестового процесса вернула старый
  canonicalizer вместо owned root. Положительный тест упал на сравнении снимка
  primary: изменился `status.events.jsonl`. Это AssertionError поведения,
  не parser/fixture failure. После мутации полный набор прошёл без неё.
- Ruff восьми изменённых Python-файлов: passed. Штатный статический анализ
  assertions времени для изменённого теста: нарушений нет. `git diff --check`: passed.
- Mypy семи production-модулей: **две существующие ошибки**, те же в архиве
  `e6e791e04`: наследование от Any TaskCliError и Any-результат чтения WP snapshot.
  Новых сообщений нет; общая проверка типов не объявляется зелёной.
- Независимое read-only ревью: APPROVE. Parent повторил полный набор и hash diff:
  `72695b5c57591c08f46c49d60f365e50ba97e06de95546ff662bbec87bb2a0b7`.

Тесты запускались с временными HOME/USERPROFILE/SPEC_KITTY_HOME/APPDATA/TEMP,
`python -B`, `--confcutdir` для выбранной группы и без pytest cache.
Git Unix tools были добавлены только в PATH процесса для grep-инварианта.
Полная root collection не выполнена; особенности запусков описаны отдельно
в `tooling-friction.md`. Настройки пользовательской среды не менялись.

## Исходный навык

Изолированный standalone Typer entrypoint с Python audit hook выполнил
`accept --mission cli-opportunity-01M1A3X5 --owned-checkout <skill-worktree>
--diagnose --json`. Получены exit 0, diagnose=true, правильный feature_dir,
primary_repo_root отдельно и пустой список запрещённых попыток.
Это диагностика, **ok=false**, не формальная приёмка:

- Нет канонического журнала статусов; пакет остаётся planned, отсутствует agent.
- Проверка software-dev ожидает `src/` и `contracts/`; структура навыка другая.
- Git чистый; документы найдены, незакрытых пунктов и уточнений нет.

Файлы исходного навыка не менялись. Его локальный commit остаётся `fe7ea12`.
Установка, публикация и ручные lifecycle-переходы не выполнялись.

## Ограничения

Дополнительная проверка документов самой ремонтной работы через тот же audit
hook остановлена до сетевого `git remote show origin`: локальный origin/HEAD
отсутствует, существующая protection policy пытается уточнить его через remote.
Ограничение не ослаблялось, refs/config не исправлялись; эта проверка не пройдена.
Формальная приёмка ремонтной работы остаётся открытой.

Python audit hook не является OS sandbox. Гарантия тестов не распространяется
на произвольные команды custom invariants, Git hooks и конкурентного внешнего
writer. Изолированного запуска root CLI с настоящим HOME, глобального ремонта,
установки, push, PR и release в этом пакете нет.

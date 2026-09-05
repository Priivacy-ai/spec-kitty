# Проверка локальной PR-ветки

Дата: 2026-09-02

Принятый результат перенесён из `codex/explicit-worktree-repair` в отдельную
ветку `codex/explicit-worktree-pr-prep` от точного `upstream/main`
`87d851382fc50cd789ba542b28dbc4bc0fb37618`. Перед публикацией task-ветка
перебазирована на восемь новых upstream-коммитов без конфликтов; исходная ветка
и primary не переписывались.

История сжата до смысловых коммитов: production и codemap, acceptance-тесты,
mission-артефакты, Windows help snapshots и type-only call-shape repair.
При подготовке устранены два delivery-дефекта без изменения поведения:

- help-нормализатор теперь одинаково обрабатывает rounded и Windows safe-box
  углы Rich; golden snapshot `move-task` фиксирует добавленный
  `--owned-checkout`;
- условный `effective_root` передаётся типизированно с сохранением прежнего
  отсутствующего keyword в flagless call-shape.

## Проверки

- real-Git owned integration: **131 passed** после rebase; на Windows для
  `grep_absence` в `PATH` явно добавлен установленный Git for Windows
  `usr/bin`;
- help, CLI и compatibility: **397 passed**;
- ownership: **21 passed**;
- Ruff всех изменённых Python-файлов: passed;
- `git diff --check`: passed;
- Mypy 31 изменённого production-модуля: 22 базовых сообщения против тех же 22
  сообщений и категорий в 30 существующих модулях на актуальном
  `upstream/main`; новый `owned_mission.py` проверен, новых сообщений нет;
- SHA-256 Git blobs `codemap.json` и `codemap.html` совпадают с
  `codemap.lock`;
- временные test/mypy каталоги удалены.

Rich документирует влияние `TERM`, `NO_COLOR`, `TTY_COMPATIBLE` и явных размеров
Console: https://rich.readthedocs.io/en/latest/console.html . Pytest загружает
родительские и вложенные `conftest.py` по directory scope:
https://docs.pytest.org/en/stable/example/simple.html . Выбран test-only
нормализатор обеих допустимых box-схем вместо зависимости от терминала.

На момент фиксации этого локального receipt push, создание PR, merge, установка
и публикация не выполнялись.

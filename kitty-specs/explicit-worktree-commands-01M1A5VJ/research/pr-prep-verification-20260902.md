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

## Исправление первого CI-прогона

После публикации draft PR `#3843` первый CI run `33671963646` завершился с
девятью предметными assertions в пяти jobs и отдельным enforced
diff-coverage blocker:

- owned-путь `acceptance` напрямую импортировал запрещённый архитектурным gate
  `mission_context_for`;
- новый read-only join baseline-файла отсутствовал в обязательном
  `untrusted_path_audit` inventory, из-за чего падали два assertions.
- routed metadata census вырос до 155, но его нижний ratchet остался на 150;
- flagless pre-review scope ошибочно выбирался от текущего checkout вместо
  прежнего `main_repo_root`;
- `_MoveTaskArgs` и frozen CLI flag surfaces не учитывали новые
  `owned_checkout` / `--owned-checkout`;
- старый unit-fixture без поля `owned` ломал runtime-state emitter;
- новый owned `move-task` integration-файл находился в общем integration-shard,
  который намеренно не запускается для draft PR, поэтому критический diff
  coverage составлял только 43%.

Локальная remediation оставляет flagless путь без изменений, а owned-проверку
топологии маршрутизирует через существующий `declared_home_surface`. Baseline
join зарегистрирован как `trusted-source`: `wp_slug` выводится из канонически
разрешённого `st.wp.path.stem`, а родительский каталог является проверенной
owned mission directory. Scope-source теперь выбирает `main_repo_root` для
flagless-вызова и explicit checkout только для owned-вызова. Контрактные наборы
обновлены, runtime emitter использует совместимый optional lookup, а 39 owned
`move-task` случаев перенесены в CLI integration-shard, который выполняется и
для draft PR.

Повторная локальная проверка:

- оба затронутых architectural файла: **26 passed**;
- три исходных CI assertions: **3 passed**;
- routed census assertion: **1 passed**;
- весь `move-task` degod contract: **7 passed**;
- frozen mission CLI flags: **10 passed**;
- flagless/owned scope-root smoke: passed;
- owned baseline-read regression: **1 passed**;
- existing owned `move-task` integration: **38 passed**;
- CLI selector собирает все **39** owned `move-task` cases;
- owned accept regressions: **4 passed**;
- критический diff coverage: **90%**; `tasks_move_task.py` — **91.2%**,
  `tasks_verdict_persistence.py` — **100%**;
- `untrusted_path_audit`: **40 rows**, из них 35 AST-discovered и 5
  inventory-only;
- Ruff и `git diff --check`: passed.

Linux CI parity-test для `scope_source_root` на локальной Windows-среде
останавливается раньше проверяемой строки: его declared-command fixture не
создаёт baseline. Корневое ветвление проверено отдельным unit-smoke; окончательное
Linux-подтверждение остаётся за повторным CI после разрешённого push.

Исправление локально закоммичено; новый push в существующий PR остаётся
отдельным внешним gate.

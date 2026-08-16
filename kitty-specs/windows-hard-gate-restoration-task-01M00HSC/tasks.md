# Задачи: восстановить hard-gates Spec Kitty на Windows

## Обзор

Работа разделена на три последовательных пакета без параллельного ownership. Первый устраняет Windows portability и collection defects в test/gate harness. Второй на уже честном oracle классифицирует реальные architecture drifts, исправляет topology boundary и синхронизирует code map. После их принятия полный Windows architecture packet выявил четыре остаточных baseline-класса; третий пакет закрывает только их и повторяет полную локальную приёмку. Внешний E2E остаётся отдельным release-gate.

## Индекс подзадач

| ID | Краткое содержание | Пакет | Параллельно |
|---|---|---|---|
| T001 | Создать GitHub issue о pre-existing hard-gate failures | WP01 | Нет |
| T002 | Зафиксировать отдельный RED commit для null sink, EUID, separators и collection | WP01 | Нет |
| T003 | Выполнить ограниченный tidy-first осмотр owned test surfaces | WP01 | Нет |
| T004 | Реализовать platform-safe oracles с независимым static expected inventory | WP01 | Нет |
| T005 | Закрыть collection семи файлов и dependent coverage/shard/session-reaper | WP01 | Нет |
| T006 | Доказать mutation sensitivity и выполнить targeted gates | WP01 | Нет |
| T007 | Зафиксировать RED для missing inventories и raw topology predicate | WP02 | Нет |
| T008 | Выполнить tidy-first и read-only codemap baseline | WP02 | Нет |
| T009 | Классифицировать каждый architecture signal и исправить owning boundary | WP02 | Нет |
| T010 | Синхронизировать inventories и code map в production commit | WP02 | Нет |
| T011 | Доказать negative/mutation sensitivity и targeted GREEN | WP02 | Нет |
| T012 | Выполнить local acceptance на финальном SHA и external E2E availability gate | WP02 | Нет |
| T013 | Сформировать SHA-bound handoff и закрыть tracers | WP02 | Нет |
| T014 | Зафиксировать четыре residual-класса отдельным RED на approved WP02 SHA | WP03 | Нет |
| T015 | Нормализовать Windows repo-relative keys в doctrine/kernel gates и seed digest | WP03 | Нет |
| T016 | Сохранить committed mission-exit node-id при capability fallback и проверить официальный width run | WP03 | Нет |
| T017 | Реконсилировать golden-count marker и воспроизводимо перегенерировать ceilings | WP03 | Нет |
| T018 | Убить mutations, выполнить targeted GREEN и статические проверки | WP03 | Нет |
| T019 | Выполнить полный contract/architecture gate на неизменённом SHA | WP03 | Нет |
| T020 | Обновить acceptance matrix, hard-gate result, tracers и SHA-bound handoff | WP03 | Нет |

## WP01 — Windows portability и collection closure

**Приоритет**: P1

**Prompt**: `tasks/WP01-windows-portability-collection.md`

**Зависимости**: отсутствуют

**Depends on**: none

### Результат

Contract null sink, EUID checks и repo-relative census работают на Windows; семь известных файлов собираются без ошибок; зависимые coverage/shard/session-reaper gates больше не падают вследствие platform collection. Static expected inventories остаются независимыми и mutation-sensitive.

### Подзадачи

- [ ] T001 Создать charter-required GitHub issue с исходными командами и counts (WP01)
- [ ] T002 Закоммитить RED-first acceptance tests до implementation fixes (WP01)
- [ ] T003 Выполнить tidy-first только внутри owned files либо записать `none found` evidence (WP01)
- [ ] T004 Заменить `/dev/null`, безопасно ограничить EUID oracle и нормализовать только actual repo-relative paths (WP01)
- [ ] T005 Добиться `0 collection errors` для семи файлов и зелёных dependent gates (WP01)
- [ ] T006 Убить обязательные mutations, прогнать targeted pytest/Ruff/py_compile/diff-check и передать в review (WP01)

### Параллельность

WP01 не трогает production topology, architecture inventories WP02 и code map. Реализация последовательна; независимый read-only review обязателен после GREEN.

## WP02 — Architecture classification, topology remediation и acceptance

**Приоритет**: P1

**Prompt**: `tasks/WP02-architecture-remediation-acceptance.md`

**Зависимости**: WP01

**Depends on**: WP01

### Результат

Missing sink и raw topology predicate классифицированы независимыми oracles; реальный boundary bypass исправлен до inventory sync либо узкое исключение доказано negative test. Code map отражает callers/impact/tests. На одном финальном SHA локальные hard-gates зелёные, а внешний E2E state отделён от завершённости реализации и не green-wash'ится.

### Подзадачи

- [ ] T007 Закоммитить RED для текущих missing sink/raw predicate сигналов (WP02)
- [ ] T008 Выполнить tidy-first и read-only baseline текущей code map (WP02)
- [ ] T009 Классифицировать и исправить каждый owning architecture boundary без blanket allowlist (WP02)
- [ ] T010 Синхронизировать точечные inventories и все три code map artifacts в production commit (WP02)
- [ ] T011 Доказать negative/mutation sensitivity и targeted GREEN (WP02)
- [ ] T012 На финальном SHA выполнить полные contract/architecture gates и external E2E access/result check (WP02)
- [ ] T013 Обновить mission evidence, issue и tracers; зафиксировать `implementation_complete`, `local_ready`, `e2e_ready`, `release_ready` (WP02)

### Параллельность

WP02 начинается только после approved WP01 и наследует его platform-safe oracle. Пересекающихся owned files нет. Full architecture run запускается после targeted GREEN; новый failure возвращается в owning subtask и после исправления требует нового full run на новом финальном SHA.

## WP03 — Windows-stable baseline closure и честная local acceptance

**Приоритет**: P1

**Prompt**: `tasks/WP03-windows-stable-baseline-closure.md`

**Зависимости**: WP02 approved

### Результат

Четыре подтверждённых остаточных класса закрыты без ослабления gates:

1. doctrine/kernel census используют POSIX repo-relative keys на Windows;
2. glossary seed integrity проверяется по каноническому содержимому, не требуя
   редактировать seed или ломаясь на CRLF checkout;
3. golden-count baseline отражает фактический merge-base/current scan, а новый
   cardinality-only helper явно annotated;
4. committed mission-exit floor сохраняет прежний parametrized node-id при
   capability fallback.

CLI width guard запускается также в официальном окружении с корневой
`tests/conftest.py`; его диагностический `--confcutdir`-red не превращается в
production fix и не меняет local-ready verdict.

### Подзадачи

- [ ] T014 Снять current residual packet на approved WP02 SHA и закоммитить
  test-only RED до любых GREEN-правок; отдельно записать, что width в полном
  окружении зелёный, а `--confcutdir` — диагностический режим.
- [ ] T015 Исправить только path/hash seams: `.as_posix()` для actual census keys,
  newline-normalized seed digest с mixed-newline guard; сохранить независимые
  static expected values. Добавить targeted negative tests.
- [ ] T016 Зафиксировать прежний `pytest.param` id явным `id=...`, оставить
  capability skip fail-closed и доказать, что committed floor не shrink'ится.
- [ ] T017 Пометить только настоящий cardinality-only site, запустить штатный
  `--freeze-baseline`, сверить ceilings с merge-base evidence и не уменьшать floor.
- [ ] T018 Выполнить все mutations: slash mismatch, raw CRLF/LF drift, удаление
  explicit id и снятие cardinality marker; затем targeted pytest/Ruff/py_compile/
  diff-check.
- [ ] T019 На неизменённом SHA выполнить полный `tests/contract` и
  `tests/architectural`; collection/errors/failures сохранить дословно.
- [ ] T020 Обновить hard-gate result и acceptance matrix (`local_ready` только при
  полном зелёном architecture), закрыть tracers и передать SHA-bound handoff.

### Owned files

- `tests/architectural/test_doctrine_census.py`
- `tests/architectural/test_kernel_no_doctrine_import.py`
- `tests/architectural/test_glossary_pack_no_regression.py`
- `tests/architectural/test_golden_count_ban.py`
- `tests/architectural/_golden_count_baseline.json`
- `tests/architectural/test_mission_exit_baseline.py`
- `tests/review/test_pre_review_gate_engine.py`
- `tests/contract/test_machine_facing_canonical_fields.py`

### Ограничения

- Не редактировать `.kittify/glossaries/spec_kitty_core.yaml`.
- Не менять `mission_exit_baseline.txt` для маскировки исчезнувшего node-id.
- Не расширять `ORPHAN_REACHED_EXCEPTIONS`: текущий orphan-сигнал классифицирован
  как Windows-разделитель, поскольку четыре файла уже принадлежат WP05–WP07.
- Не принимать `--confcutdir`, timeout или partial collection за полный gate.
- WP01/WP02 product surfaces не меняются параллельно; этот пакет идёт только после
  их approval.

### Проверки

- RED-first packet показывает каждый residual failure и два положительных контроля.
- Targeted GREEN всех восьми owned files, включая independent path/hash/node-id
  oracles.
- Минимум четыре временные mutations убиты ожидаемым тестом и восстановлены.
- Полный contract и architecture на exact final SHA: `0 failed`, `0 errors`;
  documented skip/xfail перечислены отдельно.
- Clean lane, diff-check, Ruff, py_compile; если затронуты code-map boundaries,
  parity/hash обновляются в том же commit.

### Параллельность

WP03 последовательен после WP02. Если полный run найдёт новый root-cause, пакет
останавливается и создаётся отдельный follow-up WP, а не добавляется широкая
allowlist или operator exception.

## Общая готовность

- Оба пакета соблюдают отдельный RED commit до implementation commit.
- Никакой blanket skip, count-floor reduction, wildcard allowlist или operator exception не добавлен.
- Contract и architecture suites на окончательном SHA имеют `0 failed`, `0 errors`;
  до WP03 acceptance matrix честно показывает `local_ready=false`.
- External E2E отсутствие доступа допускает `implementation_complete=true`, но оставляет `e2e_ready=false` и `release_ready=false`.
- Handoff указывает exact SHA, после которого файлы не менялись.
- Beads не используется до отдельного исправления task-local resolver; глобальная DB не изменяется.

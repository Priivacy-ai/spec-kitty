# Задачи: восстановить hard-gates Spec Kitty на Windows

## Обзор

Работа разделена на два последовательных пакета без пересекающегося ownership. Первый устраняет только Windows portability и collection defects в test/gate harness. Второй на уже честном oracle классифицирует реальные architecture drifts, исправляет topology boundary при необходимости и синхронизирует code map. Полный local suite и внешний E2E являются приёмочными gates, а не отдельными implementation packages.

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

## Общая готовность

- Оба пакета соблюдают отдельный RED commit до implementation commit.
- Никакой blanket skip, count-floor reduction, wildcard allowlist или operator exception не добавлен.
- Contract и architecture suites на окончательном SHA имеют `0 failed`, `0 errors`.
- External E2E отсутствие доступа допускает `implementation_complete=true`, но оставляет `e2e_ready=false` и `release_ready=false`.
- Handoff указывает exact SHA, после которого файлы не менялись.
- Beads не используется до отдельного исправления task-local resolver; глобальная DB не изменяется.

# Задачи: восстановить hard-gates Spec Kitty на Windows

## Обзор

Работа разделена на последовательные пакеты без параллельного ownership. Первый устраняет Windows portability и collection defects в test/gate harness. Второй на уже честном oracle классифицирует реальные architecture drifts, исправляет topology boundary и синхронизирует code map. Третий пакет закрыл свои четыре Windows-stable класса, но полный architecture packet на его SHA выявил четыре новые группы residual/root-cause. Они вынесены в WP04–WP05; финальный прогон выявил один дополнительный реальный cardinality residual, поэтому он закрывается отдельным WP07 перед повторной приёмкой WP06. Внешний E2E остаётся отдельным release-gate.

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
| T021 | Зафиксировать RED для raw root-walk и stale authority token | WP04 | Нет |
| T022 | Перевести status transition на resolver-first anchor path | WP04 | Нет |
| T023 | Синхронизировать live authority token и проверить отсутствие stale entries | WP04 | Нет |
| T024 | Убить boundary/allowlist mutations и выполнить targeted GREEN | WP04 | Нет |
| T025 | Зафиксировать RED для Windows diagnostic path и lock hash | WP05 | Нет |
| T026 | Нормализовать POSIX diagnostic keys без изменения filesystem semantics | WP05 | Нет |
| T027 | Сделать code-map lock deterministic по LF-нормализованным bytes | WP05 | Нет |
| T028 | Убить hash/path mutations и выполнить targeted GREEN | WP05 | Нет |
| T029 | Выполнить полный contract/architecture gate на exact SHA | WP06 | Нет |
| T030 | Классифицировать новые residuals и не скрывать их текущим пакетом | WP06 | Нет |
| T031 | Обновить acceptance matrix и hard-gate result | WP06 | Нет |
| T032 | Дополнить tracers и подготовить SHA-bound handoff | WP06 | Нет |
| T033 | Воспроизвести 25-й convert-site и доказать его происхождение из WP04 | WP07 | Нет |
| T034 | Явно пометить только проверенный cardinality-only assertion | WP07 | Нет |
| T035 | Убить marker mutation и выполнить targeted GREEN без изменения ceiling | WP07 | Нет |
| T036 | Передать новый immutable SHA в повторный WP06 acceptance | WP07 | Нет |

## WP01 — Windows portability и collection closure

**Приоритет**: P1

**Prompt**: `tasks/WP01-windows-portability-collection.md`

**Зависимости**: отсутствуют

**Depends on**: none

### Результат

Contract null sink, EUID checks и repo-relative census работают на Windows; семь известных файлов собираются без ошибок; зависимые coverage/shard/session-reaper gates больше не падают вследствие platform collection. Static expected inventories остаются независимыми и mutation-sensitive.

### Подзадачи

- [x] T001 Создать charter-required GitHub issue с исходными командами и counts (WP01)
- [x] T002 Закоммитить RED-first acceptance tests до implementation fixes (WP01)
- [x] T003 Выполнить tidy-first только внутри owned files либо записать `none found` evidence (WP01)
- [x] T004 Заменить `/dev/null`, безопасно ограничить EUID oracle и нормализовать только actual repo-relative paths (WP01)
- [x] T005 Добиться `0 collection errors` для семи файлов и зелёных dependent gates (WP01)
- [x] T006 Убить обязательные mutations, прогнать targeted pytest/Ruff/py_compile/diff-check и передать в review (WP01)

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

- [x] T007 Закоммитить RED для текущих missing sink/raw predicate сигналов (WP02)
- [x] T008 Выполнить tidy-first и read-only baseline текущей code map (WP02)
- [x] T009 Классифицировать и исправить каждый owning architecture boundary без blanket allowlist (WP02)
- [x] T010 Синхронизировать точечные inventories и все три code map artifacts в production commit (WP02)
- [x] T011 Доказать negative/mutation sensitivity и targeted GREEN (WP02)
- [x] T012 На финальном SHA выполнить полные contract/architecture gates и external E2E access/result check (WP02)
- [x] T013 Обновить mission evidence, issue и tracers; зафиксировать `implementation_complete`, `local_ready`, `e2e_ready`, `release_ready` (WP02)

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

- [x] T014 Снять current residual packet на approved WP02 SHA и закоммитить
  test-only RED до любых GREEN-правок; отдельно записать, что width в полном
  окружении зелёный, а `--confcutdir` — диагностический режим.
- [x] T015 Исправить только path/hash seams: `.as_posix()` для actual census keys,
  newline-normalized seed digest с mixed-newline guard; сохранить независимые
  static expected values. Добавить targeted negative tests.
- [x] T016 Зафиксировать прежний `pytest.param` id явным `id=...`, оставить
  capability skip fail-closed и доказать, что committed floor не shrink'ится.
- [x] T017 Пометить только настоящий cardinality-only site, запустить штатный
  `--freeze-baseline`, сверить ceilings с merge-base evidence и не уменьшать floor.
- [x] T018 Выполнить все mutations: slash mismatch, raw CRLF/LF drift, удаление
  explicit id и снятие cardinality marker; затем targeted pytest/Ruff/py_compile/
  diff-check.
- [x] T019 На неизменённом SHA выполнить полный `tests/contract` и
  `tests/architectural`; collection/errors/failures сохранить дословно.
- [x] T020 Обновить hard-gate result и acceptance matrix (`local_ready` только при
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

## WP04 — Resolver-first boundary и authority allowlist closure

**Приоритет**: P1

**Prompt**: `tasks/WP04-resolver-and-authority-boundaries.md`

**Зависимости**: WP03; выполняется последовательно после WP03 и не параллельно
с WP05 на общих архитектурных тестах.

### Результат

Raw `parent.parent` anchor derivation заменён canonical resolver-first путём с
сохранением fail-loud поведения. Authority allowlist отражает точный live
call-site, а stale token и новый boundary bypass ловятся независимыми
negative/mutation tests.

### Подзадачи

- [x] T021 Зафиксировать RED raw root-walk/stale token и положительные controls (WP04)
- [x] T022 Перевести status transition на canonical resolver-first путь (WP04)
- [x] T023 Синхронизировать live authority token и rationale (WP04)
- [x] T024 Убить mutations и выполнить targeted GREEN (WP04)

### Owned files

- `src/specify_cli/coordination/status_transition.py`
- `tests/architectural/test_no_write_side_rederivation.py`
- `tests/architectural/test_resolution_authority_gates.py`
- `tests/architectural/resolution_gate_allowlist.yaml`

### Ограничения

- Не скрывать raw join blanket allowlist-ом.
- Не проглатывать ошибки, кроме документированного `MissionNotFound` legacy callback.
- Историческое ownership approved WP01 для двух тестовых файлов считается
  последовательным follow-up; coordination note обязателен в handoff.

## WP05 — Cross-platform diagnostics и deterministic code-map lock

**Приоритет**: P1

**Prompt**: `tasks/WP05-cross-platform-diagnostics-and-codemap-lock.md`

**Зависимости**: WP03; можно готовить независимо от WP04, но финальная приёмка
ждёт оба пакета.

### Результат

Диагностические repo-relative keys одинаковы на Windows и POSIX, а code-map
lock сравнивается с каноническими LF-нормализованными bytes без semantic
green-wash.

### Подзадачи

- [x] T025 Зафиксировать RED diagnostic path и lock hash (WP05)
- [x] T026 Нормализовать только POSIX diagnostic keys (WP05)
- [x] T027 Обновить deterministic code-map lock (WP05)
- [x] T028 Убить mutations и выполнить targeted GREEN (WP05)

### Owned files

- `tests/architectural/test_topology_resolution_boundary.py`
- `docs/codemap/codemap.lock`

### Ограничения

- `test_no_write_side_rederivation.py` остаётся approved WP04 surface; его
  diagnostic helper меняется только последовательно и с rationale.
- JSON/HTML code map являются read-only inputs, если не доказан semantic
  boundary change.
- Не менять frozen glossary seed и не расширять allowlist ради Windows.
- Историческое ownership approved WP01/WP02 закрывается только sequential
  coordination note; параллельная запись запрещена.

## WP06 — Полная local acceptance и SHA-bound handoff

**Приоритет**: P1

**Prompt**: `tasks/WP06-final-local-acceptance-and-handoff.md`

**Зависимости**: WP07 approved; WP07 последовательно зависит от WP04 и WP05.

WP06 нельзя завершать до approved WP07: полный gate выявил residual,
добавленный WP04 уже после предыдущего baseline.

### Результат

Полные contract/architecture gates выполнены на одном неизменённом SHA;
acceptance matrix различает implementation, local, E2E и release readiness.
Любой новый residual снова выносится в follow-up, а не скрывается в текущем
handoff.

### Подзадачи

- [x] T029 Выполнить полный gate на exact SHA (WP06)
- [x] T030 Классифицировать новые residuals (WP06)
- [x] T031 Обновить acceptance matrix и hard-gate result (WP06)
- [x] T032 Дополнить tracers и SHA-bound handoff (WP06)

### Owned files

- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/acceptance-matrix.json`
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/contracts/hard-gate-result.md`
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/traces/approach.md`
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/traces/design-decisions.md`
- `kitty-specs/windows-hard-gate-restoration-task-01M00HSC/traces/tooling-friction.md`

### Ограничения

- `local_ready=true` только при полном architecture `0 failed, 0 errors` и
  нулевой collection error.
- Отсутствующий внешний E2E не превращать в `e2e_ready` или `release_ready`.

## WP07 — Закрытие cardinality residual после полного architecture gate

**Приоритет**: P1

**Prompt**: `tasks/WP07-golden-count-residual-closure.md`

**Зависимости**: WP04 и WP05 approved; блокирует повторный WP06.

### Результат

Единственный failure полного architecture gate классифицирован как новый
cardinality-only site, добавленный WP04: assertion проверяет ровно одну
конкретную live authority-запись. На строке assertion появляется узкий
`golden-count: cardinality-is-contract` marker; baseline ceiling не
увеличивается, другие sites и allowlists не меняются. Marker mutation снова
делает recurrence guard красным.

### Подзадачи

- [x] T033 Воспроизвести полный residual и сравнить список convert-sites с
  merge-base/WP03 (WP07)
- [x] T034 Добавить marker только на assertion WP04, не меняя проверяемую
  authority-семантику (WP07)
- [x] T035 Временно снять marker, получить ожидаемый RED, восстановить его и
  прогнать targeted gate, Ruff, py_compile и diff-check (WP07)
- [x] T036 Зафиксировать provenance, новый SHA и handoff для повторного WP06
  полного contract/architecture gate (WP07)

### Owned files

- `tests/architectural/test_resolution_authority_gates.py`

### Ограничения

- Не повышать `tests/architectural` ceiling с 24 до 25.
- Не добавлять wildcard/blanket allowlist и не помечать соседние assertions.
- Не менять production code, authority token, codemap или E2E/release status.
- Изменение выполняется последовательно после approved WP04; rationale о
  handoff ownership сохраняется в activity/handoff WP07.

### Проверки

- RED до marker показывает 25 non-escaped convert-sites и failure recurrence
  guard; положительный control подтверждает, что marker читается на нужной
  физической строке.
- GREEN после marker показывает 24 non-escaped convert-sites и targeted
  `test_convert_sites_do_not_exceed_frozen_baseline` проходит.
- Mutation снятия marker снова красная; после восстановления полный WP06 gate
  запускается на новом immutable SHA.

### Параллельность

WP07 не параллелен с WP06 и не меняет другие архитектурные поверхности.

## Общая готовность

- Оба пакета соблюдают отдельный RED commit до implementation commit.
- Никакой blanket skip, count-floor reduction, wildcard allowlist или operator exception не добавлен.
- Contract и architecture suites на окончательном SHA имеют `0 failed`, `0 errors`;
  до завершения WP07/WP06 acceptance matrix честно показывает
  `local_ready=false`.
- External E2E отсутствие доступа допускает `implementation_complete=true`, но оставляет `e2e_ready=false` и `release_ready=false`.
- Handoff указывает exact SHA, после которого файлы не менялись.
- Beads не используется до отдельного исправления task-local resolver; глобальная DB не изменяется.

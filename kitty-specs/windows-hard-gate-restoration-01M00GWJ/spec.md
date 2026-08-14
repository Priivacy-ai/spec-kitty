# Спецификация: восстановить hard-gates Spec Kitty на Windows

**Ветка задачи**: `codex/setup-plan-hard-gates`  
**Создано**: 2026-08-14  
**Статус**: Draft  
**Целевая аудитория**: сопровождающий Spec Kitty, который проверяет готовность изменения на Windows 10+

## Пользовательские сценарии и проверка

### Сценарий 1 — Локальные release-gates дают честный результат на Windows (P1)

Сопровождающий запускает обязательные contract и architecture suites в штатном Windows-окружении и получает результат, отражающий дефекты продукта, а не несовместимость тестовой обвязки с платформой.

**Почему P1**: сейчас contract suite падает на `/dev/null`, а architecture suite завершилась с 28 падениями и 34 ошибками; это блокирует публикацию уже проверенного изменения.

**Независимая проверка**: полный `tests/contract` завершается без падений, полный `tests/architectural` — без падений и ошибок collection.

**Сценарии приёмки**:

1. **Дано** Windows и Python 3.11+, **когда** запускается contract suite, **тогда** тесты используют платформенный null sink и не обращаются к `/dev/null`.
2. **Дано** Windows без `os.geteuid`, **когда** pytest собирает обязательные suites, **тогда** collection завершается без `AttributeError`, а платформенно недоступная проверка прав доступа явно пропускается или использует эквивалентный безопасный oracle.
3. **Дано** текущая интегрированная ветка, **когда** запускаются обе suites, **тогда** итог содержит ноль `failed` и ноль `errors`; ожидаемые `skip`/`xfail` сохраняют своё документированное значение.

---

### Сценарий 2 — Архитектурные gates остаются fail-closed и кроссплатформенными (P1)

Сопровождающий получает одинаковую семантическую оценку inventory, allowlist и call-site census на Windows и POSIX, при этом новые обходы canonical resolver не маскируются нормализацией путей.

**Почему P1**: часть текущих падений — только различие `\` и `/`, но gates также обнаружили отсутствующий inventory для `_compose_mission_anchor_feature_dir` и raw coord-topology predicate в `mission_creation.py`. Эти классы нельзя исправлять общим ослаблением assertions.

**Независимая проверка**: характерные path-oracle tests проходят после нормализации, а mutation/negative fixtures по-прежнему заставляют каждый gate падать на новом нарушении.

**Сценарии приёмки**:

1. **Дано** один и тот же логический путь, **когда** он получен через Windows `Path`, **тогда** сравнение с canonical inventory выполняется в POSIX-представлении.
2. **Дано** новый неучтённый sink, raw topology predicate или patch-site, **когда** запускается соответствующий gate, **тогда** он падает с конкретным файлом и причиной.
3. **Дано** существующий call-site, **когда** он уже маршрутизируется через canonical authority, **тогда** inventory обновляется точечно; если нет — исправляется production boundary, а не расширяется allowlist без доказательства.

---

### Сценарий 3 — Ошибки collection не создают каскад ложных hard-gate сбоев (P2)

Сопровождающий может собрать весь тестовый набор, используемый coverage/shard gates, поэтому их completeness-проверки измеряют реальные тесты, а не последствия импортной ошибки.

**Почему P2**: import-time `os.geteuid` прерывает collection и порождает десятки вторичных ошибок coverage и session-reaper.

**Независимая проверка**: семь ранее проблемных файлов собираются на Windows отдельно и внутри полного architecture run; completeness gates видят ожидаемый набор модулей.

**Сценарии приёмки**:

1. **Дано** Windows, **когда** pytest делает `--collect-only` для ранее проблемных файлов, **тогда** все файлы собираются без platform-specific import errors.
2. **Дано** полная collection, **когда** запускаются coverage/shard gates, **тогда** они не сообщают недостающие группы только из-за сорванной collection.

---

### Сценарий 4 — Внешний cross-repo E2E gate не обходится (P2)

Сопровождающий видит отдельно локальную готовность и доступность обязательного репозитория `Priivacy-ai/spec-kitty-end-to-end-testing`.

**Почему P2**: текущий GitHub principal не видит репозиторий; это внешний блокер, а не основание объявлять E2E пройденным или создавать локальное исключение.

**Независимая проверка**: при доступе запускается документированный E2E packet; без доступа команда завершается явным blocked-результатом без секретов, подмены репозитория или operator exception.

**Сценарии приёмки**:

1. **Дано** авторизованный доступ к E2E-репозиторию, **когда** запускается публикационный preflight, **тогда** он проверяет зафиксированный CLI commit совместимым E2E-набором.
2. **Дано** доступа нет, **когда** запускается preflight, **тогда** результат явно называет внешний блокер и не переводит gate в pass.

### Граничные случаи

- Windows предоставляет `os.devnull`, но не `os.geteuid`; Linux/macOS-поведение не должно регрессировать.
- Пути могут приходить как `Path`, строки с `\` или уже canonical POSIX-строки; нормализация выполняется до сравнения, но не скрывает регистр, имя файла или лишний call-site.
- Изменение строк в source сдвигает inventory line numbers; gate должен потребовать точечную синхронизацию, а не принимать широкий wildcard.
- Один первичный collection defect не должен превращаться в десятки неразличимых ошибок без указания исходного файла.
- Внешний репозиторий может быть private, переименован или недоступен текущему principal; локальный код не пытается обходить авторизацию.

## Требования

### Функциональные требования

| ID | Название | Требование | Приоритет | Статус |
|----|----------|------------|-----------|--------|
| FR-001 | Платформенный null sink | Contract tests используют `os.devnull` или эквивалентный закрываемый поток вместо hard-coded `/dev/null`. | High | Open |
| FR-002 | Безопасная проверка EUID | Import/collection не обращается к отсутствующему `os.geteuid`; Unix-specific permission oracle явно ограничен поддерживаемыми платформами. | High | Open |
| FR-003 | Canonical path comparison | Все затронутые inventory/census gates сравнивают repo-relative пути в одном POSIX-представлении. | High | Open |
| FR-004 | Точная архитектурная классификация | Каждый обнаруженный drift классифицируется как Windows-представление, устаревший inventory либо реальный boundary bypass; исправление соответствует классу. | High | Open |
| FR-005 | Resolver-first topology | Raw coord-topology predicate в `mission_creation.py` либо переводится на canonical topology authority, либо получает узкое доказанное исключение с negative test; предпочтителен resolver-first путь. | High | Open |
| FR-006 | Полная Windows collection | Все файлы, от которых зависят gate-coverage, shard и session-reaper, успешно собираются на Windows. | High | Open |
| FR-007 | Non-vacuous guards | Каждый исправленный architectural gate имеет положительный oracle и mutation/negative test, доказывающий, что новое нарушение всё ещё обнаруживается. | High | Open |
| FR-008 | Синхронизация code map | До production-правок и в итоговом commit обновляются `docs/codemap/codemap.json`, `.html` и `.lock`, чтобы карта отвечала, кто вызывает изменяемые boundaries, что они затрагивают и какими тестами покрыты. | Medium | Open |
| FR-009 | Раздельный E2E preflight | Доступность внешнего E2E-репозитория и результат его тестов представлены отдельными fail-closed состояниями; отсутствие доступа не становится pass. | High | Open |
| FR-010 | Воспроизводимый handoff | Итог содержит команды, версии, commit SHA, counts и разделение исправленных, ожидаемых skip/xfail и внешних blockers. | Medium | Open |

### Нефункциональные требования

| ID | Название | Требование | Категория | Приоритет | Статус |
|----|----------|------------|-----------|-----------|--------|
| NFR-001 | Contract gate | Полный `tests/contract` завершается с `0 failed` и `0 errors` на Windows. | Надёжность | High | Open |
| NFR-002 | Architecture gate | Полный `tests/architectural` завершается с `0 failed` и `0 errors` на Windows; существующие документированные skip/xfail не green-wash'ятся. | Надёжность | High | Open |
| NFR-003 | Кроссплатформенность | Все изменённые path/EUID/null-sink oracles проходят на Windows и не меняют ожидаемую семантику POSIX. | Совместимость | High | Open |
| NFR-004 | Fail-closed | Ни один baseline/allowlist не расширяется без конкретного call-site, rationale и negative/mutation evidence. | Безопасность архитектуры | High | Open |
| NFR-005 | Ограниченный цикл | Во время реализации сначала запускаются targeted suites; полный architecture suite запускается один раз на финальном gate, если targeted packet зелёный. | Производительность | Medium | Open |

### Ограничения

| ID | Название | Ограничение | Категория | Приоритет | Статус |
|----|----------|-------------|-----------|-----------|--------|
| C-001 | Без обхода gates | Запрещены blanket skip, `|| true`, снижение count floor, широкие wildcard allowlists и самодельный operator exception. | Governance | High | Open |
| C-002 | Git isolation | Все записи выполняются только в `C:\Users\Ruslan\.codex-worktrees\spklw-planning-setup-plan-hard-gates`, ветка `codex/setup-plan-hard-gates`. | Technical | High | Open |
| C-003 | Внешняя авторизация | Нельзя читать/печатать credentials или обходить GitHub permissions ради E2E. | Security | High | Open |
| C-004 | Beads blocker | Текущий `bd 1.1.2` ошибочно выбирает глобальный `C:\Users\Ruslan\.beads` и игнорирует task-local `BEADS_DIR`; до отдельного исправления запрещено писать в эту чужую базу. Mission metadata временно остаётся единственным task-local lifecycle source. | Tooling | High | Open |
| C-005 | Pre-existing failure issue | До реализации подтверждённые pre-existing hard-gate failures оформляются в GitHub issue с командами и доказательством происхождения согласно charter. | Governance | High | Open |

## Критерии успеха

- **SC-001**: `tests/contract` на Windows: `0 failed`, `0 errors`.
- **SC-002**: `tests/architectural` на Windows: `0 failed`, `0 errors`.
- **SC-003**: targeted collection ранее проблемных семи файлов: `0 collection errors`.
- **SC-004**: минимум по одному mutation/negative oracle для path normalization, collection portability и каждого исправленного real boundary/inventory класса.
- **SC-005**: code map JSON/HTML имеет одинаковые nodes/edges/references, а `.lock` совпадает с фактическими SHA-256.
- **SC-006**: E2E gate либо проходит на доступном canonical репозитории, либо возвращает один явный внешний blocked-результат; ложный pass невозможен.
- **SC-007**: локальная ветка остаётся clean после commit, полный handoff указывает worktree, branch, commits и все gate counts.

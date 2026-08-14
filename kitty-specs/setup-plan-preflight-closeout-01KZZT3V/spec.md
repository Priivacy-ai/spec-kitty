# Спецификация Mission: восстановить Git preflight в setup-plan

**Ветка Mission**: `codex/setup-plan-preflight-closeout`  
**Создано**: 2026-08-14  
**Статус**: Draft  
**Контекст**: regression follow-up для PR #3332; итоговый PR направляется в `codex/spec-kitty-worktree-mission-create`.

## Пользовательские сценарии и проверка

### Сценарий 1 — Git-ошибка не маскируется Mission-контекстом (приоритет P1)

Разработчик запускает `setup-plan` в checkout с проваленным Git preflight. Команда должна вернуть стабильную ошибку `GIT_PREFLIGHT_FAILED` с существующей remediation-инструкцией до попытки разрешить Mission-контекст.

**Почему P1**: сейчас команда сообщает менее полезный `PLAN_CONTEXT_UNRESOLVED`, хотя первопричина находится в Git-состоянии.

**Независимая проверка**: подменить результат Git preflight на failed и подтвердить код ошибки, remediation и отсутствие вызова Mission resolver после отказа.

**Критерии приёмки**:

1. **Дано**: Git preflight возвращает failed. **Когда**: вызывается `setup-plan --json`. **Тогда**: результат содержит `GIT_PREFLIGHT_FAILED`, а не `PLAN_CONTEXT_UNRESOLVED`.
2. **Дано**: Git preflight возвращает failed. **Когда**: вызывается человекочитаемый режим. **Тогда**: сохраняется действующая remediation-инструкция и команда завершается до любых Mission-записей.

---

### Сценарий 2 — caller-owned linked worktree сохраняет канонический lifecycle (приоритет P1)

Разработчик запускает `setup-plan` из валидного caller-owned linked worktree. После успешного Git preflight команда должна разрешить `MissionOperationContext` и продолжить использовать разные `repository_root` и `mission_anchor_root` по существующему контракту.

**Почему P1**: исправление порядка проверок не должно отменить основной результат PR #3332.

**Независимая проверка**: интеграционный тест запускает `setup-plan` из caller-owned linked worktree и подтверждает успешное разрешение Mission без записи в защищённый primary checkout.

**Критерии приёмки**:

1. **Дано**: Git preflight успешен и Mission существует в caller-owned linked worktree. **Когда**: запускается `setup-plan`. **Тогда**: команда использует канонический Mission resolver и возвращает корректные planning paths.
2. **Дано**: `repository_root`, активный checkout и `mission_anchor_root` различаются. **Когда**: выполняется planning setup. **Тогда**: topology/coordination используют `repository_root`, Git preflight — активный checkout, а Mission-артефакты — anchor surface.

---

### Сценарий 3 — preflight остаётся единственным и без побочных записей (приоритет P2)

Разработчик не должен получать двойной Git preflight или частично созданные planning-артефакты при раннем отказе.

**Почему P2**: дублирование увеличивает задержку и может разойтись по диагностике, а запись до отказа нарушает fail-closed контракт.

**Независимая проверка**: spy-оракул подтверждает ровно один вызов Git preflight и ноль Mission-resolver/write вызовов на failed path.

**Критерии приёмки**:

1. **Дано**: любой вызов `setup-plan`. **Когда**: выполняется Git preflight. **Тогда**: он вызывается ровно один раз.
2. **Дано**: Git preflight failed. **Когда**: команда завершается. **Тогда**: новые или изменённые Mission-артефакты отсутствуют.

### Граничные случаи

- Git preflight успешен, но Mission selector отсутствует или неоднозначен: после preflight возвращается соответствующая Mission-context ошибка.
- Команда запущена из обычного repository checkout: поведение остаётся совместимым с текущим `setup-plan`.
- Команда запущена из caller-owned linked worktree: не появляется вторая authority для Mission root.
- JSON и человекочитаемый режимы используют один и тот же порядок проверок и один error contract.

## Требования

### Функциональные требования

| ID | Название | Требование | Приоритет | Статус |
|----|----------|------------|-----------|--------|
| FR-001 | Приоритет Git preflight | `setup-plan` обязан завершать failed Git preflight до разрешения Mission-контекста и возвращать `GIT_PREFLIGHT_FAILED`. | High | Open |
| FR-002 | Стабильная remediation | JSON и человекочитаемый режимы обязаны сохранить существующий код ошибки и remediation для Git preflight. | High | Open |
| FR-003 | Сохранение caller-owned routing | После успешного preflight caller-owned путь обязан использовать канонический `MissionOperationContext` и сохранять разделение `repository_root`/`mission_anchor_root`; обычный checkout сохраняет действующий feature-dir resolver. | High | Open |
| FR-004 | Один preflight | Один вызов `setup-plan` обязан выполнять Git preflight ровно один раз. | Medium | Open |
| FR-005 | Fail-closed без записей | Failed Git preflight не должен вызывать Mission resolver или создавать/изменять planning-артефакты. | High | Open |

### Нефункциональные требования

| ID | Название | Требование | Категория | Приоритет | Статус |
|----|----------|------------|-----------|-----------|--------|
| NFR-001 | Кроссплатформенность | Фокусные тесты preflight и caller-owned worktree должны проходить на поддерживаемых Windows, Linux и macOS без platform-specific ветви в production-коде. | Compatibility | High | Open |
| NFR-002 | Регрессионная чувствительность | Тесты должны падать при перестановке Mission resolver перед preflight, удалении early exit или добавлении второго preflight-вызова. | Test quality | High | Open |
| NFR-003 | Статический gate | Изменённый Python-код должен проходить `ruff`, `mypy --strict` и `py_compile` без новых диагностик. | Maintainability | High | Open |
| NFR-004 | Ограниченный overhead | На успешном пути остаётся ровно один Git preflight; исправление не добавляет дополнительных Git subprocess-вызовов. | Performance | Medium | Open |

### Ограничения

| ID | Название | Ограничение | Категория | Приоритет | Статус |
|----|----------|-------------|-----------|-----------|--------|
| C-001 | Единая root authority | Нельзя вводить новый Mission-root resolver или raw path-join; используется существующий `MissionOperationContext`. | Architecture | High | Open |
| C-002 | Узкий diff | Production-правка ограничивается `mission_setup_plan.py` и, только если нужно для единой checkout authority, одним существующим resolver-модулем; тесты — фокусными preflight/caller-owned сценариями. Дальнейшее расширение границы требует повторного согласования. | Scope | High | Open |
| C-003 | Landing branch | Task-owned PR направляется в `codex/spec-kitty-worktree-mission-create`; публикация в `main` и release не входят в scope. | Delivery | High | Open |
| C-004 | ATDD-first | До production-правки должен быть воспроизведён RED для маскировки `GIT_PREFLIGHT_FAILED`. | Process | High | Open |

## Предпосылки и зависимости

- Существующие `GIT_PREFLIGHT_FAILED` и remediation являются публичным CLI-контрактом и не переименовываются.
- Канонический resolver caller-owned Mission уже реализован и остаётся единственным источником Mission identity и anchor root.
- Исправление не требует сети, SaaS, миграции данных, release или изменения пользовательской конфигурации.
- Beads CLI 1.1.2 на Windows завис при создании пустой embedded-Dolt базы; issue identity будет добавлена после восстановления инструмента и не меняет предметный scope Mission.

## Критерии успеха

- **SC-001**: существующий regression-тест `test_setup_plan_exits_on_preflight_failure_json` проходит и возвращает `GIT_PREFLIGHT_FAILED`.
- **SC-002**: новый caller-owned worktree тест проходит и подтверждает сохранение канонического Mission resolver после успешного preflight.
- **SC-003**: spy-оракул подтверждает ровно один Git preflight и отсутствие Mission resolution/write на failed path.
- **SC-004**: фокусные тесты, `ruff`, `mypy --strict`, `py_compile` и `git diff --check` проходят без новых ошибок.
- **SC-005**: mutation/deletion проверки убивают перестановку порядка, удаление early exit и дублирование preflight.

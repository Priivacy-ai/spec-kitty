# Mission Specification: Полный lifecycle Mission в пользовательском worktree

**Mission Branch**: `codex/spec-kitty-worktree-mission-create`  
**Created**: 2026-08-13  
**Status**: Утверждено  
**Input**: После создания Mission в caller-owned linked worktree весь её lifecycle должен продолжаться в том же checkout, не затрагивая repository root checkout.

## User Scenarios & Testing

### User Story 1 — Продолжить Mission в том же worktree (Priority: P1)

Разработчик создаёт Mission в отдельном task-owned linked worktree и затем выполняет команды статуса, планирования, реализации, review и приёмки из этого же checkout. Все команды находят одну и ту же Mission и не требуют копирования артефактов в repository root checkout.

**Why this priority**: Без этого основной сценарий параллельной работы обрывается сразу после создания Mission.

**Independent Test**: Создать Mission в caller-owned linked worktree, последовательно вызвать команды lifecycle и доказать, что они разрешают Mission из текущего checkout, а repository root checkout не изменился.

**Acceptance Scenarios**:

1. **Given** Mission существует только в caller-owned linked worktree, **When** разработчик запрашивает её статус по полному `mission_id`, **Then** команда возвращает статус этой Mission.
2. **Given** та же Mission, **When** разработчик выполняет планирование, финализацию задач, implement/review и accept, **Then** каждая команда использует ту же Mission и сохраняет её идентичность.
3. **Given** repository root checkout был чистым до сценария, **When** lifecycle завершён, **Then** его tracked-файлы и текущая ветка не изменились.

---

### User Story 2 — Сохранить служебную topology Spec Kitty (Priority: P1)

Разработчик или агент работает внутри управляемого coordination/lane worktree. Такие checkout продолжают использовать существующие правила размещения и не становятся caller-owned только из-за наличия Mission.

**Why this priority**: Ошибочная смена владельца служебного checkout может привести к split-brain и записи артефактов не на ту ветку.

**Independent Test**: Повторить разрешение Mission из управляемого coordination/lane worktree и подтвердить прежний canonical read/write path и запрет вложенного создания Mission.

**Acceptance Scenarios**:

1. **Given** текущий checkout управляется Spec Kitty как lane или coordination surface, **When** команда разрешает Mission, **Then** применяется существующая topology, а не caller-owned приоритет.
2. **Given** агент находится в управляемой lane, **When** он пытается создать новую Mission, **Then** прежний запрет остаётся в силе.

---

### User Story 3 — Явно обнаружить конфликт копий (Priority: P1)

Если Mission с одним селектором представлена несовместимыми копиями в текущем worktree и repository root checkout, оператор получает структурированную ошибку вместо молчаливого выбора.

**Why this priority**: Тихий выбор правдоподобной, но неправильной Mission опаснее явного отказа.

**Independent Test**: Подготовить две копии с несовпадающей идентичностью и проверить стабильный fail-closed результат без записи.

**Acceptance Scenarios**:

1. **Given** селектор совпадает с конфликтующими Mission в двух checkout, **When** выполняется разрешение, **Then** команда завершается структурированной ошибкой с обеими кандидатами.
2. **Given** конфликт отсутствует или обе поверхности указывают на одну идентичность, **When** выполняется разрешение, **Then** команда выбирает однозначный canonical path.

### Edge Cases

- Текущий каталог находится внутри репозитория, но не внутри Git checkout.
- Пользователь передал полный `mission_id`, `mid8` или human-readable slug.
- Mission существует только в repository root checkout или только в coordination worktree.
- Текущий linked worktree относится к другому Git common directory.
- Явно выбранный оператором repository root не должен быть незаметно переопределён текущим каталогом.
- Символические ссылки, различия регистра и Windows-пути не должны создавать ложный конфликт.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Caller-owned разрешение | Команды lifecycle должны разрешать Mission из текущего безопасного caller-owned linked worktree, если Mission существует там. | High | Confirmed |
| FR-002 | Полный lifecycle | Одинаковое разрешение должно применяться к status, context, planning, tasks, action implement/review, next и accept. | High | Confirmed |
| FR-003 | Чистый repository root checkout | Выполнение lifecycle из caller-owned worktree не должно создавать или изменять tracked-артефакты в repository root checkout. | High | Confirmed |
| FR-004 | Сохранение managed topology | Coordination/lane worktree должны сохранять существующие canonical правила чтения, записи и запрет вложенного создания Mission. | High | Confirmed |
| FR-005 | Fail-closed конфликт | Несовместимые Mission-кандидаты должны приводить к структурированной ошибке без выбора и записи. | High | Confirmed |
| FR-006 | Явный root остаётся авторитетным | Явно переданный оператором repository root должен сохранять приоритет и не подменяться текущим каталогом. | High | Confirmed |
| FR-007 | Единая идентичность | Все команды должны возвращать один и тот же `mission_id`, slug и путь для одной Mission в пределах сценария. | High | Confirmed |
| FR-008 | Параллельные задачи | Несколько caller-owned worktree одного репозитория должны независимо разрешать только собственные Mission. | Medium | Confirmed |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Кроссплатформенность | Acceptance-сценарии должны проходить на Windows, Linux и macOS в поддерживаемой CI-матрице. | Compatibility | High | Confirmed |
| NFR-002 | Ограниченный overhead | Дополнительное разрешение не должно добавлять более одного обхода Mission-кандидатов и более 50 мс к p95 локального selector-вызова на тестовом репозитории с 100 Mission. | Performance | Medium | Confirmed |
| NFR-003 | Детерминированность | Одинаковые checkout, селектор и файловое состояние должны давать одинаковый результат в 100 повторных вызовах. | Reliability | High | Confirmed |
| NFR-004 | Регрессионная защита | Все новые ветви выбора и отказа должны иметь исполняемые тесты; targeted suite должна проходить без новых предупреждений. | Quality | High | Confirmed |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Не менять глобальную семантику root | Глобальный поиск repository root нельзя превращать в безусловный выбор текущего linked worktree. | Architecture | High | Confirmed |
| C-002 | Один canonical resolver | Выбор Mission surface должен принадлежать одной общей boundary, а не дублироваться отдельными командами. | Architecture | High | Confirmed |
| C-003 | Без автоматической миграции | Существующие Mission и topology не должны требовать миграции данных. | Compatibility | High | Confirmed |
| C-004 | Минимальный diff | Изменения ограничиваются root/selector boundary, её прямыми потребителями, тестами и необходимой документацией. | Delivery | Medium | Confirmed |

### Key Entities

- **Caller-owned checkout**: linked worktree, созданный пользователем или внешним инструментом, а не Spec Kitty.
- **Managed checkout**: coordination/lane surface, жизненным циклом которой управляет Spec Kitty.
- **Mission identity**: неизменяемый `mission_id` и связанные с ним slug и каталог.
- **Mission candidate**: возможная копия Mission, обнаруженная на разрешённой поверхности.
- **Resolved Mission surface**: единственная поверхность, выбранная после проверки ownership, topology и конфликтов.

## Assumptions

- Текущая ветка `codex/spec-kitty-worktree-mission-create` и PR #3332 остаются delivery surface этого исправления.
- Caller-owned worktree должен быть связан с тем же Git common directory, что и repository root checkout.
- Параллельная реализация задач, затрагивающих одинаковые файлы, остаётся запрещённой вне этого исправления.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Сквозной сценарий create → status → plan/tasks → implement/review → accept проходит из caller-owned linked worktree без ручного копирования файлов.
- **SC-002**: Во всех acceptance-сценариях repository root checkout сохраняет исходную ветку и нулевой tracked diff.
- **SC-003**: Managed coordination/lane regression suite проходит без изменения ожидаемых путей и запретов.
- **SC-004**: Каждый конфликт идентичности завершается одним стабильным структурированным error code и нулевым числом записей.
- **SC-005**: Два параллельных caller-owned worktree в одном репозитории разрешают собственные Mission без взаимного влияния в 100% тестовых запусков.

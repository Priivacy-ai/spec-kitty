# Задачи: восстановить Git preflight в setup-plan

## Обзор

Работа собрана в один связный пакет: production-порядок gate, выбор активного Git checkout и проверяющие его тесты нельзя безопасно разнести по параллельным lane без риска временно получить противоречивый CLI-контракт.

## Индекс подзадач

| ID | Краткое содержание | Пакет | Параллельно |
|---|---|---|---|
| T001 | Зафиксировать RED для приоритета Git preflight и error contract | WP01 | Нет |
| T002 | Добавить канонический helper выбора caller-owned linked checkout | WP01 | Нет |
| T003 | Перестроить setup-plan на один ранний Git preflight | WP01 | Нет |
| T004 | Доказать успешный caller-owned lifecycle без записи в primary | WP01 | Нет |
| T005 | Добавить mutation/deletion sensitivity для критических регрессий | WP01 | Нет |
| T006 | Выполнить статические gates, differential и проверку карты кода | WP01 | Нет |

## WP01 — Восстановить приоритет Git preflight в setup-plan

**Приоритет**: P1  
**Prompt**: `tasks/WP01-setup-plan-preflight.md`  
**Зависимости**: отсутствуют  
**Оценка prompt**: около 300–400 строк

### Результат

`setup-plan` после сохранённых hosted-auth/SaaS gates проверяет активный Git checkout ровно один раз, при отказе возвращает существующий `GIT_PREFLIGHT_FAILED` без Mission resolution или записей, а после успеха сохраняет канонический caller-owned routing.

### Независимая проверка

Фокусные unit и linked-worktree integration tests должны независимо подтвердить код/remediation ошибки, аргумент и количество вызовов preflight, отсутствие Mission resolver на failed path и неизменность primary checkout на успешном caller-owned path.

### Подзадачи

- [ ] T001 Зафиксировать RED для приоритета Git preflight и стабильного JSON/human error contract (WP01)
- [ ] T002 Добавить канонический helper выбора caller-owned linked checkout с fallback на repository checkout (WP01)
- [ ] T003 Перестроить setup-plan на один ранний Git preflight после hosted-auth/SaaS gates и до Mission resolution (WP01)
- [ ] T004 Добавить caller-owned integration oracle для правильного checkout и неизменности primary surface (WP01)
- [ ] T005 Добавить mutation/deletion проверки порядка, early exit, количества вызовов и выбора checkout (WP01)
- [ ] T006 Выполнить фокусные и статические gates, branch/base differential и проверить необходимость обновления codemap (WP01)

### Эскиз реализации

1. Воспроизвести текущую маскировку `GIT_PREFLIGHT_FAILED` и зафиксировать наблюдаемый RED без production-правок.
2. Вынести узкий checkout-selection helper рядом с существующей same-repository логикой; не создавать новую Mission authority и не запускать subprocess внутри helper.
3. Перенести существующий Git preflight в точку после auth/SaaS boundary и до caller-owned Mission resolution, сохранив обычный feature-dir path.
4. Проверить реальный linked-worktree путь, аргумент preflight, отсутствие побочных записей и стабильность primary snapshot.
5. Доказать чувствительность тестов к четырём реалистичным мутациям.
6. Прогнать целевые тесты и статические проверки; посторонние красные результаты классифицировать сравнением с base.

### Параллельность

Параллельная реализация не допускается: подзадачи затрагивают одни production-функции и меняющийся порядок вызовов. Read-only независимый review после GREEN допустим.

### Риски

- Проверка repository root вместо caller-owned checkout скроет реальное Git-состояние.
- Перенос preflight перед auth/SaaS gates изменит несвязанный приоритет ошибок.
- Новый helper может случайно стать второй Mission-root authority.
- Mock-only тесты могут пройти при неверном реальном linked-worktree поведении.
- Широкий Windows suite может содержать baseline failures; их нельзя приписывать этому diff без differential.

### Готовность

- Все FR-001–FR-005 покрыты наблюдаемыми тестами.
- RED воспроизведён до production fix, затем целевой набор GREEN.
- Mutation/deletion проверки ловят четыре заданных дефекта.
- Ruff, strict mypy для изменённого production-кода, py_compile и `git diff --check` проходят без новых диагностик.
- Изменения остаются в заявленных файлах; карта кода обновлена только при реальном изменении module boundary.

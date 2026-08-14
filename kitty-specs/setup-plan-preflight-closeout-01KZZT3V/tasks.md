# Задачи: восстановить Git preflight в setup-plan

## Обзор

Работа собрана в один связный пакет: production-порядок gate, выбор активного Git checkout и проверяющие его тесты нельзя безопасно разнести по параллельным lane без риска временно получить противоречивый CLI-контракт.

## Индекс подзадач

| ID | Краткое содержание | Пакет | Параллельно |
|---|---|---|---|
| T001 | Зафиксировать RED для приоритета Git preflight и error contract | WP01 | Нет |
| T002 | Выполнить отдельный tidy-first campsite-clean выбранной поверхности | WP01 | Нет |
| T003 | Добавить канонический helper выбора caller-owned linked checkout | WP01 | Нет |
| T004 | Перестроить setup-plan на один ранний Git preflight | WP01 | Нет |
| T005 | Доказать успешный caller-owned lifecycle без записи в primary | WP01 | Нет |
| T006 | Добавить mutation/deletion sensitivity для критических регрессий | WP01 | Нет |
| T007 | Выполнить статические gates, differential, tracers и проверку карты кода | WP01 | Нет |

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

- [ ] T001 Зафиксировать RED для приоритета Git preflight и стабильного JSON/human error contract отдельным commit до implementation commits (WP01)
- [ ] T002 Выполнить отдельный behavior-preserving tidy-first campsite-clean выбранных production/test surfaces (WP01)
- [ ] T003 Добавить канонический helper выбора caller-owned linked checkout с fallback на repository checkout (WP01)
- [ ] T004 Перестроить setup-plan на один ранний Git preflight после hosted-auth/SaaS gates и до Mission resolution (WP01)
- [ ] T005 Добавить caller-owned integration oracle для правильного checkout и неизменности primary surface (WP01)
- [ ] T006 Добавить mutation/deletion проверки порядка, early exit, количества вызовов и выбора checkout (WP01)
- [ ] T007 Выполнить фокусные и статические gates, branch/base differential, tracer closeout и проверить необходимость обновления codemap (WP01)

### Эскиз реализации

1. Воспроизвести текущую маскировку `GIT_PREFLIGHT_FAILED` и закоммитить наблюдаемый RED отдельным commit без production-правок.
2. До функциональной production-правки выполнить отдельный tidy-first осмотр/cleanup только выбранных surfaces; отсутствие релевантного debt тоже зафиксировать.
3. Вынести узкий checkout-selection helper рядом с существующей same-repository логикой; не создавать новую Mission authority и не запускать subprocess внутри helper.
4. Перенести существующий Git preflight в точку после auth/SaaS boundary и до caller-owned Mission resolution, сохранив обычный feature-dir path.
5. Проверить реальный linked-worktree путь, аргумент preflight, отсутствие побочных записей и стабильность primary snapshot.
6. Доказать чувствительность тестов к четырём реалистичным мутациям.
7. Прогнать целевые тесты и статические проверки, обновить три tracer через canonical CLI; посторонние красные результаты классифицировать сравнением с base.

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
- RED воспроизведён и закоммичен отдельно до production fix, затем целевой набор GREEN.
- Tidy-first campsite-clean выполнен отдельным behavior-preserving шагом без расширения выбранного file set.
- Mutation/deletion проверки ловят четыре заданных дефекта.
- Ruff, strict mypy для изменённого production-кода, py_compile и `git diff --check` проходят без новых диагностик.
- Изменения остаются в заявленных файлах; карта кода обновлена только при реальном изменении module boundary.
- `approach`, `design-decisions` и `tooling-friction` ведутся через canonical tracer CLI и оценены при closeout.

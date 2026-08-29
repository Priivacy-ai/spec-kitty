# Рабочие пакеты: платный opt-in ревьюер GLM 5.3

**Исходные артефакты**: `spec.md`, `plan.md`, `research.md`.

**Тесты**: обязательны; платный route проверяется только offline-фикстурами, без model call.

**Организация**: пять подзадач объединены в один неделимый пакет. Его полный prompt находится в `tasks/WP01-glm53-local-estimate-gate.md`.

## Формат подзадач: `[Txxx] Описание`

Подзадачи — ссылочные строки, а не checkbox. Статус ведёт штатный runtime Spec Kitty.

---

## WP01 — локальный порог advertised-оценки для GLM 5.3 (P1)

**Цель**: добавить ровно один платный route `openrouter/z-ai/glm-5.3` с явным локальным порогом advertised-оценки, повторной проверкой metadata перед prompt и байт-совместимым бесплатным режимом.

**Независимая проверка**: focused unit/integration-тесты, архитектурные границы, Ruff, strict mypy и `python docs/codemap/codemap.lock` проходят без внешнего вызова.

**Prompt**: `tasks/WP01-glm53-local-estimate-gate.md`

**Требования**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009.

### Включённые подзадачи

T001 Зафиксировать offline acceptance-контракт отдельным failing-коммитом.

T002 Добавить каноническую Decimal-котировку, оценку, fingerprint и consent digest.

T003 Реализовать exact-route CLI opt-in, metadata-only preview и повторную проверку quote до prompt/session.

T004 Сохранить free v1 без изменений и добавить paid v2 provenance/schema.

T005 Обновить краткое руководство и карту кода; пройти все локальные gates без model call.

### Зависимости

- Нет; WP01 — единственный пакет Mission.

---

## Сводка исполнения

- **Последовательность**: только WP01.
- **Параллелизм**: нет между пакетами; внутренний TDD-порядок T001 → T002–T005.
- **Граница**: никакого paid smoke, model call, account mutation, fallback или retry.

## Покрытие требований

| Требование | Пакет |
|---|---|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| FR-006 | WP01 |
| FR-007 | WP01 |
| FR-008 | WP01 |
| FR-009 | WP01 |

## Индекс подзадач

| ID | Кратко | Пакет |
|---|---|---|
| T001 | Failing acceptance-коммит | WP01 |
| T002 | Котировка и consent | WP01 |
| T003 | CLI и quote re-probe | WP01 |
| T004 | Free v1 / paid v2 | WP01 |
| T005 | Документация, codemap и gates | WP01 |

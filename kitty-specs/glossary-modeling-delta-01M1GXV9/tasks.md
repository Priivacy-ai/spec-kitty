---
description: "Пакет работ для усиления glossary skills проверкой модели"
---

# Пакеты работ: усиление glossary skills проверкой модели

**Входы**: `spec.md`, `plan.md`
**Организация**: один атомарный пакет; публичный route и detailed workflow не разделяются между исполнителями.

## Индекс подзадач

| ID | Описание | WP | Параллельно |
|----|----------|----|-------------|
| T001 | Зафиксировать baseline трёх синтетических smoke-сценариев до изменения skills | WP01 | Нет |
| T002 | Добавить короткий route в `spk-doctrine-glossary/SKILL.md` | WP01 | Нет |
| T003 | Добавить model pressure-test в `spec-kitty-glossary-context/SKILL.md` | WP01 | Нет |
| T004 | Повторить три smoke-сценария и сравнить с baseline | WP01 | Нет |
| T005 | Запустить validators, targeted tests и scope scan | WP01 | Нет |

---

## WP01 — Три проверки качества модели (P1, MVP)

**Цель**: атомарно добавить code cross-check, concrete edge scenario и all-three ADR gate в существующий glossary workflow.

**Независимая проверка**: три синтетических запроса демонстрируют требуемое поведение; validators и targeted tests проходят; diff остаётся в разрешённом scope.

**Prompt**: `tasks/WP01-model-pressure-test.md`
**Требования**: FR-001–FR-006, NFR-001–NFR-003, C-001–C-004
**Зависимости**: нет.

### Включённые подзадачи

T001 Зафиксировать failing-first/snapshot baseline трёх синтетических smoke-сценариев до изменения skills

T002 Добавить короткий route в `src/doctrine/skills/spk-doctrine-glossary/SKILL.md`

T003 Добавить conditional model pressure-test в `src/doctrine/skills/spec-kitty-glossary-context/SKILL.md`

T004 Повторить те же smoke-сценарии и подтвердить code cross-check, edge scenario и ADR gate

T005 Запустить validator обоих skills, `tests/doctrine/test_spk_skill_pack.py` и scope scan

### Риски и меры

- Широкий trigger → применять pressure-test только к моделированию или спорным терминам.
- Дублирование → подробные правила живут только в legacy detailed skill; публичный skill лишь маршрутизирует.
- Документальный шум → ADR разрешён только при прохождении всех трёх gates.
- Непроверенное утверждение → при отсутствии кода обязательно маркировать гипотезу.

## Сводка покрытия

| Требования | Пакет |
|------------|-------|
| FR-001–FR-006 | WP01 |
| NFR-001–NFR-003 | WP01 |
| C-001–C-004 | WP01 |

# План реализации: усиление glossary skills проверкой модели

**Ветка**: `codex/glossary-modeling-delta` | **Дата**: 2026-09-02 | **Спецификация**: `spec.md`

## Резюме

Добавить в существующий glossary workflow три узких механизма: сверку существенных утверждений модели с доступным кодом, проверку неоднозначного термина конкретным граничным сценарием и тройной gate перед рекомендацией ADR. Не переносить внешний `domain-modeling` skill, его файловую структуру или общий процесс.

## Технический контекст

**Формат**: Markdown-инструкции Codex skills  
**Основные зависимости**: существующие `spk-doctrine-glossary` и `spec-kitty-glossary-context`  
**Хранилище**: N/A  
**Проверка**: skill validator, doctrine skill-pack tests, три синтетических поведенческих smoke-сценария  
**Целевая платформа**: Codex skills на поддерживаемых платформах  
**Тип изменения**: узкое обновление существующих instruction artifacts  
**Ограничение размера**: не более двух продуктовых `SKILL.md`, без нового runtime-кода и нового skill

## Проверка charter

- Один canonical source: изменения только в `src/doctrine/skills/`; глобальные проекции не редактируются.
- Терминологическая целостность: новые проверки дополняют существующие concepts/aliases/conflicts/semantic drift.
- ATDD: до изменения инструкций фиксируются три наблюдаемых smoke-сценария; после изменения каждый обязан пройти.
- Узкий scope: runtime glossary, registry, CLI, templates и ADR-документы не меняются.
- PR-only delivery: итоговая реализация остаётся в task-ветке; merge выполняет maintainer/operator.

Нарушений charter, требующих исключения, нет.

## Техническое решение

### 1. Публичная маршрутизация

В `src/doctrine/skills/spk-doctrine-glossary/SKILL.md` добавить короткий маршрут: когда запрос не только курирует термины, но и уточняет доменную модель, detailed workflow должен применить model pressure-test. Публичный skill не дублирует подробные инструкции.

### 2. Подробный model pressure-test

В `src/doctrine/skills/spec-kitty-glossary-context/SKILL.md` добавить компактный раздел, применяемый только при уточнении модели или спорного термина:

1. Проверить существенное утверждение по доступным типам, API и тестам; при отсутствии evidence назвать его гипотезой.
2. Проверить неоднозначный термин одним конкретным граничным сценарием и уточнить definition/boundary/relation при расхождении.
3. Рекомендовать ADR только если одновременно выполнены три условия: трудно обратить, неожиданно без контекста, есть реальный компромисс между альтернативами.

### 3. Проверка результата

- До реализации прогнать три синтетических сценария и сохранить наблюдаемый baseline.
- После реализации повторить те же сценарии.
- Проверить оба skill validator и целевой doctrine skill-pack test.
- Проверить diff на отсутствие `CONTEXT.md`, `CONTEXT-MAP.md`, нового skill, runtime-кода и ADR template.

## Структура изменения

```text
src/doctrine/skills/
├── spk-doctrine-glossary/SKILL.md
└── spec-kitty-glossary-context/SKILL.md

tests/doctrine/
└── test_spk_skill_pack.py        # существующая regression-проверка, без обязательной правки
```

**Решение по структуре**: один work package владеет обоими текстами, потому что публичный route и detailed workflow образуют один контракт и должны изменяться атомарно.

## Карта реализации

### IC-01 — Проверка качества доменной модели

- **Назначение**: добавить три agreed mechanisms без создания параллельного workflow.
- **Требования**: FR-001–FR-006, NFR-001–NFR-003, C-001–C-004.
- **Поверхности**: два canonical `SKILL.md` и существующие validation commands.
- **Зависимости**: нет.
- **Риски**: слишком широкий trigger, дублирование glossary workflow, чрезмерное создание ADR.
- **Снижение рисков**: conditional trigger, одна detailed authority, all-three ADR gate, запрет новой файловой структуры.

## Codemap

`docs/codemap/codemap.lock` отсутствует. Обновление codemap не требуется: границы модулей, зависимости, routes, storage и data flow не меняются; продуктовый diff состоит только из instruction artifacts.

## Delivery gates

1. Повторное одобрение baseline до продуктовых правок.
2. Failing-first/snapshot evidence для трёх синтетических сценариев.
3. Реализация только в task-owned worktree.
4. Validator + targeted tests + scope scan.
5. Review и PR; установка/проекция и merge не входят в этот шаг.

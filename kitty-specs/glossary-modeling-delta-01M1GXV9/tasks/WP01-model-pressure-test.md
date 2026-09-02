---
work_package_id: WP01
title: Три проверки качества модели
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
- C-001
- C-002
- C-003
- C-004
tracker_refs: []
planning_base_branch: codex/glossary-modeling-delta
merge_target_branch: codex/glossary-modeling-delta
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: null
history:
- 2026-09-02 created
authoritative_surface: src/doctrine/skills/
owned_files:
- src/doctrine/skills/spk-doctrine-glossary/SKILL.md
- src/doctrine/skills/spec-kitty-glossary-context/SKILL.md
execution_mode: instruction_change
role: implementer
tags:
- glossary
- domain-modeling
---

## Цель

Добавить в существующий glossary workflow ровно три механизма: сверку модели с кодом, проверку термина конкретным граничным сценарием и тройной ADR-gate. Не импортировать внешний skill целиком.

## Сначала — проверка

До редактирования `SKILL.md` зафиксировать реакцию текущего workflow на три синтетических запроса:

1. Описание модели противоречит типам или тестам в небольшом публичном fixture.
2. Термин `status` имеет два возможных смысла и один граничный сценарий.
3. Из четырёх решений три не проходят по одному ADR-gate, одно проходит все три.

Baseline должен показать, какой из требуемых механизмов сейчас отсутствует или не гарантирован. Parser/fixture error не считается доказательством.

## Реализация

1. В публичном skill добавить только route к detailed workflow для model-shaping requests.
2. В detailed skill добавить один conditional раздел без повторения существующих правил glossary.
3. Для code cross-check требовать конкретную проверенную поверхность либо честную маркировку гипотезы.
4. Для ambiguous term требовать один concrete edge scenario, но не навязывать его уже каноническим бесспорным терминам.
5. Для ADR требовать одновременное прохождение всех трёх gates.

## Запрещённое расширение scope

- Новый skill или новый glossary store.
- `CONTEXT.md` / `CONTEXT-MAP.md`.
- Изменения runtime glossary, CLI, registry, ADR templates или глобальной установленной проекции.
- Общая переработка существующего glossary workflow.

## Definition of Done

- Три повторных smoke-сценария демонстрируют ожидаемое поведение.
- Оба изменённых skills проходят `quick_validate.py`.
- `tests/doctrine/test_spk_skill_pack.py` проходит.
- Scope scan подтверждает только два разрешённых продуктовых файла.
- Diff короткий, не дублирует existing authority и не содержит внешнего framework boilerplate.

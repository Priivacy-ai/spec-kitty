# Рабочие пакеты

Каталог содержит инструкции рабочих пакетов.

## Структура каталога

```
tasks/
├── WP01-setup-infrastructure.md
├── WP02-user-authentication.md
├── WP03-api-endpoints.md
└── README.md
```

Все файлы пакетов находятся непосредственно в `tasks/`. Статус хранится в `status.events.jsonl`, а не в YAML пакетов.

## Формат файла

Каждый файл должен содержать YAML-метаданные:

```yaml
---
work_package_id: "WP01"
title: "Название пакета"
dependencies: []
planning_base_branch: "codex/explicit-worktree-repair"
merge_target_branch: "codex/explicit-worktree-repair"
branch_strategy: "Документы подготовлены в codex/explicit-worktree-repair; интеграция вне локального этапа запрещена."
subtasks:
  - "T001"
  - "T002"
phase: "Подготовка"
assignee: ""
agent: ""
shell_pid: ""
history:
  - timestamp: "2025-01-01T00:00:00Z"
    agent: "system"
    action: "Инструкция подготовлена штатной командой"
---

# WP01: Название пакета

[Содержание инструкции]
```

## Учёт состояния

Состояние хранится в каноническом журнале `status.events.jsonl`, не в YAML пакета.
Изменять его следует только штатной командой:

```bash
spec-kitty agent tasks move-task <WPID> --to <lane>
```

Пример синтаксиса, не указание выполнить переход в этом этапе:
```bash
spec-kitty agent tasks move-task WP01 --to doing
```

## Имена файлов

- Формат: `WP01-kebab-case-slug.md`.
- Текущий пакет: `WP01-explicit-checkout.md`.

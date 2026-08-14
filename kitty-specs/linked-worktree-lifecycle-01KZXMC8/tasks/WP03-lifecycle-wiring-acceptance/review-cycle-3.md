---
affected_files: []
cycle_number: 3
mission_slug: linked-worktree-lifecycle-01KZXMC8
reproduction_command:
reviewed_at: '2026-08-14T04:05:56Z'
reviewer_agent: user
wp_id: WP03
---

# WP03 cycle 3 — REQUEST_CHANGES

## Blocker 1 — tasks lifecycle всё ещё обходит общий Mission resolver

Сквозной тест вызывает production CLI для основных семейств, но переходы
`in_progress -> for_review` и `in_review -> done` выполняет напрямую через
`append_event(..., force=True)`. `tasks.py`, `tasks_move_task.py` и
`tasks_mark_status.py` по-прежнему содержат raw `locate_project_root` /
`_find_mission_slug` и не получают `MissionOperationContext`.

Провести operation context через `move-task` и `mark-status`, затем заменить
прямые event fixture в acceptance-сценарии реальными production CLI переходами
до и после review с проверкой неизменности primary checkout.

## Blocker 2 — architectural guard остаётся ручным списком

Gate сканирует фиксированный tuple из 15 файлов. Уже существующие tasks-модули
и `mission_branch_context.py` с raw lookup находятся вне tuple, поэтому обход
остаётся зелёным. Нужен динамический repo-wide census (либо inventory, полнота
которого выводится из production CLI registrations/call sites), shrink-only
foundation allowlist и mutation в ранее не перечисленном consumer.

## Evidence

- Scoped regressions: 195 passed.
- Full-lifecycle + architectural: 4 passed.
- Ruff: PASS.
- Codemap: 7/7 nodes, 11/11 edges, оба hash совпадают.
- Broad strict mypy: 13 старых ошибок на неизменённых строках; новой регрессии нет.

Anti-patterns: dead code PASS; synthetic fixture FAIL; silent empty PASS;
FR coverage FAIL; frozen N/A; locked decision FAIL; shared ownership PASS;
production fragility PASS.
